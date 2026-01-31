# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class FleetNotificationTemplate(models.Model):
    _name = 'fleet.notification.template'
    _description = 'Fleet Notification Templates'
    _order = 'name'

    name = fields.Char('Template Name', required=True)
    active = fields.Boolean('Active', default=True)

    # Notification Type
    notification_type = fields.Selection([
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('pickup_reminder', 'Pickup Reminder'),
        ('return_reminder', 'Return Reminder'),
        ('rental_started', 'Rental Started'),
        ('rental_completed', 'Rental Completed'),
        ('payment_received', 'Payment Received'),
        ('payment_due', 'Payment Due'),
        ('document_expiry', 'Document Expiry Reminder'),
        ('service_scheduled', 'Service Scheduled'),
        ('damage_report', 'Damage Report'),
        ('promo_offer', 'Promotional Offer'),
        ('welcome', 'Welcome Message'),
        ('thank_you', 'Thank You Message'),
    ], string='Notification Type', required=True)

    # Channels
    send_email = fields.Boolean('Send Email', default=True)
    send_sms = fields.Boolean('Send SMS', default=False)
    send_whatsapp = fields.Boolean('Send WhatsApp', default=False)

    # Email Template
    email_subject = fields.Char('Email Subject')
    email_body_html = fields.Html('Email Body', sanitize_style=True)

    # SMS Template
    sms_body = fields.Text('SMS Body', help='Max 160 characters recommended. Use placeholders like {{customer_name}}, {{vehicle_name}}, etc.')

    # WhatsApp Template
    whatsapp_body = fields.Text('WhatsApp Body')

    # Timing
    send_timing = fields.Selection([
        ('immediate', 'Immediately'),
        ('scheduled', 'Scheduled'),
    ], string='Send Timing', default='immediate')

    hours_before = fields.Integer('Hours Before Event', default=24, help='For reminder notifications')

    # Placeholders Help
    placeholder_help = fields.Text('Available Placeholders', compute='_compute_placeholder_help')

    @api.depends('notification_type')
    def _compute_placeholder_help(self):
        placeholders = """
Available Placeholders:
{{customer_name}} - Customer's name
{{customer_email}} - Customer's email
{{customer_phone}} - Customer's phone
{{vehicle_name}} - Vehicle name
{{vehicle_plate}} - License plate
{{booking_ref}} - Booking reference
{{rental_ref}} - Rental reference
{{pickup_date}} - Pickup date/time
{{return_date}} - Return date/time
{{pickup_location}} - Pickup location
{{return_location}} - Return location
{{total_amount}} - Total rental amount
{{daily_rate}} - Daily rate
{{duration_days}} - Rental duration
{{company_name}} - Company name
{{company_phone}} - Company phone
{{company_email}} - Company email
"""
        for template in self:
            template.placeholder_help = placeholders

    def send_notification(self, record, extra_values=None):
        """Send notification based on template"""
        self.ensure_one()

        values = self._prepare_values(record, extra_values)

        if self.send_email:
            self._send_email(record, values)

        if self.send_sms:
            self._send_sms(record, values)

        # Log notification
        self._log_notification(record, values)

        return True

    def _prepare_values(self, record, extra_values=None):
        """Prepare template values from record"""
        values = extra_values or {}

        # Get company info
        company = self.env.company
        values.update({
            'company_name': company.name,
            'company_phone': company.phone or '',
            'company_email': company.email or '',
        })

        # Get customer info
        customer = None
        if hasattr(record, 'customer_id') and record.customer_id:
            customer = record.customer_id
        elif hasattr(record, 'partner_id') and record.partner_id:
            customer = record.partner_id

        if customer:
            values.update({
                'customer_name': customer.name,
                'customer_email': customer.email or '',
                'customer_phone': customer.phone or customer.mobile or '',
            })

        # Get vehicle info
        vehicle = None
        if hasattr(record, 'vehicle_id') and record.vehicle_id:
            vehicle = record.vehicle_id
        elif hasattr(record, 'assigned_vehicle_id') and record.assigned_vehicle_id:
            vehicle = record.assigned_vehicle_id

        if vehicle:
            values.update({
                'vehicle_name': vehicle.name,
                'vehicle_plate': vehicle.license_plate or '',
            })

        # Get booking/rental info
        if record._name == 'fleet.booking':
            values.update({
                'booking_ref': record.name,
                'pickup_date': record.pickup_date.strftime('%Y-%m-%d %H:%M') if record.pickup_date else '',
                'return_date': record.return_date.strftime('%Y-%m-%d %H:%M') if record.return_date else '',
                'pickup_location': record.pickup_location or '',
                'return_location': record.return_location or '',
                'total_amount': f"{record.estimated_total_amount:.2f}" if record.estimated_total_amount else '',
            })

        if record._name == 'fleet.rental':
            values.update({
                'rental_ref': record.name,
                'pickup_date': record.start_date.strftime('%Y-%m-%d %H:%M') if record.start_date else '',
                'return_date': record.end_date.strftime('%Y-%m-%d %H:%M') if record.end_date else '',
                'pickup_location': record.pickup_location or '',
                'return_location': record.return_location or '',
                'total_amount': f"{record.total_amount:.2f}" if record.total_amount else '',
                'daily_rate': f"{record.daily_rate:.2f}" if record.daily_rate else '',
                'duration_days': str(record.duration_days) if hasattr(record, 'duration_days') else '',
            })

        return values

    def _render_template(self, template_text, values):
        """Render template with values"""
        if not template_text:
            return ''

        result = template_text
        for key, value in values.items():
            result = result.replace('{{' + key + '}}', str(value or ''))

        return result

    def _send_email(self, record, values):
        """Send email notification"""
        customer = None
        if hasattr(record, 'customer_id') and record.customer_id:
            customer = record.customer_id
        elif hasattr(record, 'partner_id') and record.partner_id:
            customer = record.partner_id

        if not customer or not customer.email:
            _logger.warning(f"Cannot send email: No customer email for record {record}")
            return

        subject = self._render_template(self.email_subject, values)
        body = self._render_template(self.email_body_html, values)

        mail_values = {
            'subject': subject,
            'body_html': body,
            'email_to': customer.email,
            'email_from': self.env.company.email or self.env.user.email,
        }

        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()

        _logger.info(f"Email sent to {customer.email} for {self.notification_type}")

    def _send_sms(self, record, values):
        """Send SMS notification"""
        customer = None
        if hasattr(record, 'customer_id') and record.customer_id:
            customer = record.customer_id
        elif hasattr(record, 'partner_id') and record.partner_id:
            customer = record.partner_id

        if not customer:
            _logger.warning(f"Cannot send SMS: No customer for record {record}")
            return

        phone = customer.mobile or customer.phone
        if not phone:
            _logger.warning(f"Cannot send SMS: No phone number for customer {customer.name}")
            return

        body = self._render_template(self.sms_body, values)

        # Try to use Odoo's SMS module if available
        if 'sms.sms' in self.env:
            sms = self.env['sms.sms'].sudo().create({
                'number': phone,
                'body': body,
            })
            sms.send()
            _logger.info(f"SMS sent to {phone} for {self.notification_type}")
        else:
            _logger.warning("SMS module not installed. SMS not sent.")

    def _log_notification(self, record, values):
        """Log notification to history"""
        self.env['fleet.notification.log'].sudo().create({
            'template_id': self.id,
            'notification_type': self.notification_type,
            'record_model': record._name,
            'record_id': record.id,
            'customer_name': values.get('customer_name', ''),
            'customer_email': values.get('customer_email', ''),
            'customer_phone': values.get('customer_phone', ''),
            'sent_email': self.send_email,
            'sent_sms': self.send_sms,
        })


class FleetNotificationLog(models.Model):
    _name = 'fleet.notification.log'
    _description = 'Notification History Log'
    _order = 'create_date desc'

    template_id = fields.Many2one('fleet.notification.template', string='Template')
    notification_type = fields.Selection([
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('pickup_reminder', 'Pickup Reminder'),
        ('return_reminder', 'Return Reminder'),
        ('rental_started', 'Rental Started'),
        ('rental_completed', 'Rental Completed'),
        ('payment_received', 'Payment Received'),
        ('payment_due', 'Payment Due'),
        ('document_expiry', 'Document Expiry Reminder'),
        ('service_scheduled', 'Service Scheduled'),
        ('damage_report', 'Damage Report'),
        ('promo_offer', 'Promotional Offer'),
        ('welcome', 'Welcome Message'),
        ('thank_you', 'Thank You Message'),
    ], string='Notification Type')

    record_model = fields.Char('Record Model')
    record_id = fields.Integer('Record ID')

    customer_name = fields.Char('Customer Name')
    customer_email = fields.Char('Customer Email')
    customer_phone = fields.Char('Customer Phone')

    sent_email = fields.Boolean('Email Sent')
    sent_sms = fields.Boolean('SMS Sent')

    status = fields.Selection([
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ], string='Status', default='sent')

    error_message = fields.Text('Error Message')


class FleetNotificationScheduler(models.Model):
    _name = 'fleet.notification.scheduler'
    _description = 'Scheduled Notifications'

    template_id = fields.Many2one('fleet.notification.template', string='Template', required=True)
    record_model = fields.Char('Record Model', required=True)
    record_id = fields.Integer('Record ID', required=True)
    scheduled_date = fields.Datetime('Scheduled Date', required=True)
    sent = fields.Boolean('Sent', default=False)

    @api.model
    def _cron_send_scheduled_notifications(self):
        """Cron job to send scheduled notifications"""
        _logger.info("Running scheduled notifications cron job")

        pending = self.search([
            ('sent', '=', False),
            ('scheduled_date', '<=', fields.Datetime.now()),
        ])

        for schedule in pending:
            try:
                record = self.env[schedule.record_model].browse(schedule.record_id)
                if record.exists():
                    schedule.template_id.send_notification(record)
                schedule.sent = True
            except Exception as e:
                _logger.error(f"Failed to send scheduled notification: {e}")

        return True

    @api.model
    def _cron_send_pickup_reminders(self):
        """Send pickup reminders for bookings/rentals happening soon"""
        _logger.info("Running pickup reminder cron job")

        # Find template
        template = self.env['fleet.notification.template'].search([
            ('notification_type', '=', 'pickup_reminder'),
            ('active', '=', True),
        ], limit=1)

        if not template:
            return

        # Get rentals starting in the next 24 hours
        reminder_window = fields.Datetime.now() + timedelta(hours=template.hours_before)

        rentals = self.env['fleet.rental'].search([
            ('state', '=', 'confirmed'),
            ('start_date', '<=', reminder_window),
            ('start_date', '>', fields.Datetime.now()),
        ])

        for rental in rentals:
            # Check if reminder already sent
            existing = self.env['fleet.notification.log'].search([
                ('record_model', '=', 'fleet.rental'),
                ('record_id', '=', rental.id),
                ('notification_type', '=', 'pickup_reminder'),
            ], limit=1)

            if not existing:
                template.send_notification(rental)

        return True

    @api.model
    def _cron_send_return_reminders(self):
        """Send return reminders for rentals ending soon"""
        _logger.info("Running return reminder cron job")

        # Find template
        template = self.env['fleet.notification.template'].search([
            ('notification_type', '=', 'return_reminder'),
            ('active', '=', True),
        ], limit=1)

        if not template:
            return

        # Get rentals ending in the next 24 hours
        reminder_window = fields.Datetime.now() + timedelta(hours=template.hours_before)

        rentals = self.env['fleet.rental'].search([
            ('state', '=', 'in_progress'),
            ('end_date', '<=', reminder_window),
            ('end_date', '>', fields.Datetime.now()),
        ])

        for rental in rentals:
            # Check if reminder already sent
            existing = self.env['fleet.notification.log'].search([
                ('record_model', '=', 'fleet.rental'),
                ('record_id', '=', rental.id),
                ('notification_type', '=', 'return_reminder'),
            ], limit=1)

            if not existing:
                template.send_notification(rental)

        return True
