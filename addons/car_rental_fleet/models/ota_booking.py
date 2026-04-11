# -*- coding: utf-8 -*-
"""
OTA (Online Travel Agency) Booking Email Processor

Automatically parses incoming booking emails from Rakuten Travel,
Jalan, and other OTAs, then creates fleet.booking records with
auto-assigned vehicles.

The model inherits mail.thread so Odoo's fetchmail module routes
incoming emails to message_new(), which does the parsing and booking.
"""

import re
import logging
from datetime import datetime

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


# ─── Vehicle class mapping: Japanese OTA terms → rental_category ───
VEHICLE_CLASS_MAP = {
    'コンパクト': 'compact',
    'エコノミー': 'economy',
    'スタンダード': 'compact',
    'セダン': 'premium',
    'ワンボックス': 'minivan',
    'ミニバン': 'minivan',
    'ワゴン': 'wagon',
    'SUV': 'suv',
    'RV': 'suv',
    '軽自動車': 'compact',
    'エコカー': 'compact',
    'ハイブリッド': 'compact',
    'キャンピング': 'campervan',
    'プレミアム': 'premium',
    'ラグジュアリー': 'luxury',
    'バン': 'minivan',
}


def _parse_japanese_date(text):
    """Parse Japanese date formats into datetime.

    Handles:
      2026-4-30（木）08:30
      2026年05月03日 08:00
      2026/04/30 08:30
    """
    if not text:
        return None

    # Format: 2026-4-30（木）08:30 or 2026-4-30（木）08:30
    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})[（(][^)）]*[)）]\s*(\d{1,2}):(\d{2})', text)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                        int(m.group(4)), int(m.group(5)))

    # Format: 2026年05月03日 08:00
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})', text)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                        int(m.group(4)), int(m.group(5)))

    # Format: 2026/04/30 08:30
    m = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})', text)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                        int(m.group(4)), int(m.group(5)))

    return None


def _extract_field(text, *patterns):
    """Try multiple regex patterns, return first match group 1."""
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip()
    return ''


def _extract_price(text):
    """Extract price in JPY from text like '25,530円' or '合計金額：38,020円'."""
    m = re.search(r'合計[金額）)]*[：:\s]*[（(]?([,\d]+)\s*円', text)
    if not m:
        m = re.search(r'（合計）[：:\s]*([,\d]+)\s*円', text)
    if not m:
        m = re.search(r'合計金額[：:\s]*([,\d]+)\s*円', text)
    if m:
        return int(m.group(1).replace(',', ''))
    return 0


def _map_vehicle_class(class_text):
    """Map Japanese vehicle class description to rental_category."""
    if not class_text:
        return 'compact'
    for keyword, category in VEHICLE_CLASS_MAP.items():
        if keyword in class_text:
            return category
    return 'compact'  # default


def _clean_name(name):
    """Remove 様 suffix and extra whitespace from Japanese names."""
    if not name:
        return ''
    return re.sub(r'\s*様\s*$', '', name).strip()


def parse_rakuten_email(body):
    """Parse a Rakuten Travel booking email into a dict of fields.

    Returns dict with keys: ota_reference, customer_name, customer_name_kana,
    customer_email, customer_phone, driver_name, driver_name_kana,
    pickup_date, return_date, vehicle_class, total_price, options, is_cancel
    """
    if not body:
        return None

    result = {
        'source': 'rakuten',
        'is_cancel': bool(re.search(r'キャンセル|取消', body)),
    }

    # OTA Reference — try both formats
    result['ota_reference'] = _extract_field(
        body,
        r'予約番号\s*[：:]\s*([A-Za-z0-9]+)',
        r'予約番号\s*[：:]\s*(\S+)',
    )

    # Customer name
    result['customer_name'] = _clean_name(_extract_field(
        body,
        r'予約者氏名\s*[：:]\s*(.+?)(?:\s*様|\s*$)',
        r'予約者氏名\s*[：:]\s*(.+)',
    ))

    # Customer name kana
    result['customer_name_kana'] = _clean_name(_extract_field(
        body,
        r'予約者氏名[（(]カナ[)）]\s*[：:]\s*(.+?)(?:\s*様|\s*$)',
        r'予約者氏名（カナ）\s*[：:]\s*(.+)',
    ))

    # Driver name (may differ from booker)
    result['driver_name'] = _clean_name(_extract_field(
        body,
        r'運転者氏名\s*[：:]\s*(.+?)(?:\s*様|\s*$)',
        r'利用者氏名\s*[：:]\s*(.+?)(?:\s*様|\s*$)',
    )) or result['customer_name']

    # Driver name kana
    result['driver_name_kana'] = _clean_name(_extract_field(
        body,
        r'運転者氏名[（(]?カナ[)）]?\s*[：:]\s*(.+?)(?:\s*様|\s*$)',
        r'利用者氏名[（(]カナ[)）]\s*[：:]\s*(.+?)(?:\s*様|\s*$)',
    )) or result['customer_name_kana']

    # Email
    result['customer_email'] = _extract_field(
        body,
        r'メールアドレス\s*[：:]\s*(\S+@\S+)',
        r'予約者メールアドレス\s*[：:]\s*(\S+@\S+)',
    )

    # Phone
    result['customer_phone'] = _extract_field(
        body,
        r'運転者電話番号\s*[：:]\s*([\d\-]+)',
        r'電話番号\s*[：:]\s*([\d\-]+)',
    )

    # Pickup date
    pickup_text = _extract_field(
        body,
        r'貸出日時\s*[：:]\s*(.+)',
        r'□貸出日時\s*[：:]\s*(.+)',
    )
    result['pickup_date'] = _parse_japanese_date(pickup_text)

    # Return date
    return_text = _extract_field(
        body,
        r'返却日時\s*[：:]\s*(.+)',
        r'□返却日時\s*[：:]\s*(.+)',
    )
    result['return_date'] = _parse_japanese_date(return_text)

    # Vehicle class
    class_text = _extract_field(
        body,
        r'車両クラス\s*[：:]\s*(.+)',
        r'詳細車両クラス\s*[：:]\s*(.+)',
        r'料金プラン\s*[：:]\s*(.+)',
    )
    result['vehicle_class'] = _map_vehicle_class(class_text)
    result['vehicle_class_raw'] = class_text

    # Total price
    result['total_price'] = _extract_price(body)

    # Options
    options = []
    if re.search(r'カーナビ', body):
        options.append('navigation')
    if re.search(r'ETC', body):
        options.append('etc')
    if re.search(r'免責補償', body):
        options.append('cdw')
    if re.search(r'あんしん補償', body):
        options.append('full_insurance')
    if re.search(r'チャイルドシート', body):
        options.append('child_seat')
    if re.search(r'ジュニアシート', body):
        options.append('junior_seat')
    result['options'] = options

    # Non-smoking
    result['non_smoking'] = bool(re.search(r'禁煙', body))

    # Pickup/return location
    result['pickup_location'] = _extract_field(
        body,
        r'貸出営業所\s*[：:]\s*(.+)',
        r'貸渡営業所名\s*[：:]\s*(.+)',
    ) or '葛西店'
    result['return_location'] = _extract_field(
        body,
        r'返却営業所\s*[：:]\s*(.+)',
        r'返却営業所名\s*[：:]\s*(.+)',
    ) or result['pickup_location']

    # Validate minimum required fields
    if not result['ota_reference'] and not result['pickup_date']:
        return None

    return result


class TdcOtaEmail(models.Model):
    _name = 'tdc.ota.email'
    _description = 'OTA Booking Email'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='OTA Reference', index=True)
    source = fields.Selection([
        ('rakuten', 'Rakuten Travel'),
        ('jalan', 'Jalan'),
        ('other', 'Other'),
    ], string='Source', default='other')
    state = fields.Selection([
        ('received', 'Received'),
        ('booked', 'Booked'),
        ('cancelled', 'Cancelled'),
        ('duplicate', 'Duplicate'),
        ('no_availability', 'No Availability'),
        ('error', 'Error'),
    ], string='Status', default='received', tracking=True)

    # Parsed booking data
    customer_name = fields.Char(string='Customer Name')
    customer_name_kana = fields.Char(string='Customer Name (Kana)')
    customer_email = fields.Char(string='Customer Email')
    customer_phone = fields.Char(string='Customer Phone')
    driver_name = fields.Char(string='Driver Name')
    driver_name_kana = fields.Char(string='Driver Name (Kana)')
    pickup_date = fields.Datetime(string='Pickup Date')
    return_date = fields.Datetime(string='Return Date')
    pickup_location = fields.Char(string='Pickup Location')
    return_location = fields.Char(string='Return Location')
    vehicle_class = fields.Selection([
        ('economy', 'Economy'),
        ('compact', 'Compact'),
        ('midsize', 'Midsize'),
        ('wagon', 'Wagon'),
        ('premium', 'Premium'),
        ('luxury', 'Luxury'),
        ('suv', 'SUV'),
        ('minivan', 'Minivan'),
        ('campervan', 'Campervan'),
    ], string='Vehicle Class')
    vehicle_class_raw = fields.Char(string='Vehicle Class (Original)')
    total_price = fields.Float(string='Total Price (JPY)')
    options = fields.Char(string='Options')
    non_smoking = fields.Boolean(string='Non-Smoking', default=True)

    # Result
    booking_id = fields.Many2one('fleet.booking', string='Created Booking', readonly=True)
    assigned_vehicle_id = fields.Many2one('fleet.vehicle', string='Assigned Vehicle', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    error_message = fields.Text(string='Error Details')
    raw_email = fields.Text(string='Raw Email')
    is_cancel = fields.Boolean(string='Is Cancellation', default=False)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """Called by Odoo's mail gateway when a new email arrives.

        Parses the email, creates the OTA record, and auto-processes it.
        """
        subject = msg_dict.get('subject', '')
        body = msg_dict.get('body', '')
        email_from = msg_dict.get('email_from', '')

        # Detect source from sender
        source = 'other'
        if re.search(r'rakuten', email_from, re.IGNORECASE):
            source = 'rakuten'
        elif re.search(r'jalan', email_from, re.IGNORECASE):
            source = 'jalan'

        # Strip HTML tags from body for parsing
        plain_body = re.sub(r'<[^>]+>', '', body)
        full_text = f"{subject}\n\n{plain_body}"

        # Parse the email
        parsed = None
        if source == 'rakuten':
            parsed = parse_rakuten_email(full_text)

        vals = {
            'name': parsed.get('ota_reference', subject[:60]) if parsed else subject[:60],
            'source': source,
            'raw_email': full_text[:10000],
            'is_cancel': parsed.get('is_cancel', False) if parsed else False,
        }

        if parsed:
            vals.update({
                'customer_name': parsed.get('customer_name', ''),
                'customer_name_kana': parsed.get('customer_name_kana', ''),
                'customer_email': parsed.get('customer_email', ''),
                'customer_phone': parsed.get('customer_phone', ''),
                'driver_name': parsed.get('driver_name', ''),
                'driver_name_kana': parsed.get('driver_name_kana', ''),
                'pickup_date': parsed.get('pickup_date'),
                'return_date': parsed.get('return_date'),
                'pickup_location': parsed.get('pickup_location', '葛西店'),
                'return_location': parsed.get('return_location', '葛西店'),
                'vehicle_class': parsed.get('vehicle_class', 'compact'),
                'vehicle_class_raw': parsed.get('vehicle_class_raw', ''),
                'total_price': parsed.get('total_price', 0),
                'options': ', '.join(parsed.get('options', [])),
                'non_smoking': parsed.get('non_smoking', True),
            })

        if custom_values:
            vals.update(custom_values)

        record = super().message_new(msg_dict, custom_values=vals)

        # Auto-process after creation
        try:
            record._process_ota_booking()
        except Exception as e:
            _logger.error("OTA auto-process failed for %s: %s", record.name, str(e))
            record.write({
                'state': 'error',
                'error_message': str(e),
            })

        return record

    def _process_ota_booking(self):
        """Process the parsed OTA email — find vehicle, create booking."""
        self.ensure_one()

        if not self.pickup_date or not self.return_date:
            self.write({
                'state': 'error',
                'error_message': 'Could not parse pickup or return dates from email.',
            })
            return

        # ── Handle cancellation ──
        if self.is_cancel:
            return self._process_cancellation()

        # ── Duplicate check ──
        existing = self.search([
            ('name', '=', self.name),
            ('state', '=', 'booked'),
            ('id', '!=', self.id),
        ], limit=1)
        if existing:
            self.write({
                'state': 'duplicate',
                'error_message': f'Duplicate of OTA email #{existing.id} (booking {existing.booking_id.id})',
                'booking_id': existing.booking_id.id,
            })
            return

        # Also check fleet.booking special_requirements for the OTA reference
        if self.name:
            existing_booking = self.env['fleet.booking'].search([
                ('special_requirements', 'ilike', f'Ref: {self.name}'),
                ('state', 'not in', ['cancelled', 'expired']),
            ], limit=1)
            if existing_booking:
                self.write({
                    'state': 'duplicate',
                    'booking_id': existing_booking.id,
                    'assigned_vehicle_id': existing_booking.assigned_vehicle_id.id,
                    'error_message': f'Booking already exists: #{existing_booking.id}',
                })
                return

        # ── Find available vehicle ──
        category = self.vehicle_class or 'compact'
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
                ('pickup_date', '<', self.return_date),
                ('return_date', '>', self.pickup_date),
            ])
            if overlapping == 0:
                assigned = v
                break

        if not assigned:
            self.write({
                'state': 'no_availability',
                'error_message': f'No {category} vehicle available for {self.pickup_date} - {self.return_date}',
            })
            return

        # ── Find or create customer ──
        partner = None
        if self.customer_email:
            partner = self.env['res.partner'].search([
                ('email', '=', self.customer_email)
            ], limit=1)
        if not partner and self.customer_phone:
            partner = self.env['res.partner'].search([
                ('phone', '=', self.customer_phone)
            ], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': self.customer_name or 'OTA Customer',
                'email': self.customer_email or False,
                'phone': self.customer_phone or False,
                'lang': 'ja_JP',
            })

        # ── Create fleet.booking ──
        booking = self.env['fleet.booking'].create({
            'customer_id': partner.id,
            'assigned_vehicle_id': assigned.id,
            'pickup_date': self.pickup_date,
            'return_date': self.return_date,
            'pickup_location': self.pickup_location or '葛西店',
            'return_location': self.return_location or '葛西店',
            'estimated_total_amount': self.total_price or 0,
            'state': 'confirmed',
            'contact_email': self.customer_email or '',
            'contact_phone': self.customer_phone or '',
            'special_requirements': (
                f'OTA: {self.source} | Ref: {self.name} | '
                f'Driver: {self.driver_name} ({self.driver_name_kana}) | '
                f'Options: {self.options}'
            ),
        })

        self.write({
            'state': 'booked',
            'booking_id': booking.id,
            'assigned_vehicle_id': assigned.id,
            'partner_id': partner.id,
        })

        _logger.info(
            "OTA booking created: %s → booking #%s, vehicle %s (%s)",
            self.name, booking.id, assigned.name, category,
        )

    def _process_cancellation(self):
        """Find and cancel an existing booking by OTA reference."""
        self.ensure_one()

        if not self.name:
            self.write({
                'state': 'error',
                'error_message': 'Cannot process cancellation without OTA reference.',
            })
            return

        booking = self.env['fleet.booking'].search([
            ('special_requirements', 'ilike', f'Ref: {self.name}'),
            ('state', 'not in', ['cancelled', 'expired']),
        ], limit=1)

        if not booking:
            self.write({
                'state': 'error',
                'error_message': f'No active booking found for OTA reference: {self.name}',
            })
            return

        booking.write({'state': 'cancelled'})
        self.write({
            'state': 'cancelled',
            'booking_id': booking.id,
            'assigned_vehicle_id': booking.assigned_vehicle_id.id,
        })

        _logger.info("OTA cancellation: %s → booking #%s cancelled", self.name, booking.id)

    def action_reprocess(self):
        """Manual reprocess button for failed/error records."""
        for rec in self:
            if rec.state in ('error', 'no_availability', 'received'):
                try:
                    rec._process_ota_booking()
                except Exception as e:
                    rec.write({
                        'state': 'error',
                        'error_message': str(e),
                    })
