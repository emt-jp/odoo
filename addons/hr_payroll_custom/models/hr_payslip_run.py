# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrPayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _description = 'Payslip Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char('Name', required=True, tracking=True)
    date_start = fields.Date('Date From', required=True, tracking=True,
                              default=lambda self: fields.Date.today().replace(day=1))
    date_end = fields.Date('Date To', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('close', 'Close'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Payslips')

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.company)

    # Statistics
    payslip_count = fields.Integer('Payslip Count', compute='_compute_payslip_count')
    total_amount = fields.Monetary('Total Amount', compute='_compute_total_amount',
                                     currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    @api.depends('slip_ids')
    def _compute_payslip_count(self):
        for batch in self:
            batch.payslip_count = len(batch.slip_ids)

    @api.depends('slip_ids.net_wage')
    def _compute_total_amount(self):
        for batch in self:
            batch.total_amount = sum(batch.slip_ids.filtered(lambda s: s.state == 'done').mapped('net_wage'))

    def action_generate_payslips(self):
        """Generate payslips for all employees with active contracts"""
        self.ensure_one()

        # Get all active contracts
        contracts = self.env['hr.payroll.contract'].search([
            ('state', '=', 'open'),
            ('date_start', '<=', self.date_end),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', self.date_start),
        ])

        if not contracts:
            raise UserError(_('No active contracts found for this period.'))

        # Generate payslips
        payslips = self.env['hr.payslip']
        for contract in contracts:
            # Check if payslip already exists
            existing = self.env['hr.payslip'].search([
                ('employee_id', '=', contract.employee_id.id),
                ('date_from', '=', self.date_start),
                ('date_to', '=', self.date_end),
            ])
            if existing:
                continue

            payslip_vals = {
                'name': f"Payslip for {contract.employee_id.name} - {self.date_start.strftime('%B %Y')}",
                'employee_id': contract.employee_id.id,
                'contract_id': contract.id,
                'date_from': self.date_start,
                'date_to': self.date_end,
                'payslip_run_id': self.id,
            }
            payslip = self.env['hr.payslip'].create(payslip_vals)
            payslips |= payslip

        if not payslips:
            raise UserError(_('All payslips for this period have already been generated.'))

        # Compute all payslips
        payslips.action_compute_sheet()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('%d payslips have been generated and computed.') % len(payslips),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_close(self):
        """Close batch and verify all payslips"""
        for batch in self:
            if not batch.slip_ids:
                raise UserError(_('No payslips in this batch.'))

            draft_slips = batch.slip_ids.filtered(lambda s: s.state == 'draft')
            if draft_slips:
                raise UserError(_('All payslips must be verified before closing the batch.'))

        return self.write({'state': 'close'})

    def action_draft(self):
        """Reopen batch"""
        return self.write({'state': 'draft'})

    def action_view_payslips(self):
        """View payslips in this batch"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payslips'),
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('payslip_run_id', '=', self.id)],
            'context': {'default_payslip_run_id': self.id},
        }
