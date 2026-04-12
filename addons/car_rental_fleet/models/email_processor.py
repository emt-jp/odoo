# -*- coding: utf-8 -*-
"""
AI-Powered Email Processor

Receives emails via Odoo's fetchmail, sends them to Claude (Anthropic API)
for classification and data extraction, then routes to the appropriate
Odoo model: fleet.booking, account.move, project.task, crm.lead, or archive.

Supports multiple inboxes with per-account context.
Auto-unsubscribes from spam/newsletters.
"""

import base64
import email as email_lib
import imaplib
import io
import re
import json
import logging
from datetime import datetime, timedelta
from email.header import decode_header

import requests

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'
CLAUDE_MODEL = 'claude-sonnet-4-20250514'

# Claude Vision limits
CLAUDE_VISION_TYPES = ('image/jpeg', 'image/png', 'image/gif', 'image/webp')
CLAUDE_IMAGE_MAX_BYTES = 5 * 1024 * 1024  # 5MB per image
CLAUDE_MAX_IMAGES = 4
PDF_MAX_PAGES = 20
PDF_TEXT_MAX_CHARS = 6000
FEW_SHOT_LIMIT = 5

EXT_TO_MIME = {
    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp',
}


class TdcEmailProcessor(models.Model):
    _name = 'tdc.email.processor'
    _description = 'AI Email Processor'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Subject', index=True)
    email_from = fields.Char(string='From')
    email_to = fields.Char(string='To (Inbox)')
    email_date = fields.Datetime(string='Email Date')
    message_id = fields.Char(
        string='Message-ID', index=True,
        help='RFC 2822 Message-ID header. Used to deduplicate during IMAP backfill.',
    )

    # AI Classification
    classification = fields.Selection([
        ('rental_booking', 'Rental Booking'),
        ('rental_cancel', 'Rental Cancellation'),
        ('invoice', 'Invoice / Receipt'),
        ('expense', 'Expense / Receipt'),
        ('task', 'Task / Action Item'),
        ('customer_inquiry', 'Customer Inquiry'),
        ('spam', 'Spam / Newsletter'),
        ('informational', 'Informational'),
        ('unclassified', 'Unclassified'),
    ], string='Classification', default='unclassified', tracking=True)
    ai_classification = fields.Selection([
        ('rental_booking', 'Rental Booking'),
        ('rental_cancel', 'Rental Cancellation'),
        ('invoice', 'Invoice / Receipt'),
        ('expense', 'Expense / Receipt'),
        ('task', 'Task / Action Item'),
        ('customer_inquiry', 'Customer Inquiry'),
        ('spam', 'Spam / Newsletter'),
        ('informational', 'Informational'),
        ('unclassified', 'Unclassified'),
    ], string='Original AI Classification', readonly=True,
       help='What the AI (or matching rule) initially said. Used to detect manual corrections.')
    matched_rule_id = fields.Many2one(
        'tdc.email.rule', string='Matched Rule', readonly=True, ondelete='set null',
        help='If set, classification came from this rule rather than Claude.')
    corrected = fields.Boolean(
        string='Manually Corrected', compute='_compute_corrected', store=False,
        help='True when the current classification differs from what AI/rule originally assigned.')
    confidence = fields.Float(string='AI Confidence', digits=(3, 2))
    ai_summary = fields.Text(string='AI Summary')
    ai_raw_response = fields.Text(string='AI Raw Response')

    # Attachment processing
    attachment_summary = fields.Text(
        string='Attachment Summary', readonly=True,
        help='Human-readable summary of attachments extracted and fed to Claude.')

    state = fields.Selection([
        ('received', 'Received'),
        ('classified', 'Classified'),
        ('processed', 'Processed'),
        ('review', 'Needs Review'),
        ('error', 'Error'),
        ('ignored', 'Ignored'),
        ('unsubscribed', 'Unsubscribed'),
    ], string='Status', default='received', tracking=True)

    # Extracted data (JSON)
    extracted_data = fields.Text(string='Extracted Data (JSON)')

    # Links to created records
    booking_id = fields.Many2one('fleet.booking', string='Booking', readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice/Bill', readonly=True)
    task_id = fields.Many2one('project.task', string='Task', readonly=True)
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    lead_id = fields.Many2one('crm.lead', string='Lead', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Contact', readonly=True)

    # Raw email
    raw_email = fields.Text(string='Raw Email Body')
    error_message = fields.Text(string='Error Details')
    unsubscribe_url = fields.Char(string='Unsubscribe URL')

    @api.depends('classification', 'ai_classification')
    def _compute_corrected(self):
        for r in self:
            r.corrected = bool(r.ai_classification) and r.classification != r.ai_classification

    # Fields added in version 2.2 — may not exist in DB during the window
    # between code deploy and module upgrade. _safe_write strips them.
    _V22_FIELDS = (
        'ai_classification', 'matched_rule_id', 'attachment_summary',
        'message_id', 'email_date',
    )

    def _v22_columns_in_db(self):
        """Return the subset of v2.2 fields whose columns actually exist in
        the DB right now. Cheap (information_schema, ~1ms) and always fresh,
        so the same worker handles both pre- and post-upgrade transparently.
        """
        try:
            with self.env.cr.savepoint():
                self.env.cr.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'tdc_email_processor'
                      AND column_name = ANY(%s)
                """, (list(self._V22_FIELDS),))
                return {row[0] for row in self.env.cr.fetchall()}
        except Exception:
            return set()

    def _safe_write(self, vals):
        """Write that drops v2.2 fields if their columns don't exist yet.

        Used by the email pipeline so the fetchmail cron doesn't crash
        in the window between deploying new code and upgrading the module.
        """
        if not vals:
            return
        present = self._v22_columns_in_db()
        filtered = {k: v for k, v in vals.items() if k in present or k not in self._V22_FIELDS}
        if filtered:
            self.write(filtered)

    # ─────────────────────────────────────────────
    # Mail gateway: receive email
    # ─────────────────────────────────────────────

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """Called by Odoo fetchmail when a new email arrives."""
        subject = msg_dict.get('subject', '') or ''
        body = msg_dict.get('body', '') or ''
        email_from = msg_dict.get('email_from', '') or ''
        email_to = msg_dict.get('to', '') or ''
        date = msg_dict.get('date', '')

        # Strip HTML
        plain_body = re.sub(r'<[^>]+>', ' ', body)
        plain_body = re.sub(r'\s+', ' ', plain_body).strip()

        # Extract List-Unsubscribe header if present
        unsubscribe_url = ''
        headers = msg_dict.get('headers', {}) or {}
        if isinstance(headers, dict):
            unsub = headers.get('List-Unsubscribe', '') or headers.get('list-unsubscribe', '')
            if unsub:
                m = re.search(r'<(https?://[^>]+)>', unsub)
                if m:
                    unsubscribe_url = m.group(1)
        # Also try to find unsubscribe link in body
        if not unsubscribe_url:
            m = re.search(r'(https?://[^\s<>"]+unsubscribe[^\s<>"]*)', body, re.IGNORECASE)
            if m:
                unsubscribe_url = m.group(1)

        vals = {
            'name': subject[:200],
            'email_from': email_from[:200],
            'email_to': email_to[:200],
            'raw_email': f"Subject: {subject}\nFrom: {email_from}\nTo: {email_to}\n\n{plain_body[:8000]}",
            'unsubscribe_url': unsubscribe_url[:500],
        }

        if custom_values:
            vals.update(custom_values)

        record = super().message_new(msg_dict, custom_values=vals)

        # Extract attachments from msg_dict now — message_post will link them
        # to this record afterwards, but at this moment they're only available
        # via the msg_dict passed to the gateway.
        attachments = record._parse_msg_attachments(msg_dict)

        # Auto-process
        try:
            record._classify_and_process(attachments=attachments)
        except Exception as e:
            _logger.error("Email processor error for %s: %s", record.id, str(e))
            record.write({
                'state': 'error',
                'error_message': str(e)[:1000],
            })

        return record

    # ─────────────────────────────────────────────
    # Attachment handling
    # ─────────────────────────────────────────────

    def _parse_msg_attachments(self, msg_dict):
        """Normalize attachments from the fetchmail msg_dict into
        [{filename, content (bytes), mimetype}, ...]."""
        items = msg_dict.get('attachments', []) or []
        result = []
        for a in items:
            filename, content, info = None, None, {}
            # Odoo uses EmailAttachment namedtuples: (fname, content, info)
            if hasattr(a, 'fname'):
                filename = a.fname
                content = a.content
                info = getattr(a, 'info', {}) or {}
            elif isinstance(a, (tuple, list)):
                if len(a) >= 3:
                    filename, content, info = a[0], a[1], (a[2] or {})
                elif len(a) == 2:
                    filename, content = a[0], a[1]
            if not filename or content is None:
                continue
            if isinstance(content, str):
                content = content.encode('utf-8', errors='replace')
            mimetype = ''
            if isinstance(info, dict):
                mimetype = info.get('content-type', '') or info.get('mimetype', '') or ''
            mimetype = mimetype.split(';')[0].strip().lower()
            result.append({
                'filename': filename,
                'content': content,
                'mimetype': mimetype,
            })
        return result

    def _get_attachments_from_record(self):
        """Read attachments already linked to this record via mail.message."""
        self.ensure_one()
        result = []
        for msg in self.message_ids:
            for a in msg.attachment_ids:
                try:
                    content = a.raw or (base64.b64decode(a.datas) if a.datas else b'')
                except Exception as e:
                    _logger.warning("Could not read attachment %s: %s", a.name, e)
                    continue
                result.append({
                    'filename': a.name or 'attachment',
                    'content': content,
                    'mimetype': (a.mimetype or '').split(';')[0].strip().lower(),
                })
        return result

    def _guess_mimetype(self, filename, mimetype):
        if mimetype:
            return mimetype
        if filename and '.' in filename:
            ext = filename.lower().rsplit('.', 1)[-1]
            if ext == 'pdf':
                return 'application/pdf'
            return EXT_TO_MIME.get(ext, '')
        return ''

    def _extract_pdf_text(self, content_bytes):
        """Extract text from a PDF byte string. Returns str or '' on failure."""
        try:
            try:
                from pypdf import PdfReader  # preferred modern lib
            except ImportError:
                from PyPDF2 import PdfReader  # older fallback
        except ImportError:
            _logger.warning("Neither pypdf nor PyPDF2 installed; skipping PDF text extraction")
            return ''

        try:
            reader = PdfReader(io.BytesIO(content_bytes))
            parts = []
            for page in reader.pages[:PDF_MAX_PAGES]:
                try:
                    parts.append(page.extract_text() or '')
                except Exception:
                    continue
            text = '\n'.join(p for p in parts if p).strip()
            return text[:PDF_TEXT_MAX_CHARS]
        except Exception as e:
            _logger.warning("PDF extraction failed: %s", e)
            return ''

    def _build_image_block(self, content_bytes, mimetype):
        """Return a Claude Vision content block for an image, or None if unsupported."""
        if mimetype not in CLAUDE_VISION_TYPES:
            return None
        if len(content_bytes) > CLAUDE_IMAGE_MAX_BYTES:
            return None
        return {
            'type': 'image',
            'source': {
                'type': 'base64',
                'media_type': mimetype,
                'data': base64.b64encode(content_bytes).decode('ascii'),
            },
        }

    def _process_attachments(self, attachments):
        """Return (pdf_context_text, image_blocks, summary_lines)."""
        pdf_chunks = []
        image_blocks = []
        summary_lines = []
        for a in attachments:
            filename = a.get('filename') or 'attachment'
            content = a.get('content') or b''
            mimetype = self._guess_mimetype(filename, a.get('mimetype') or '')
            size_kb = len(content) // 1024

            if mimetype == 'application/pdf' or filename.lower().endswith('.pdf'):
                text = self._extract_pdf_text(content)
                if text:
                    pdf_chunks.append(f"--- PDF: {filename} ---\n{text}")
                    summary_lines.append(f"{filename} ({size_kb}KB PDF): {len(text)} chars extracted")
                else:
                    summary_lines.append(f"{filename} ({size_kb}KB PDF): extraction failed")
            elif mimetype in CLAUDE_VISION_TYPES or mimetype.startswith('image/'):
                if len(image_blocks) >= CLAUDE_MAX_IMAGES:
                    summary_lines.append(f"{filename} ({size_kb}KB image): skipped (max {CLAUDE_MAX_IMAGES} images)")
                    continue
                block = self._build_image_block(content, mimetype)
                if block:
                    image_blocks.append(block)
                    summary_lines.append(f"{filename} ({size_kb}KB image): sent to Claude Vision")
                else:
                    summary_lines.append(f"{filename} ({size_kb}KB image): unsupported or too large")
            else:
                summary_lines.append(f"{filename} ({size_kb}KB, {mimetype or 'unknown'}): not processed")

        pdf_context = '\n\n'.join(pdf_chunks) if pdf_chunks else ''
        return pdf_context, image_blocks, summary_lines

    def _attach_to_record(self, target_model, target_id, attachments):
        """Link the original email attachments to a target record (booking, invoice, task)."""
        if not attachments or not target_id:
            return
        Attachment = self.env['ir.attachment'].sudo()
        for a in attachments:
            try:
                Attachment.create({
                    'name': a.get('filename') or 'attachment',
                    'datas': base64.b64encode(a.get('content') or b''),
                    'res_model': target_model,
                    'res_id': target_id,
                    'mimetype': a.get('mimetype') or 'application/octet-stream',
                })
            except Exception as e:
                _logger.warning("Attach %s → %s,%s failed: %s",
                                a.get('filename'), target_model, target_id, e)

    # ─────────────────────────────────────────────
    # AI Classification
    # ─────────────────────────────────────────────

    def _get_api_key(self):
        """Get Anthropic API key from system parameters."""
        key = self.env['ir.config_parameter'].sudo().get_param('tdc.anthropic_api_key', '')
        if not key:
            raise UserError('Anthropic API key not configured. Set tdc.anthropic_api_key in System Parameters.')
        return key

    def _get_existing_projects(self):
        """Fetch existing project names for AI matching."""
        projects = self.env['project.project'].search([], limit=50)
        return [{'id': p.id, 'name': p.name} for p in projects]

    def _get_existing_partners(self):
        """Fetch vendor/partner names for expense allocation."""
        partners = self.env['res.partner'].search([
            ('supplier_rank', '>', 0)
        ], limit=100)
        return [{'id': p.id, 'name': p.name} for p in partners]

    def _get_correction_examples(self, limit=FEW_SHOT_LIMIT):
        """Fetch recent emails where the user manually corrected the AI classification.

        Returns a list of dicts {from, subject, wrong, correct} — used as few-shot
        examples in the Claude prompt so the model learns from past mistakes.

        Defensive: if ai_classification column doesn't exist yet (deployment
        window before upgrade), returns []. The savepoint stops a missing
        column from poisoning the outer transaction.
        """
        if 'ai_classification' not in self._v22_columns_in_db():
            return []
        try:
            with self.env.cr.savepoint():
                corrections = self.env['tdc.email.processor'].search([
                    ('id', '!=', self.id or 0),
                    ('ai_classification', '!=', False),
                    ('classification', '!=', False),
                ], order='write_date desc', limit=50)
                examples = []
                for c in corrections:
                    if c.ai_classification and c.classification and c.ai_classification != c.classification:
                        examples.append({
                            'from': (c.email_from or '')[:80],
                            'subject': (c.name or '')[:120],
                            'wrong': c.ai_classification,
                            'correct': c.classification,
                        })
                        if len(examples) >= limit:
                            break
                return examples
        except Exception as e:
            _logger.warning("Correction examples query failed: %s", e)
            return []

    def _build_classification_prompt(self, pdf_context='', has_images=False):
        """Build the Claude prompt with context, past corrections, and attachment info."""
        self.ensure_one()

        projects = self._get_existing_projects()
        project_list = '\n'.join([f"  - id={p['id']}: {p['name']}" for p in projects]) or '  (no projects yet)'

        vendors = self._get_existing_partners()
        vendor_list = '\n'.join([f"  - id={v['id']}: {v['name']}" for v in vendors[:30]]) or '  (no vendors yet)'

        inbox = self.email_to or ''

        examples = self._get_correction_examples()
        examples_section = ''
        if examples:
            lines = [
                '',
                'PAST CORRECTIONS — a human reviewer corrected the AI on these. Learn from them:',
            ]
            for i, e in enumerate(examples, 1):
                lines.append(
                    f"  {i}. From: {e['from']} | Subject: {e['subject']}"
                )
                lines.append(
                    f"     AI said: {e['wrong']} → HUMAN CORRECTED to: {e['correct']}"
                )
            examples_section = '\n'.join(lines) + '\n'

        attachments_section = ''
        if pdf_context:
            attachments_section += f"\nATTACHED PDF CONTENT:\n{pdf_context}\n"
        if has_images:
            attachments_section += (
                "\nATTACHED IMAGES: The user has also attached images (shown above as image blocks). "
                "Use them to extract data — e.g., receipts, handwritten forms, screenshots of bookings.\n"
            )

        return f"""You are an AI email assistant for eMoment Japan KK (Tokyo Driving Club car rental business).

Analyze this email and classify it. Extract structured data for automatic processing.

INBOX: {inbox}
FROM: {self.email_from}
SUBJECT: {self.name}
BODY:
{(self.raw_email or '')[:4000]}
{attachments_section}
EXISTING ODOO PROJECTS:
{project_list}

KNOWN VENDORS:
{vendor_list}
{examples_section}
Classify as ONE of:
- rental_booking: Car rental booking from OTA (Rakuten, Jalan) or direct customer
- rental_cancel: Cancellation of existing rental booking
- invoice: Vendor invoice or bill to pay
- expense: Receipt, payment confirmation, or expense to record
- task: Action item, request, or work to be done by the team
- customer_inquiry: Question from customer needing response
- spam: Marketing email, newsletter, promotional — should unsubscribe
- informational: Notification, confirmation, FYI — no action needed (e.g., delivery notifications, system alerts, ETC usage reports)

Return ONLY valid JSON (no markdown, no explanation):
{{
  "classification": "one_of_above",
  "confidence": 0.95,
  "summary": "One-line summary in English",
  "extracted_data": {{
    "for_rental_booking": {{
      "customer_name": "",
      "customer_email": "",
      "customer_phone": "",
      "pickup_date": "YYYY-MM-DD HH:MM",
      "return_date": "YYYY-MM-DD HH:MM",
      "vehicle_class": "compact|minivan|wagon|suv|premium|campervan",
      "total_price": 0,
      "ota_reference": "",
      "ota_source": "rakuten|jalan|direct|other"
    }},
    "for_invoice_or_expense": {{
      "vendor_name": "",
      "vendor_id": null,
      "invoice_number": "",
      "amount": 0,
      "currency": "JPY",
      "category": "fuel|maintenance|insurance|office|toll|parking|cleaning|other",
      "description": "",
      "due_date": "YYYY-MM-DD"
    }},
    "for_task": {{
      "title": "",
      "description": "",
      "priority": "high|medium|low",
      "project_match_id": null,
      "project_match_name": "",
      "new_project_name": "",
      "due_date": "YYYY-MM-DD"
    }},
    "for_customer_inquiry": {{
      "customer_name": "",
      "customer_email": "",
      "topic": "",
      "urgency": "high|medium|low"
    }}
  }}
}}

Important rules:
- For tasks: match to an existing project by ID if the context fits. If no project matches, put the suggested name in "new_project_name".
- For invoices/expenses: match to an existing vendor by ID if recognized. If new vendor, leave vendor_id as null.
- For rental bookings: extract all Japanese fields (予約番号, 貸出日時, 返却日時, etc.)
- For spam: confidence should be high (>0.9) before we auto-unsubscribe
- ETC usage reports, charging station notifications, and system alerts are "informational" not "spam"
- Return ONLY the JSON object, no other text."""

    def _call_claude(self, content):
        """Call Anthropic Claude API.

        `content` can be either a string (text-only prompt) or a list of
        content blocks (for multimodal requests with images).
        """
        api_key = self._get_api_key()
        message_content = content  # string or list — Claude accepts both

        try:
            response = requests.post(
                ANTHROPIC_API_URL,
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json',
                },
                json={
                    'model': CLAUDE_MODEL,
                    'max_tokens': 1024,
                    'messages': [{'role': 'user', 'content': message_content}],
                },
                timeout=60,
            )

            if response.status_code != 200:
                raise Exception(f"Claude API error {response.status_code}: {response.text[:500]}")

            data = response.json()
            text = data.get('content', [{}])[0].get('text', '')
            return text

        except requests.exceptions.Timeout:
            raise Exception("Claude API timeout (30s)")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Claude API request failed: {str(e)}")

    def _parse_ai_response(self, response_text):
        """Parse Claude's JSON response."""
        try:
            # Strip markdown code fences if present
            text = response_text.strip()
            if text.startswith('```'):
                text = re.sub(r'^```\w*\n?', '', text)
                text = re.sub(r'\n?```$', '', text)

            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            m = re.search(r'\{[\s\S]*\}', response_text)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            raise Exception(f"Could not parse AI response as JSON: {response_text[:300]}")

    # ─────────────────────────────────────────────
    # Main processing pipeline
    # ─────────────────────────────────────────────

    def _check_rules(self):
        """Return the first active rule matching this email, or None.

        Defensive against the rules table not existing yet — that happens
        in the window between deploying new code and upgrading the module.
        We use a savepoint so a missing table doesn't poison the outer
        transaction (which would otherwise break the whole fetchmail batch).
        """
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                rules = self.env['tdc.email.rule'].search([('active', '=', True)])
                if not rules:
                    return None
                email_from = self.email_from or ''
                subject = self.name or ''
                body = self.raw_email or ''
                for rule in rules:
                    if rule.matches(email_from, subject, body):
                        return rule
                return None
        except Exception as e:
            _logger.warning("Rule check skipped (table missing or error): %s", e)
            return None

    def _classify_and_process(self, attachments=None):
        """Main pipeline: rule check → attachment extraction → Claude → route."""
        self.ensure_one()

        # Collect attachments — from caller (message_new flow) or the record itself
        if attachments is None:
            attachments = self._get_attachments_from_record()

        # ── 1. Fast path: check deterministic rules first (no API cost) ──
        rule = self._check_rules()
        if rule:
            rule.record_hit()
            extracted = {}
            self._safe_write({
                'classification': rule.classification,
                'ai_classification': rule.classification,
                'matched_rule_id': rule.id,
                'confidence': rule.confidence or 1.0,
                'ai_summary': f"Matched rule: {rule.name}",
                'ai_raw_response': f"[Rule match] {rule.name} (id={rule.id})",
                'extracted_data': json.dumps(extracted),
                'state': 'classified',
            })
            _logger.info("Email %s matched rule %s → %s", self.id, rule.name, rule.classification)
            # Only short-circuit Claude for classes that don't need field extraction.
            # Booking, invoice, task, cancel, inquiry all need structured data,
            # so we fall through and still call Claude (rule just pre-labels the class).
            if rule.classification in ('spam', 'informational'):
                self._route_to_handler(rule.classification, extracted, attachments=attachments)
                return

        # ── 2. Extract attachment content for Claude ──
        pdf_context, image_blocks, summary_lines = self._process_attachments(attachments)
        if summary_lines:
            self._safe_write({'attachment_summary': '\n'.join(summary_lines)})

        # ── 3. Build prompt and call Claude (multimodal if images present) ──
        prompt = self._build_classification_prompt(
            pdf_context=pdf_context,
            has_images=bool(image_blocks),
        )
        if image_blocks:
            content = list(image_blocks) + [{'type': 'text', 'text': prompt}]
        else:
            content = prompt

        raw_response = self._call_claude(content)
        result = self._parse_ai_response(raw_response)

        classification = result.get('classification', 'unclassified')
        confidence = float(result.get('confidence', 0))
        summary = result.get('summary', '')
        extracted = result.get('extracted_data', {})

        # If a rule already set classification, only overwrite if they agree —
        # the rule is the authoritative label; Claude is just enriching data.
        # (matched_rule_id may not exist in the DB yet during the upgrade window.)
        try:
            had_rule = bool(self.matched_rule_id)
        except Exception:
            had_rule = False
        if had_rule:
            classification = self.classification
            confidence = max(confidence, self.confidence)

        self._safe_write({
            'classification': classification,
            'ai_classification': classification,
            'confidence': confidence,
            'ai_summary': summary,
            'ai_raw_response': raw_response[:5000],
            'extracted_data': json.dumps(extracted, ensure_ascii=False, indent=2),
            'state': 'classified',
        })

        # Auto-process if confidence is high enough
        if confidence >= 0.9:
            self._route_to_handler(classification, extracted, attachments=attachments)
        elif confidence >= 0.7:
            self.write({'state': 'review'})
            _logger.info("Email %s classified as %s (%.0f%%) — flagged for review",
                         self.id, classification, confidence * 100)
        else:
            self.write({'state': 'review'})
            _logger.info("Email %s low confidence %.0f%% — manual triage needed",
                         self.id, confidence * 100)

    def _route_to_handler(self, classification, extracted, attachments=None):
        """Route to the appropriate handler based on classification."""
        handlers = {
            'rental_booking': self._handle_rental_booking,
            'rental_cancel': self._handle_rental_cancel,
            'invoice': self._handle_invoice,
            'expense': self._handle_invoice,  # same handler
            'task': self._handle_task,
            'customer_inquiry': self._handle_inquiry,
            'spam': self._handle_spam,
            'informational': self._handle_informational,
        }

        handler = handlers.get(classification, self._handle_informational)
        try:
            handler(extracted, attachments=attachments or [])
        except Exception as e:
            _logger.error("Handler %s failed for email %s: %s", classification, self.id, str(e))
            self.write({
                'state': 'error',
                'error_message': f"{classification} handler: {str(e)[:500]}",
            })

    # ─────────────────────────────────────────────
    # Handlers
    # ─────────────────────────────────────────────

    def _handle_rental_booking(self, extracted, attachments=None):
        """Create fleet.booking from OTA or direct booking email."""
        self.ensure_one()
        data = extracted.get('for_rental_booking', {})

        ota_ref = data.get('ota_reference', '')
        if not ota_ref:
            ota_ref = f"EMAIL-{self.id}"

        # Duplicate check
        if ota_ref and ota_ref != f"EMAIL-{self.id}":
            existing = self.env['fleet.booking'].search([
                ('special_requirements', 'ilike', f'Ref: {ota_ref}'),
                ('state', 'not in', ['cancelled', 'expired']),
            ], limit=1)
            if existing:
                self.write({
                    'state': 'processed',
                    'booking_id': existing.id,
                    'ai_summary': f"Duplicate — booking #{existing.id} already exists for ref {ota_ref}",
                })
                return

        # Parse dates
        pickup = self._parse_datetime(data.get('pickup_date', ''))
        return_dt = self._parse_datetime(data.get('return_date', ''))

        if not pickup or not return_dt:
            self.write({
                'state': 'error',
                'error_message': 'Could not parse pickup/return dates from AI extraction',
            })
            return

        # Find available vehicle
        category = data.get('vehicle_class', 'compact')
        vehicles = self.env['fleet.vehicle'].search([
            ('is_rental_vehicle', '=', True),
            ('rental_category', '=', category),
            ('availability_status', '=', 'available'),
        ], limit=50)

        assigned = None
        for v in vehicles:
            overlapping = self.env['fleet.booking'].search_count([
                ('assigned_vehicle_id', '=', v.id),
                ('state', 'not in', ['cancelled', 'expired']),
                ('pickup_date', '<', return_dt),
                ('return_date', '>', pickup),
            ])
            if overlapping == 0:
                assigned = v
                break

        if not assigned:
            self.write({
                'state': 'review',
                'error_message': f'No {category} vehicle available for {pickup} - {return_dt}',
            })
            return

        # Find or create customer
        partner = self._find_or_create_partner(
            name=data.get('customer_name', ''),
            email=data.get('customer_email', ''),
            phone=data.get('customer_phone', ''),
        )

        # Create booking
        booking = self.env['fleet.booking'].create({
            'customer_id': partner.id,
            'assigned_vehicle_id': assigned.id,
            'pickup_date': pickup,
            'return_date': return_dt,
            'pickup_location': '葛西店',
            'return_location': '葛西店',
            'estimated_total_amount': float(data.get('total_price', 0)),
            'state': 'confirmed',
            'contact_email': data.get('customer_email', ''),
            'contact_phone': data.get('customer_phone', ''),
            'special_requirements': (
                f"OTA: {data.get('ota_source', 'email')} | "
                f"Ref: {ota_ref} | "
                f"AI-processed from email #{self.id}"
            ),
        })

        self._attach_to_record('fleet.booking', booking.id, attachments)

        self.write({
            'state': 'processed',
            'booking_id': booking.id,
            'partner_id': partner.id,
        })
        _logger.info("AI created booking #%s from email #%s (%s)", booking.id, self.id, ota_ref)

    def _handle_rental_cancel(self, extracted, attachments=None):
        """Cancel an existing fleet.booking by OTA reference."""
        self.ensure_one()
        data = extracted.get('for_rental_booking', {})
        ota_ref = data.get('ota_reference', '')

        if not ota_ref:
            self.write({'state': 'review', 'error_message': 'No OTA reference found for cancellation'})
            return

        booking = self.env['fleet.booking'].search([
            ('special_requirements', 'ilike', f'Ref: {ota_ref}'),
            ('state', 'not in', ['cancelled', 'expired']),
        ], limit=1)

        if not booking:
            self.write({'state': 'review', 'error_message': f'No active booking for ref {ota_ref}'})
            return

        booking.write({'state': 'cancelled'})
        self.write({
            'state': 'processed',
            'booking_id': booking.id,
        })
        _logger.info("AI cancelled booking #%s from email #%s", booking.id, self.id)

    def _handle_invoice(self, extracted, attachments=None):
        """Create account.move (vendor bill) from invoice/receipt email."""
        self.ensure_one()
        data = extracted.get('for_invoice_or_expense', {})

        vendor_name = data.get('vendor_name', '') or self.email_from
        amount = float(data.get('amount', 0))
        description = data.get('description', '') or self.ai_summary or self.name

        if amount <= 0:
            self.write({
                'state': 'review',
                'error_message': 'Could not extract amount from invoice/receipt',
            })
            return

        # Find or create vendor partner
        vendor_id = data.get('vendor_id')
        if vendor_id:
            partner = self.env['res.partner'].browse(vendor_id)
            if not partner.exists():
                partner = None
        else:
            partner = None

        if not partner:
            partner = self._find_or_create_partner(
                name=vendor_name,
                email='',
                phone='',
                is_vendor=True,
            )

        # Find purchase journal
        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if not journal:
            self.write({
                'state': 'error',
                'error_message': 'No purchase journal found. Create one in Accounting settings.',
            })
            return

        # Create vendor bill
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'journal_id': journal.id,
            'ref': data.get('invoice_number', '') or f'AI-EMAIL-{self.id}',
            'invoice_date': fields.Date.today(),
            'invoice_date_due': self._parse_date(data.get('due_date', '')) or fields.Date.today(),
            'narration': f"AI-processed from email: {self.name}\nCategory: {data.get('category', 'other')}",
            'invoice_line_ids': [(0, 0, {
                'name': description[:200],
                'quantity': 1,
                'price_unit': amount,
            })],
        })

        self._attach_to_record('account.move', invoice.id, attachments)

        self.write({
            'state': 'processed',
            'invoice_id': invoice.id,
            'partner_id': partner.id,
        })
        _logger.info("AI created bill #%s (¥%s) from email #%s", invoice.id, amount, self.id)

    def _handle_task(self, extracted, attachments=None):
        """Create project.task, matching to existing project or creating new one."""
        self.ensure_one()
        data = extracted.get('for_task', {})

        title = data.get('title', '') or self.name or 'Untitled Task'
        description = data.get('description', '') or self.ai_summary or ''
        priority_map = {'high': '1', 'medium': '0', 'low': '0'}
        priority = priority_map.get(data.get('priority', 'medium'), '0')

        # Find or create project
        project = None
        project_match_id = data.get('project_match_id')
        if project_match_id:
            project = self.env['project.project'].browse(project_match_id)
            if not project.exists():
                project = None

        if not project:
            new_name = data.get('new_project_name', '') or data.get('project_match_name', '') or 'General'
            # Search by name (case-insensitive)
            project = self.env['project.project'].search([
                ('name', 'ilike', new_name),
            ], limit=1)

            if not project:
                project = self.env['project.project'].create({
                    'name': new_name,
                })
                _logger.info("AI created project '%s' from email #%s", new_name, self.id)

        # Parse due date
        due_date = self._parse_date(data.get('due_date', ''))

        task = self.env['project.task'].create({
            'name': title[:200],
            'description': f"{description}\n\n---\nAI-processed from email #{self.id}\nFrom: {self.email_from}",
            'project_id': project.id,
            'priority': priority,
            'date_deadline': due_date,
        })

        self._attach_to_record('project.task', task.id, attachments)

        self.write({
            'state': 'processed',
            'task_id': task.id,
            'project_id': project.id,
        })
        _logger.info("AI created task #%s in project '%s' from email #%s",
                      task.id, project.name, self.id)

    def _handle_inquiry(self, extracted, attachments=None):
        """Create CRM lead from customer inquiry."""
        self.ensure_one()
        data = extracted.get('for_customer_inquiry', {})

        name = data.get('customer_name', '') or self.email_from
        email = data.get('customer_email', '') or ''
        topic = data.get('topic', '') or self.name

        # Extract email from the from field if not in extracted data
        if not email and self.email_from:
            m = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', self.email_from)
            if m:
                email = m.group(0)

        lead = self.env['crm.lead'].create({
            'name': topic[:200],
            'partner_name': name,
            'email_from': email,
            'description': f"{self.ai_summary or ''}\n\n---\nOriginal email from: {self.email_from}\n{self.name}",
            'type': 'lead',
            'priority': '2' if data.get('urgency') == 'high' else '1' if data.get('urgency') == 'medium' else '0',
        })

        self._attach_to_record('crm.lead', lead.id, attachments)

        self.write({
            'state': 'processed',
            'lead_id': lead.id,
        })
        _logger.info("AI created lead #%s from email #%s", lead.id, self.id)

    def _handle_spam(self, extracted, attachments=None):
        """Auto-unsubscribe from spam/newsletter and archive."""
        self.ensure_one()

        if self.unsubscribe_url:
            try:
                resp = requests.get(self.unsubscribe_url, timeout=10, allow_redirects=True)
                if resp.status_code < 400:
                    _logger.info("Auto-unsubscribed from %s (email #%s)", self.unsubscribe_url[:80], self.id)
                    self.write({'state': 'unsubscribed'})
                    return
                else:
                    _logger.warning("Unsubscribe failed (HTTP %s) for email #%s", resp.status_code, self.id)
            except Exception as e:
                _logger.warning("Unsubscribe request failed for email #%s: %s", self.id, str(e))

        self.write({'state': 'ignored'})

    def _handle_informational(self, extracted, attachments=None):
        """Archive informational emails — no action needed."""
        self.ensure_one()
        self.write({'state': 'ignored'})

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────

    def _find_or_create_partner(self, name='', email='', phone='', is_vendor=False):
        """Find existing partner or create new one."""
        partner = None
        if email:
            partner = self.env['res.partner'].search([('email', '=', email)], limit=1)
        if not partner and phone:
            partner = self.env['res.partner'].search([('phone', '=', phone)], limit=1)
        if not partner and name:
            partner = self.env['res.partner'].search([('name', '=ilike', name)], limit=1)

        if not partner:
            vals = {
                'name': name or email or 'Unknown',
                'email': email or False,
                'phone': phone or False,
                'lang': 'ja_JP',
            }
            if is_vendor:
                vals['supplier_rank'] = 1
            partner = self.env['res.partner'].create(vals)

        return partner

    def _parse_datetime(self, text):
        """Parse various datetime formats."""
        if not text:
            return None
        for fmt in [
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%dT%H:%M:%S',
            '%Y/%m/%d %H:%M',
        ]:
            try:
                return datetime.strptime(text.strip(), fmt)
            except ValueError:
                continue
        return None

    def _parse_date(self, text):
        """Parse date string."""
        if not text:
            return None
        for fmt in ['%Y-%m-%d', '%Y/%m/%d']:
            try:
                return datetime.strptime(text.strip(), fmt).date()
            except ValueError:
                continue
        return None

    # ─────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────

    def action_reprocess(self):
        """Manual reprocess button."""
        for rec in self:
            if rec.state in ('error', 'review', 'received', 'classified'):
                try:
                    rec._classify_and_process()
                except Exception as e:
                    rec.write({
                        'state': 'error',
                        'error_message': str(e)[:1000],
                    })

    def action_force_process(self):
        """Force process even if confidence was low."""
        for rec in self:
            if rec.classification and rec.extracted_data:
                try:
                    extracted = json.loads(rec.extracted_data)
                    attachments = rec._get_attachments_from_record()
                    rec._route_to_handler(rec.classification, extracted, attachments=attachments)
                except Exception as e:
                    rec.write({
                        'state': 'error',
                        'error_message': str(e)[:1000],
                    })

    def action_mark_ignored(self):
        """Manually mark as ignored."""
        self.write({'state': 'ignored'})

    # ─────────────────────────────────────────────
    # Backfill
    # ─────────────────────────────────────────────

    @api.model
    def cron_backfill_attachments(self, limit=200):
        """Entry point for a scheduled/manual backfill of legacy emails.

        Picks records that haven't been through the new attachment pipeline
        (attachment_summary is empty) and have attachments in their linked
        mail.message. For records already in 'processed' state with a linked
        target record (booking/invoice/task/lead), we only *attach* the files
        to the target — we do NOT re-run classification, to avoid creating
        duplicate bookings/invoices. For everything else, we re-run the full
        pipeline.
        """
        candidates = self.search([
            ('attachment_summary', '=', False),
        ], limit=limit, order='id desc')

        stats = {'scanned': 0, 'no_attachments': 0, 'reattached': 0, 'reclassified': 0, 'errors': 0}
        for rec in candidates:
            stats['scanned'] += 1
            try:
                result = rec._backfill_one()
                if result in stats:
                    stats[result] += 1
            except Exception as e:
                _logger.exception("Backfill failed for email %s: %s", rec.id, e)
                stats['errors'] += 1
        _logger.info("Email attachment backfill: %s", stats)
        return stats

    def _backfill_one(self):
        """Backfill logic for a single record. Returns a stat key."""
        self.ensure_one()
        attachments = self._get_attachments_from_record()
        if not attachments:
            # Mark so it isn't re-scanned every run
            self._safe_write({'attachment_summary': '(no attachments)'})
            return 'no_attachments'

        # If this record is already processed and linked to a target,
        # just attach the files to the target — don't re-route or re-classify.
        target_model, target_id = None, None
        if self.booking_id:
            target_model, target_id = 'fleet.booking', self.booking_id.id
        elif self.invoice_id:
            target_model, target_id = 'account.move', self.invoice_id.id
        elif self.task_id:
            target_model, target_id = 'project.task', self.task_id.id
        elif self.lead_id:
            target_model, target_id = 'crm.lead', self.lead_id.id

        if target_model and self.state == 'processed':
            self._attach_to_record(target_model, target_id, attachments)
            # Also record a summary so we skip this record on the next backfill
            _, _, summary_lines = self._process_attachments(attachments)
            header = f"Backfilled: attached {len(attachments)} file(s) to {target_model} #{target_id}"
            self._safe_write({
                'attachment_summary': header + '\n' + '\n'.join(summary_lines),
            })
            _logger.info("Backfill: attached %d file(s) to %s #%s from email %s",
                         len(attachments), target_model, target_id, self.id)
            return 'reattached'

        # Not already routed to a target — run full pipeline with attachments.
        self._classify_and_process(attachments=attachments)
        return 'reclassified'

    def action_backfill_attachments(self):
        """Button handler: backfill the selected records (or all if called from menu).

        When triggered from a list view with selected records, only those are
        processed. When triggered from a menu action with no recordset, we
        fall through to the cron entry point which scans all candidates.
        """
        if self:
            stats = {'scanned': 0, 'no_attachments': 0, 'reattached': 0, 'reclassified': 0, 'errors': 0}
            for rec in self:
                stats['scanned'] += 1
                try:
                    result = rec._backfill_one()
                    if result in stats:
                        stats[result] += 1
                except Exception as e:
                    _logger.exception("Backfill failed for email %s: %s", rec.id, e)
                    stats['errors'] += 1
        else:
            stats = self.cron_backfill_attachments()

        msg = (
            f"Scanned {stats['scanned']}: "
            f"{stats['reclassified']} re-classified, "
            f"{stats['reattached']} re-attached, "
            f"{stats['no_attachments']} without attachments, "
            f"{stats['errors']} errors"
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Attachment backfill complete',
                'message': msg,
                'type': 'success' if stats['errors'] == 0 else 'warning',
                'sticky': True,
            },
        }

    def action_create_rule(self):
        """Open a pre-filled 'Create Rule' form based on this email.

        Intended to be clicked after the user has manually corrected the
        classification — so the rule teaches the system to handle future
        emails from this sender correctly without calling Claude.
        """
        self.ensure_one()
        sender = self.email_from or ''
        # Prefer the domain as a sender match — broader than a single address
        domain_match = re.search(r'@([\w.-]+)', sender)
        sender_pattern = domain_match.group(1) if domain_match else sender

        default_notes = (
            f"Auto-generated from email #{self.id}\n"
            f"Subject: {self.name}\n"
            f"AI originally said: {self.ai_classification or 'n/a'}\n"
            f"Human corrected to: {self.classification}"
        )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Classification Rule',
            'res_model': 'tdc.email.rule',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': f"{self.classification} from {sender_pattern}"[:80],
                'default_sender_pattern': sender_pattern,
                'default_classification': self.classification,
                'default_match_type': 'substring',
                'default_created_from_email_id': self.id,
                'default_notes': default_notes,
            },
        }

    # ─────────────────────────────────────────────
    # IMAP backfill — read every email with attachments straight from the inbox
    # ─────────────────────────────────────────────

    def _decode_mime_header(self, value):
        """Decode an RFC 2047 encoded header to a plain string."""
        if not value:
            return ''
        try:
            parts = decode_header(value)
            out = []
            for text, enc in parts:
                if isinstance(text, bytes):
                    try:
                        out.append(text.decode(enc or 'utf-8', errors='replace'))
                    except LookupError:
                        out.append(text.decode('utf-8', errors='replace'))
                else:
                    out.append(text)
            return ''.join(out)
        except Exception:
            return str(value)

    def _walk_mime(self, mime):
        """Walk a parsed MIME message.

        Returns (plain_body_text, [{filename, content, mimetype}, ...]).
        Attachments are identified by Content-Disposition or a filename on a
        non-text part. Inline images in HTML mails are also treated as
        attachments so Claude Vision can look at them.
        """
        body_parts = []
        attachments = []
        for part in mime.walk():
            if part.is_multipart():
                continue

            ctype = (part.get_content_type() or '').lower()
            disp = (part.get('Content-Disposition') or '').lower()
            filename = part.get_filename()
            if filename:
                filename = self._decode_mime_header(filename)

            is_attachment = (
                'attachment' in disp
                or (filename and not ctype.startswith('text/'))
                or (ctype.startswith('image/') and filename)
            )

            if is_attachment and filename:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        attachments.append({
                            'filename': filename,
                            'content': payload,
                            'mimetype': ctype,
                        })
                except Exception as e:
                    _logger.warning("Could not decode attachment %s: %s", filename, e)
                continue

            if ctype == 'text/plain':
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body_parts.append(payload.decode(charset, errors='replace'))
                except Exception:
                    pass
            elif ctype == 'text/html' and not body_parts:
                # Only use HTML if we haven't seen a plain part — strip tags
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html = payload.decode(charset, errors='replace')
                        plain = re.sub(r'<[^>]+>', ' ', html)
                        plain = re.sub(r'\s+', ' ', plain).strip()
                        body_parts.append(plain)
                except Exception:
                    pass

        return '\n\n'.join(body_parts), attachments

    def _ingest_mime_message(self, mime):
        """Create a tdc.email.processor record from a parsed MIME message
        and run it through the pipeline. Dedupes on Message-ID.
        Returns a stat key."""
        msg_id_hdr = (mime.get('Message-ID') or '').strip()
        if msg_id_hdr:
            existing = self.search([('message_id', '=', msg_id_hdr)], limit=1)
            if existing:
                return 'skipped_dup'

        subject = self._decode_mime_header(mime.get('Subject', ''))
        email_from = self._decode_mime_header(mime.get('From', ''))
        email_to = self._decode_mime_header(mime.get('To', ''))

        body_text, attachments = self._walk_mime(mime)

        if not attachments:
            return 'no_atts'

        unsubscribe_url = ''
        unsub = mime.get('List-Unsubscribe', '') or ''
        m = re.search(r'<(https?://[^>]+)>', unsub)
        if m:
            unsubscribe_url = m.group(1)

        email_date = None
        date_hdr = mime.get('Date')
        if date_hdr:
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(date_hdr)
                if dt:
                    # Odoo stores naive UTC datetimes
                    if dt.tzinfo:
                        dt = dt.astimezone(tz=None).replace(tzinfo=None)
                    email_date = dt
            except Exception:
                pass

        # IMAP backfill is only ever invoked manually after a successful module
        # upgrade — but defensive anyway: drop v2.2 fields if columns missing.
        create_vals = {
            'name': (subject or '(no subject)')[:200],
            'email_from': email_from[:200],
            'email_to': email_to[:200],
            'email_date': email_date,
            'message_id': msg_id_hdr[:200],
            'raw_email': f"Subject: {subject}\nFrom: {email_from}\nTo: {email_to}\n\n{body_text[:8000]}",
            'unsubscribe_url': unsubscribe_url[:500],
            'state': 'received',
        }
        present = self._v22_columns_in_db()
        create_vals = {k: v for k, v in create_vals.items()
                       if k in present or k not in self._V22_FIELDS}
        rec = self.create(create_vals)

        # Attach files to the new processor record so they appear in chatter
        # and future re-processing via _get_attachments_from_record() works.
        rec._attach_to_record('tdc.email.processor', rec.id, attachments)

        try:
            rec._classify_and_process(attachments=attachments)
        except Exception as e:
            _logger.error("Pipeline error on ingested email #%s: %s", rec.id, e)
            rec.write({'state': 'error', 'error_message': str(e)[:1000]})

        return 'ingested'

    @api.model
    def imap_backfill(self, since_months=12, folder='INBOX', limit=500):
        """Read all emails with attachments from the configured IMAP mailbox,
        ingest them as tdc.email.processor records, and run the full AI pipeline
        (including attachment extraction). Safe to re-run — dedupes on Message-ID.

        Credentials read from ir.config_parameter:
          tdc.imap_host     (default imap.gmail.com)
          tdc.imap_port     (default 993)
          tdc.imap_user     (e.g. car.care@emoment.jp)
          tdc.imap_password (Gmail app password, not account password)

        For Gmail mailboxes, uses X-GM-RAW "has:attachment newer_than:Nm" —
        orders of magnitude faster than standard IMAP SEARCH. Falls back to
        SINCE <date> + client-side attachment filtering for non-Gmail servers.
        """
        params = self.env['ir.config_parameter'].sudo()
        host = params.get_param('tdc.imap_host', 'imap.gmail.com')
        port = int(params.get_param('tdc.imap_port', '993'))
        user = params.get_param('tdc.imap_user', '')
        password = params.get_param('tdc.imap_password', '')

        if not user or not password:
            raise UserError(
                'IMAP credentials not set. Configure these System Parameters:\n'
                '  tdc.imap_host, tdc.imap_port, tdc.imap_user, tdc.imap_password\n'
                'For Gmail, tdc.imap_password must be an App Password.'
            )

        stats = {
            'scanned': 0,
            'skipped_dup': 0,
            'ingested': 0,
            'no_atts': 0,
            'errors': 0,
        }

        imap = None
        try:
            _logger.info("IMAP backfill: connecting to %s:%s as %s", host, port, user)
            imap = imaplib.IMAP4_SSL(host, port)
            imap.login(user, password)
            imap.select(folder, readonly=True)

            uids = []
            is_gmail = 'gmail' in host.lower()
            if is_gmail:
                try:
                    query = f'"has:attachment newer_than:{int(since_months)}m"'
                    typ, data = imap.uid('search', None, 'X-GM-RAW', query)
                    if typ == 'OK' and data and data[0]:
                        uids = data[0].split()
                        _logger.info("IMAP backfill: Gmail X-GM-RAW found %d messages", len(uids))
                    else:
                        _logger.info("IMAP backfill: Gmail search returned no results (%s)", typ)
                except Exception as e:
                    _logger.warning("IMAP backfill: X-GM-RAW failed (%s), falling back", e)
                    uids = []

            if not uids:
                since_dt = datetime.now() - timedelta(days=int(since_months) * 31)
                since_str = since_dt.strftime('%d-%b-%Y')
                typ, data = imap.uid('search', None, 'SINCE', since_str)
                if typ != 'OK':
                    raise UserError(f'IMAP search failed: {typ}')
                uids = data[0].split() if data and data[0] else []
                _logger.info("IMAP backfill: standard SINCE %s found %d messages",
                             since_str, len(uids))

            # Most-recent first, then cap to limit
            uids = list(reversed(uids))
            if limit:
                uids = uids[:int(limit)]

            for uid in uids:
                stats['scanned'] += 1
                try:
                    typ, msg_data = imap.uid('fetch', uid, '(RFC822)')
                    if typ != 'OK' or not msg_data or not msg_data[0]:
                        stats['errors'] += 1
                        continue
                    # msg_data[0] is a tuple (response, raw_bytes)
                    raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
                    if not raw:
                        stats['errors'] += 1
                        continue
                    mime = email_lib.message_from_bytes(raw)
                    result = self._ingest_mime_message(mime)
                    if result in stats:
                        stats[result] += 1
                    # Commit after each to avoid losing everything on a later crash
                    if stats['scanned'] % 10 == 0:
                        self.env.cr.commit()
                except Exception as e:
                    _logger.exception("IMAP backfill error uid=%s: %s", uid, e)
                    stats['errors'] += 1
        finally:
            if imap is not None:
                try:
                    imap.close()
                except Exception:
                    pass
                try:
                    imap.logout()
                except Exception:
                    pass

        _logger.info("IMAP backfill done: %s", stats)
        return stats

    @api.model
    def action_imap_backfill(self):
        """UI entry point: run IMAP backfill with default parameters (12 months,
        500 messages) and show a notification with the result."""
        stats = self.imap_backfill(since_months=12, limit=500)
        msg = (
            f"Scanned {stats['scanned']}: "
            f"{stats['ingested']} ingested, "
            f"{stats['skipped_dup']} already known, "
            f"{stats['no_atts']} without attachments, "
            f"{stats['errors']} errors"
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'IMAP backfill complete',
                'message': msg,
                'type': 'success' if stats['errors'] == 0 else 'warning',
                'sticky': True,
            },
        }
