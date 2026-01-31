# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    contract_ids = fields.One2many('hr.payroll.contract', 'employee_id', string='Contracts')
    contract_count = fields.Integer('Contract Count', compute='_compute_contract_count')
    payslip_count = fields.Integer('Payslip Count', compute='_compute_payslip_count')
    current_contract_id = fields.Many2one('hr.payroll.contract', string='Current Contract',
                                          compute='_compute_current_contract', store=False)

    @api.depends('contract_ids', 'contract_ids.state', 'contract_ids.date_start', 'contract_ids.date_end')
    def _compute_current_contract(self):
        """Get the currently active contract"""
        for employee in self:
            contracts = employee.contract_ids.filtered(
                lambda c: c.state == 'open'
            ).sorted(key=lambda c: c.date_start, reverse=True)
            employee.current_contract_id = contracts[0] if contracts else False

    @api.depends('contract_ids')
    def _compute_contract_count(self):
        for employee in self:
            employee.contract_count = len(employee.contract_ids)

    @api.depends()
    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = self.env['hr.payslip'].search_count([
                ('employee_id', '=', employee.id),
            ])

    def action_view_contracts(self):
        """View employee contracts"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contracts'),
            'res_model': 'hr.payroll.contract',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_view_payslips(self):
        """View employee payslips"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payslips'),
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
