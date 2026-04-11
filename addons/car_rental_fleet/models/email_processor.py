# -*- coding: utf-8 -*-
"""
AI-Powered Email Processor

Receives emails via Odoo's fetchmail, sends them to Claude (Anthropic API)
for classification and data extraction, then routes to the appropriate
Odoo model: fleet.booking, account.move, project.task, crm.lead, or archive.

Supports multiple inboxes with per-account context.
Auto-unsubscribes from spam/newsletters.
"""

import re
import json
import logging
from datetime import datetime

import requests

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'
CLAUDE_MODEL = 'claude-sonnet-4-20250514'


class TdcEmailProcessor(models.Model):
    _name = 'tdc.email.processor'
    _description = 'AI Email Processor'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Subject', index=True)
    email_from = fields.Char(string='From')
    email_to = fields.Char(string='To (Inbox)')
    email_date = fields.Datetime(string='Email Date')

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
    confidence = fields.Float(string='AI Confidence', digits=(3, 2))
    ai_summary = fields.Text(string='AI Summary')
    ai_raw_response = fields.Text(string='AI Raw Response')

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

        # Auto-process
        try:
            record._classify_and_process()
        except Exception as e:
            _logger.error("Email processor error for %s: %s", record.id, str(e))
            record.write({
                'state': 'error',
                'error_message': str(e)[:1000],
            })

        return record

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

    def _build_classification_prompt(self):
        """Build the Claude prompt with context."""
        self.ensure_one()

        projects = self._get_existing_projects()
        project_list = '\n'.join([f"  - id={p['id']}: {p['name']}" for p in projects]) or '  (no projects yet)'

        vendors = self._get_existing_partners()
        vendor_list = '\n'.join([f"  - id={v['id']}: {v['name']}" for v in vendors[:30]]) or '  (no vendors yet)'

        inbox = self.email_to or ''

        return f"""You are an AI email assistant for eMoment Japan KK (Tokyo Driving Club car rental business).

Analyze this email and classify it. Extract structured data for automatic processing.

INBOX: {inbox}
FROM: {self.email_from}
SUBJECT: {self.name}
BODY:
{(self.raw_email or '')[:4000]}

EXISTING ODOO PROJECTS:
{project_list}

KNOWN VENDORS:
{vendor_list}

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

    def _call_claude(self, prompt):
        """Call Anthropic Claude API."""
        api_key = self._get_api_key()

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
                    'messages': [{'role': 'user', 'content': prompt}],
                },
                timeout=30,
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

    def _classify_and_process(self):
        """Main pipeline: classify email with Claude, then route to handler."""
        self.ensure_one()

        # Build prompt and call Claude
        prompt = self._build_classification_prompt()
        raw_response = self._call_claude(prompt)
        result = self._parse_ai_response(raw_response)

        classification = result.get('classification', 'unclassified')
        confidence = float(result.get('confidence', 0))
        summary = result.get('summary', '')
        extracted = result.get('extracted_data', {})

        self.write({
            'classification': classification,
            'confidence': confidence,
            'ai_summary': summary,
            'ai_raw_response': raw_response[:5000],
            'extracted_data': json.dumps(extracted, ensure_ascii=False, indent=2),
            'state': 'classified',
        })

        # Auto-process if confidence is high enough
        if confidence >= 0.9:
            self._route_to_handler(classification, extracted)
        elif confidence >= 0.7:
            self.write({'state': 'review'})
            _logger.info("Email %s classified as %s (%.0f%%) — flagged for review",
                         self.id, classification, confidence * 100)
        else:
            self.write({'state': 'review'})
            _logger.info("Email %s low confidence %.0f%% — manual triage needed",
                         self.id, confidence * 100)

    def _route_to_handler(self, classification, extracted):
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
            handler(extracted)
        except Exception as e:
            _logger.error("Handler %s failed for email %s: %s", classification, self.id, str(e))
            self.write({
                'state': 'error',
                'error_message': f"{classification} handler: {str(e)[:500]}",
            })

    # ─────────────────────────────────────────────
    # Handlers
    # ─────────────────────────────────────────────

    def _handle_rental_booking(self, extracted):
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

        self.write({
            'state': 'processed',
            'booking_id': booking.id,
            'partner_id': partner.id,
        })
        _logger.info("AI created booking #%s from email #%s (%s)", booking.id, self.id, ota_ref)

    def _handle_rental_cancel(self, extracted):
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

    def _handle_invoice(self, extracted):
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

        self.write({
            'state': 'processed',
            'invoice_id': invoice.id,
            'partner_id': partner.id,
        })
        _logger.info("AI created bill #%s (¥%s) from email #%s", invoice.id, amount, self.id)

    def _handle_task(self, extracted):
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

        self.write({
            'state': 'processed',
            'task_id': task.id,
            'project_id': project.id,
        })
        _logger.info("AI created task #%s in project '%s' from email #%s",
                      task.id, project.name, self.id)

    def _handle_inquiry(self, extracted):
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

        self.write({
            'state': 'processed',
            'lead_id': lead.id,
        })
        _logger.info("AI created lead #%s from email #%s", lead.id, self.id)

    def _handle_spam(self, extracted):
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

    def _handle_informational(self, extracted):
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
                    rec._route_to_handler(rec.classification, extracted)
                except Exception as e:
                    rec.write({
                        'state': 'error',
                        'error_message': str(e)[:1000],
                    })

    def action_mark_ignored(self):
        """Manually mark as ignored."""
        self.write({'state': 'ignored'})
