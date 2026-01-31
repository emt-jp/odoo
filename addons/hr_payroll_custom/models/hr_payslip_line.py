# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrPayslipLine(models.Model):
    _name = 'hr.payslip.line'
    _description = 'Payslip Line'
    _order = 'sequence, id'

    name = fields.Char('Description', required=True)
    code = fields.Char('Code', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Payslip', required=True, ondelete='cascade')
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Salary Rule', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    contract_id = fields.Many2one('hr.payroll.contract', string='Contract', required=True)

    category_id = fields.Many2one('hr.salary.rule.category', string='Category', required=True)
    sequence = fields.Integer('Sequence', default=10)

    rate = fields.Float('Rate', digits='Payroll Rate', default=1.0)
    quantity = fields.Float('Quantity', digits='Payroll', default=1.0)
    total = fields.Monetary('Total', compute='_compute_total', store=True, currency_field='currency_id')

    company_id = fields.Many2one('res.company', related='payslip_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', related='payslip_id.currency_id', store=True)

    @api.depends('rate', 'quantity')
    def _compute_total(self):
        """Calculate line total"""
        for line in self:
            line.total = line.rate * line.quantity


class HrSalaryRuleCategory(models.Model):
    _name = 'hr.salary.rule.category'
    _description = 'Salary Rule Category'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    code = fields.Char('Code', required=True, unique=True)
    sequence = fields.Integer('Sequence', default=10)
    note = fields.Text('Description')
