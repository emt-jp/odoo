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
            if partner.t_number and not t_number_pattern.match(partner.t_number):
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
