# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class ResPartnerTNumber(models.Model):
    _inherit = 'res.partner'

    # Japanese T-Number (適格請求書発行事業者登録番号)
    t_number = fields.Char(
        string='T-Number (登録番号)',
        size=14,
        help='Japanese Qualified Invoice Issuer Registration Number. '
             'Format: T + 13 digits (e.g., T1234567890123)'
    )
    is_qualified_invoice_issuer = fields.Boolean(
        string='Qualified Invoice Issuer (適格請求書発行事業者)',
        compute='_compute_is_qualified_invoice_issuer',
        store=True,
        help='Indicates if this partner is a registered Qualified Invoice Issuer in Japan'
    )

    @api.depends('t_number')
    def _compute_is_qualified_invoice_issuer(self):
        for partner in self:
            partner.is_qualified_invoice_issuer = bool(partner.t_number)

    @api.constrains('t_number')
    def _check_t_number_format(self):
        """Validate T-Number format: T + 13 digits"""
        t_number_pattern = re.compile(r'^T\d{13}$')
        for partner in self:
            if partner.t_number:
                # Remove any spaces or dashes
                cleaned_number = partner.t_number.replace(' ', '').replace('-', '').upper()
                if not t_number_pattern.match(cleaned_number):
                    raise ValidationError(_(
                        'Invalid T-Number format. '
                        'The T-Number must be in format: T + 13 digits (e.g., T1234567890123)'
                    ))
                # Update with cleaned format
                if partner.t_number != cleaned_number:
                    partner.t_number = cleaned_number

    @api.onchange('t_number')
    def _onchange_t_number(self):
        """Clean and format T-Number on change"""
        if self.t_number:
            # Auto-format: uppercase and remove spaces/dashes
            cleaned = self.t_number.replace(' ', '').replace('-', '').upper()
            # Add T prefix if not present and the rest is numeric
            if cleaned and not cleaned.startswith('T') and cleaned.isdigit():
                cleaned = 'T' + cleaned
            self.t_number = cleaned

    def action_lookup_t_number(self):
        """Open National Tax Agency website to verify T-Number"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.invoice-kohyo.nta.go.jp/index.html',
            'target': 'new',
        }
