# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import uuid
import hashlib
import hmac
import json
import logging
import requests
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _name = 'payment.transaction.custom'
    _description = 'Custom Payment Transaction'
    _order = 'create_date desc'

    name = fields.Char('Reference', required=True, default=lambda self: str(uuid.uuid4())[:8].upper())
    invoice_id = fields.Many2one('account.move', string='Invoice', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='invoice_id.partner_id', store=True)
    company_id = fields.Many2one('res.company', related='invoice_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id')

    amount = fields.Monetary('Amount', required=True)
    provider = fields.Selection([
        ('stripe', 'Stripe'),
        ('paypay', 'PayPay'),
        ('airpay', 'AirPay'),
    ], string='Payment Provider', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('done', 'Paid'),
        ('cancelled', 'Cancelled'),
        ('error', 'Error'),
    ], string='Status', default='draft')

    provider_reference = fields.Char('Provider Reference')
    payment_url = fields.Char('Payment URL')
    payment_date = fields.Datetime('Payment Date')
    error_message = fields.Text('Error Message')

    # Webhook data
    webhook_data = fields.Text('Webhook Data')

    def action_generate_payment_link(self):
        """Generate payment link based on provider"""
        self.ensure_one()
        if self.provider == 'stripe':
            return self._generate_stripe_link()
        elif self.provider == 'paypay':
            return self._generate_paypay_link()
        elif self.provider == 'airpay':
            return self._generate_airpay_link()

    def _generate_stripe_link(self):
        """Generate Stripe Checkout Session"""
        company = self.company_id
        if not company.stripe_enabled or not company.stripe_secret_key:
            raise UserError(_('Stripe is not configured for this company'))

        try:
            import stripe
            stripe.api_key = company.stripe_secret_key

            # Get base URL
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': self.currency_id.name.lower(),
                        'unit_amount': int(self.amount * 100),  # Stripe uses cents
                        'product_data': {
                            'name': f'Invoice {self.invoice_id.name}',
                            'description': f'Payment for invoice {self.invoice_id.name}',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'{base_url}/payment/success?transaction_id={self.id}',
                cancel_url=f'{base_url}/payment/cancel?transaction_id={self.id}',
                metadata={
                    'transaction_id': str(self.id),
                    'invoice_id': str(self.invoice_id.id),
                },
            )

            self.write({
                'provider_reference': session.id,
                'payment_url': session.url,
                'state': 'pending',
            })

            return session.url

        except ImportError:
            raise UserError(_('Stripe library not installed. Please install: pip install stripe'))
        except Exception as e:
            self.write({'state': 'error', 'error_message': str(e)})
            raise UserError(_('Failed to create Stripe session: %s') % str(e))

    def _generate_paypay_link(self):
        """Generate PayPay payment link"""
        company = self.company_id
        if not company.paypay_enabled or not company.paypay_api_key:
            raise UserError(_('PayPay is not configured for this company'))

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        # PayPay API endpoint
        if company.paypay_production:
            api_url = 'https://api.paypay.ne.jp/v2/codes'
        else:
            api_url = 'https://stg-api.paypay.ne.jp/v2/codes'

        merchant_payment_id = f'{self.invoice_id.name}-{self.name}'

        payload = {
            'merchantPaymentId': merchant_payment_id,
            'amount': {
                'amount': int(self.amount),
                'currency': 'JPY'
            },
            'codeType': 'ORDER_QR',
            'orderDescription': f'Invoice {self.invoice_id.name}',
            'isAuthorization': False,
            'redirectUrl': f'{base_url}/payment/paypay/callback?transaction_id={self.id}',
            'redirectType': 'WEB_LINK',
        }

        headers = {
            'Authorization': f'Bearer {company.paypay_api_key}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            result = response.json()

            if response.status_code == 200 and result.get('resultInfo', {}).get('code') == 'SUCCESS':
                payment_url = result.get('data', {}).get('url')
                self.write({
                    'provider_reference': merchant_payment_id,
                    'payment_url': payment_url,
                    'state': 'pending',
                })
                return payment_url
            else:
                error_msg = result.get('resultInfo', {}).get('message', 'Unknown error')
                self.write({'state': 'error', 'error_message': error_msg})
                raise UserError(_('PayPay Error: %s') % error_msg)

        except requests.exceptions.RequestException as e:
            self.write({'state': 'error', 'error_message': str(e)})
            raise UserError(_('Failed to connect to PayPay: %s') % str(e))

    def _generate_airpay_link(self):
        """Generate AirPay payment link"""
        company = self.company_id
        if not company.airpay_enabled or not company.airpay_api_key:
            raise UserError(_('AirPay is not configured for this company'))

        # AirPay typically requires in-store terminal integration
        # For online payments, generate a reference code
        payment_ref = f'AIR-{self.invoice_id.name}-{self.name}'

        self.write({
            'provider_reference': payment_ref,
            'state': 'pending',
            'error_message': _('AirPay requires terminal integration. Use reference: %s') % payment_ref,
        })

        return False  # AirPay doesn't have direct payment links

    def action_confirm_payment(self):
        """Manually confirm payment and mark invoice as paid"""
        self.ensure_one()
        self._process_payment_success()

    def _process_payment_success(self, webhook_data=None):
        """Process successful payment"""
        self.write({
            'state': 'done',
            'payment_date': fields.Datetime.now(),
            'webhook_data': json.dumps(webhook_data) if webhook_data else False,
        })

        # Create payment and reconcile with invoice
        self._create_payment_and_reconcile()

    def _create_payment_and_reconcile(self):
        """Create account.payment and reconcile with invoice"""
        self.ensure_one()
        invoice = self.invoice_id

        if invoice.payment_state == 'paid':
            return  # Already paid

        # Find a bank journal
        journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

        if not journal:
            journal = self.env['account.journal'].search([
                ('type', '=', 'cash'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)

        if not journal:
            _logger.warning('No bank/cash journal found for payment reconciliation')
            return

        # Find payment method line on the journal (Odoo 17+ uses payment_method_line_id)
        payment_method_line = journal.inbound_payment_method_line_ids[:1]
        if not payment_method_line:
            _logger.warning('No inbound payment method line found on journal %s', journal.name)
            return

        # Create payment
        payment_vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'journal_id': journal.id,
            'payment_method_line_id': payment_method_line.id,
            'ref': f'{self.provider.upper()} - {self.provider_reference}',
        }

        try:
            payment = self.env['account.payment'].create(payment_vals)
            payment.action_post()

            # Reconcile with invoice
            invoice_line = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )
            payment_line = payment.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )

            if invoice_line and payment_line:
                (invoice_line + payment_line).reconcile()
                _logger.info('Payment %s reconciled with invoice %s', payment.name, invoice.name)

        except Exception as e:
            _logger.error('Failed to create/reconcile payment: %s', e)


class AccountMovePayment(models.Model):
    _inherit = 'account.move'

    # Payment integration fields
    payment_transaction_ids = fields.One2many(
        'payment.transaction.custom', 'invoice_id', string='Payment Transactions'
    )
    payment_link_stripe = fields.Char('Stripe Payment Link', compute='_compute_payment_links')
    payment_link_paypay = fields.Char('PayPay Payment Link', compute='_compute_payment_links')
    payment_link_airpay = fields.Char('AirPay Payment Link', compute='_compute_payment_links')

    has_online_payment = fields.Boolean(
        'Online Payment Available',
        compute='_compute_has_online_payment'
    )

    @api.depends('company_id.enable_online_payment')
    def _compute_has_online_payment(self):
        for move in self:
            move.has_online_payment = move.company_id.enable_online_payment

    @api.depends('payment_transaction_ids')
    def _compute_payment_links(self):
        for move in self:
            stripe_tx = move.payment_transaction_ids.filtered(
                lambda t: t.provider == 'stripe' and t.state == 'pending'
            )[:1]
            paypay_tx = move.payment_transaction_ids.filtered(
                lambda t: t.provider == 'paypay' and t.state == 'pending'
            )[:1]
            airpay_tx = move.payment_transaction_ids.filtered(
                lambda t: t.provider == 'airpay' and t.state == 'pending'
            )[:1]

            move.payment_link_stripe = stripe_tx.payment_url if stripe_tx else False
            move.payment_link_paypay = paypay_tx.payment_url if paypay_tx else False
            move.payment_link_airpay = airpay_tx.payment_url if airpay_tx else False

    def action_generate_payment_links(self):
        """Generate payment links for all enabled providers"""
        self.ensure_one()

        if self.state != 'posted':
            raise UserError(_('Invoice must be posted before generating payment links'))

        if self.payment_state == 'paid':
            raise UserError(_('Invoice is already paid'))

        company = self.company_id
        links = []

        # Generate Stripe link
        if company.stripe_enabled:
            tx = self.env['payment.transaction.custom'].create({
                'invoice_id': self.id,
                'amount': self.amount_residual,
                'provider': 'stripe',
            })
            url = tx.action_generate_payment_link()
            if url:
                links.append(('Stripe', url))

        # Generate PayPay link
        if company.paypay_enabled:
            tx = self.env['payment.transaction.custom'].create({
                'invoice_id': self.id,
                'amount': self.amount_residual,
                'provider': 'paypay',
            })
            url = tx.action_generate_payment_link()
            if url:
                links.append(('PayPay', url))

        # Generate AirPay reference
        if company.airpay_enabled:
            tx = self.env['payment.transaction.custom'].create({
                'invoice_id': self.id,
                'amount': self.amount_residual,
                'provider': 'airpay',
            })
            tx.action_generate_payment_link()

        if not links:
            raise UserError(_('No payment providers are configured. Please configure payment settings.'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Payment Links Generated'),
                'message': _('Payment links have been generated successfully.'),
                'type': 'success',
            }
        }

    def action_send_payment_link(self):
        """Send payment link to customer via email"""
        self.ensure_one()

        # Generate links if not exists
        if not self.payment_transaction_ids.filtered(lambda t: t.state == 'pending'):
            self.action_generate_payment_links()

        # Get the email template
        template = self.env.ref('custom_accounting.email_template_payment_link', raise_if_not_found=False)

        if template:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Send Payment Link'),
                'res_model': 'mail.compose.message',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_model': 'account.move',
                    'default_res_ids': [self.id],
                    'default_template_id': template.id,
                    'default_composition_mode': 'comment',
                },
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Email Template Missing'),
                    'message': _('Payment link email template not found.'),
                    'type': 'warning',
                }
            }
