# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import is_html_empty

_logger = logging.getLogger(__name__)


class AccountMoveExtended(models.Model):
    _inherit = 'account.move'

    stripe_payment_link_url = fields.Char(
        'Stripe Payment Link', copy=False, readonly=True,
        help='Permanent Stripe Payment Link URL for this invoice',
    )

    # Additional tracking fields
    approval_state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', tracking=True, copy=False)

    approved_by = fields.Many2one('res.users', string='Approved By', copy=False)
    approved_date = fields.Datetime('Approval Date', copy=False)
    rejection_reason = fields.Text('Rejection Reason', copy=False)

    # Custom reference fields
    internal_reference = fields.Char('Internal Reference', copy=False)
    department_name = fields.Char('Department', help='Department name for categorization')

    # Financial notes
    financial_notes = fields.Html('Financial Notes')

    # Recurring invoice fields
    is_recurring = fields.Boolean('Recurring Invoice', default=False)
    recurring_interval = fields.Integer('Recurring Interval', default=1)
    recurring_period = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], string='Recurring Period', default='months')
    next_recurring_date = fields.Date('Next Recurring Date')

    # Payment tracking
    payment_reminder_sent = fields.Boolean('Payment Reminder Sent', default=False)
    payment_reminder_date = fields.Date('Last Reminder Date')

    def action_post(self):
        """Override to auto-generate Stripe Payment Link on invoice post."""
        res = super().action_post()
        for move in self:
            if (move.move_type == 'out_invoice'
                    and move.company_id.stripe_enabled
                    and move.company_id.stripe_secret_key
                    and not move.stripe_payment_link_url):
                try:
                    move._create_stripe_payment_link()
                except Exception as e:
                    _logger.warning(
                        'Failed to create Stripe Payment Link for %s: %s',
                        move.name, e,
                    )
        return res

    def _create_stripe_payment_link(self):
        """Create a permanent Stripe Payment Link and embed it in narration."""
        self.ensure_one()
        try:
            import stripe
        except ImportError:
            _logger.warning('stripe library not installed, skipping payment link')
            return

        stripe.api_key = self.company_id.stripe_secret_key
        currency = self.currency_id.name.lower()

        # JPY has no decimal places; most others use cents
        zero_decimal = currency in (
            'jpy', 'krw', 'vnd', 'bif', 'clp', 'djf', 'gnf', 'kmf',
            'mga', 'pyg', 'rwf', 'ugx', 'xaf', 'xof', 'xpf',
        )
        amount = int(self.amount_total) if zero_decimal else int(self.amount_total * 100)

        # Create a one-off Stripe Product + Price + Payment Link
        product = stripe.Product.create(
            name=f'Invoice {self.name}',
            metadata={
                'odoo_invoice_id': str(self.id),
                'odoo_invoice_name': self.name,
            },
        )

        price = stripe.Price.create(
            product=product.id,
            unit_amount=amount,
            currency=currency,
        )

        payment_link = stripe.PaymentLink.create(
            line_items=[{'price': price.id, 'quantity': 1}],
            metadata={
                'odoo_invoice_id': str(self.id),
                'odoo_invoice_name': self.name,
                'odoo_partner_id': str(self.partner_id.id),
            },
        )

        url = payment_link.url
        self.stripe_payment_link_url = url

        # Embed in narration (HTML)
        link_html = (
            '<div style="margin-top:10px; padding:8px 12px; '
            'border:1px solid #dee2e6; border-radius:4px; background:#f8f9fa; '
            'font-size:11px;">'
            '<strong>💳 Pay Online / オンライン決済</strong><br/>'
            f'<a href="{url}" target="_blank" '
            'style="color:#0d6efd; word-break:break-all;">'
            f'{url}</a></div>'
        )
        existing = self.narration or ''
        if is_html_empty(existing):
            self.narration = link_html
        else:
            self.narration = existing + link_html

        # Also record as payment.transaction.custom
        self.env['payment.transaction.custom'].create({
            'invoice_id': self.id,
            'amount': self.amount_total,
            'provider': 'stripe',
            'provider_reference': payment_link.id,
            'payment_url': url,
            'state': 'pending',
        })

        _logger.info(
            'Stripe Payment Link created for %s: %s', self.name, url,
        )

    def action_approve(self):
        """Approve the journal entry"""
        for move in self:
            if move.approval_state == 'pending':
                move.write({
                    'approval_state': 'approved',
                    'approved_by': self.env.user.id,
                    'approved_date': fields.Datetime.now(),
                })
        return True

    def action_reject(self):
        """Open rejection wizard"""
        return {
            'name': _('Reject Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_id': self.id},
        }

    def action_request_approval(self):
        """Request approval for this entry"""
        for move in self:
            move.approval_state = 'pending'
        return True

    def action_send_payment_reminder(self):
        """Send payment reminder email"""
        self.ensure_one()
        # This can be extended to send actual emails
        self.write({
            'payment_reminder_sent': True,
            'payment_reminder_date': fields.Date.today(),
        })
        return True

    def action_create_recurring(self):
        """Create next recurring invoice"""
        self.ensure_one()
        if not self.is_recurring or not self.next_recurring_date:
            return False

        # Copy the invoice
        new_move = self.copy({
            'date': self.next_recurring_date,
            'invoice_date': self.next_recurring_date,
        })

        # Calculate next recurring date
        from dateutil.relativedelta import relativedelta
        if self.recurring_period == 'days':
            delta = relativedelta(days=self.recurring_interval)
        elif self.recurring_period == 'weeks':
            delta = relativedelta(weeks=self.recurring_interval)
        elif self.recurring_period == 'months':
            delta = relativedelta(months=self.recurring_interval)
        else:
            delta = relativedelta(years=self.recurring_interval)

        self.next_recurring_date = self.next_recurring_date + delta

        return {
            'name': _('Recurring Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': new_move.id,
            'view_mode': 'form',
        }


class AccountMoveLineExtended(models.Model):
    _inherit = 'account.move.line'

    # Additional analysis fields
    cost_center_id = fields.Many2one('account.analytic.account', string='Cost Center')
    project_name = fields.Char('Project', help='Project name for categorization')

    # Budget tracking
    budget_line_id = fields.Many2one('account.budget.line', string='Budget Line')

    # Notes
    line_notes = fields.Char('Line Notes')


