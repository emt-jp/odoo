# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMoveTNumber(models.Model):
    _inherit = 'account.move'

    # Japanese Qualified Invoice System fields
    is_qualified_invoice = fields.Boolean(
        string='Qualified Invoice (適格請求書)',
        compute='_compute_is_qualified_invoice',
        store=True,
        help='Indicates if this is a Qualified Invoice under Japanese tax law'
    )
    issuer_t_number = fields.Char(
        string='Issuer T-Number',
        compute='_compute_issuer_t_number',
        store=True,
        help='T-Number of the invoice issuer'
    )
    recipient_t_number = fields.Char(
        string='Recipient T-Number',
        related='partner_id.t_number',
        readonly=True,
        help='T-Number of the invoice recipient (if registered)'
    )

    # Tax breakdown by rate (8% reduced / 10% standard)
    tax_amount_reduced = fields.Monetary(
        string='Reduced Rate Tax (8%)',
        compute='_compute_tax_breakdown',
        currency_field='currency_id',
        help='Total tax amount at reduced rate (8%)'
    )
    tax_base_reduced = fields.Monetary(
        string='Reduced Rate Base',
        compute='_compute_tax_breakdown',
        currency_field='currency_id',
        help='Tax base amount at reduced rate (8%)'
    )
    tax_amount_standard = fields.Monetary(
        string='Standard Rate Tax (10%)',
        compute='_compute_tax_breakdown',
        currency_field='currency_id',
        help='Total tax amount at standard rate (10%)'
    )
    tax_base_standard = fields.Monetary(
        string='Standard Rate Base',
        compute='_compute_tax_breakdown',
        currency_field='currency_id',
        help='Tax base amount at standard rate (10%)'
    )
    has_multiple_tax_rates = fields.Boolean(
        string='Multiple Tax Rates',
        compute='_compute_tax_breakdown',
        help='Indicates if invoice has both 8% and 10% tax rates'
    )

    @api.depends('company_id', 'company_id.t_number', 'company_id.use_japanese_invoice_system')
    def _compute_is_qualified_invoice(self):
        for move in self:
            move.is_qualified_invoice = (
                move.company_id.use_japanese_invoice_system and
                bool(move.company_id.t_number)
            )

    @api.depends('company_id', 'company_id.t_number')
    def _compute_issuer_t_number(self):
        for move in self:
            move.issuer_t_number = move.company_id.t_number

    @api.depends('invoice_line_ids', 'invoice_line_ids.tax_ids', 'invoice_line_ids.price_subtotal')
    def _compute_tax_breakdown(self):
        for move in self:
            reduced_tax = 0.0
            reduced_base = 0.0
            standard_tax = 0.0
            standard_base = 0.0

            for line in move.invoice_line_ids:
                for tax in line.tax_ids:
                    # Determine tax rate category
                    tax_amount = tax.amount if hasattr(tax, 'amount') else 0
                    line_tax_amount = line.price_subtotal * (tax_amount / 100) if tax_amount else 0

                    if tax_amount == 8:
                        # 8% reduced rate (food, newspapers, etc.)
                        reduced_tax += line_tax_amount
                        reduced_base += line.price_subtotal
                    elif tax_amount == 10:
                        # 10% standard rate
                        standard_tax += line_tax_amount
                        standard_base += line.price_subtotal
                    elif 7 <= tax_amount <= 9:
                        # Catch 8% variations
                        reduced_tax += line_tax_amount
                        reduced_base += line.price_subtotal
                    elif 9 < tax_amount <= 11:
                        # Catch 10% variations
                        standard_tax += line_tax_amount
                        standard_base += line.price_subtotal

            move.tax_amount_reduced = reduced_tax
            move.tax_base_reduced = reduced_base
            move.tax_amount_standard = standard_tax
            move.tax_base_standard = standard_base
            move.has_multiple_tax_rates = bool(reduced_base) and bool(standard_base)

    def get_tax_breakdown_summary(self):
        """Return formatted tax breakdown for reports"""
        self.ensure_one()
        summary = []

        if self.tax_base_reduced:
            summary.append({
                'rate': '8%',
                'rate_name': _('Reduced Rate (軽減税率)'),
                'base': self.tax_base_reduced,
                'tax': self.tax_amount_reduced,
            })

        if self.tax_base_standard:
            summary.append({
                'rate': '10%',
                'rate_name': _('Standard Rate (標準税率)'),
                'base': self.tax_base_standard,
                'tax': self.tax_amount_standard,
            })

        return summary

    def action_print_qualified_invoice(self):
        """Print Japanese Qualified Invoice format"""
        self.ensure_one()
        if not self.is_qualified_invoice:
            raise UserError(_(
                'This invoice is not a Qualified Invoice. '
                'Please ensure your company has a valid T-Number configured.'
            ))
        return self.env.ref('custom_accounting.action_report_invoice_t_number').report_action(self)


class AccountMoveLineTNumber(models.Model):
    _inherit = 'account.move.line'

    # Flag for reduced tax rate items (8%)
    is_reduced_tax_rate = fields.Boolean(
        string='Reduced Tax Rate (軽減税率)',
        compute='_compute_is_reduced_tax_rate',
        store=True,
        help='Indicates if this line is subject to reduced tax rate (8%)'
    )

    @api.depends('tax_ids')
    def _compute_is_reduced_tax_rate(self):
        for line in self:
            is_reduced = False
            for tax in line.tax_ids:
                tax_amount = tax.amount if hasattr(tax, 'amount') else 0
                if 7 <= tax_amount <= 9:  # 8% or similar
                    is_reduced = True
                    break
            line.is_reduced_tax_rate = is_reduced
