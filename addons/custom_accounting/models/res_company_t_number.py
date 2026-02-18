# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class ResCompanyTNumber(models.Model):
    _inherit = 'res.company'

    # Japanese T-Number for the company (適格請求書発行事業者登録番号)
    t_number = fields.Char(
        string='T-Number (登録番号)',
        size=14,
        help='Company\'s Japanese Qualified Invoice Issuer Registration Number. '
             'Format: T + 13 digits (e.g., T1234567890123)'
    )
    is_qualified_invoice_issuer = fields.Boolean(
        string='Qualified Invoice Issuer (適格請求書発行事業者)',
        compute='_compute_is_qualified_invoice_issuer',
        store=True,
        help='Indicates if this company is a registered Qualified Invoice Issuer in Japan'
    )
    use_japanese_invoice_system = fields.Boolean(
        string='Use Japanese Invoice System (インボイス制度)',
        default=False,
        help='Enable Japanese Qualified Invoice System features'
    )

    # Hanko (会社印) - Company Seal
    hanko_image = fields.Binary(
        string='Hanko/Company Seal (会社印)',
        help='Upload your company seal (Hanko) image. This will be displayed on receipts when invoices are paid.'
    )
    hanko_image_filename = fields.Char(string='Hanko Filename')

    # Payment Provider Settings
    enable_online_payment = fields.Boolean(
        string='Enable Online Payment',
        default=False,
        help='Allow customers to pay invoices online'
    )

    # Stripe Settings
    stripe_enabled = fields.Boolean(string='Enable Stripe', default=False)
    stripe_publishable_key = fields.Char(string='Stripe Publishable Key')
    stripe_secret_key = fields.Char(string='Stripe Secret Key')
    stripe_webhook_secret = fields.Char(string='Stripe Webhook Secret')

    # PayPay Settings
    paypay_enabled = fields.Boolean(string='Enable PayPay', default=False)
    paypay_api_key = fields.Char(string='PayPay API Key')
    paypay_api_secret = fields.Char(string='PayPay API Secret')
    paypay_merchant_id = fields.Char(string='PayPay Merchant ID')
    paypay_production = fields.Boolean(string='PayPay Production Mode', default=False)

    # AirPay Settings
    airpay_enabled = fields.Boolean(string='Enable AirPay', default=False)
    airpay_api_key = fields.Char(string='AirPay API Key')
    airpay_api_secret = fields.Char(string='AirPay API Secret')
    airpay_merchant_id = fields.Char(string='AirPay Merchant ID')

    @api.depends('t_number')
    def _compute_is_qualified_invoice_issuer(self):
        for company in self:
            company.is_qualified_invoice_issuer = bool(company.t_number)

    @api.constrains('t_number')
    def _check_t_number_format(self):
        """Validate T-Number format: T + 13 digits"""
        t_number_pattern = re.compile(r'^T\d{13}$')
        for company in self:
            if company.t_number and not t_number_pattern.match(company.t_number):
                raise ValidationError(_(
                    'Invalid T-Number format. '
                    'The T-Number must be in format: T + 13 digits (e.g., T1234567890123)'
                ))

    def write(self, vals):
        """Clean T-Number formatting before save"""
        if 't_number' in vals and vals['t_number']:
            cleaned = vals['t_number'].replace(' ', '').replace('-', '').upper()
            if cleaned and not cleaned.startswith('T') and cleaned.isdigit():
                cleaned = 'T' + cleaned
            vals['t_number'] = cleaned
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """Clean T-Number formatting on create"""
        for vals in vals_list:
            if vals.get('t_number'):
                cleaned = vals['t_number'].replace(' ', '').replace('-', '').upper()
                if cleaned and not cleaned.startswith('T') and cleaned.isdigit():
                    cleaned = 'T' + cleaned
                vals['t_number'] = cleaned
        return super().create(vals_list)

    @api.onchange('t_number')
    def _onchange_t_number(self):
        """Clean and format T-Number on change"""
        if self.t_number:
            cleaned = self.t_number.replace(' ', '').replace('-', '').upper()
            if cleaned and not cleaned.startswith('T') and cleaned.isdigit():
                cleaned = 'T' + cleaned
            self.t_number = cleaned
            # Auto-enable Japanese invoice system when T-Number is set
            if cleaned:
                self.use_japanese_invoice_system = True
