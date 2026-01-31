# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date

class HrPayrollContract(models.Model):
    _name = 'hr.payroll.contract'
    _description = 'Payroll Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    # Basic Information
    name = fields.Char('Contract Reference', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True, ondelete='cascade')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', string='Department', store=True, readonly=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', string='Job Position', store=True, readonly=True)

    # Contract Period
    date_start = fields.Date('Start Date', required=True, default=fields.Date.today, tracking=True)
    date_end = fields.Date('End Date', tracking=True, help="End date of the contract (if it's a fixed-term contract)")

    # Contract Status
    state = fields.Selection([
        ('draft', 'New'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True, copy=False)
    active = fields.Boolean('Active', default=True)

    # Salary Structure
    struct_id = fields.Many2one('hr.salary.structure', string='Salary Structure', tracking=True)

    # Currency
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # Salary Components - Earnings
    wage = fields.Monetary('Basic Salary', required=True, help="Employee's monthly basic salary", tracking=True)
    hra = fields.Monetary('House Rent Allowance (HRA)', compute='_compute_hra', store=True, readonly=False, tracking=True)
    da = fields.Monetary('Dearness Allowance (DA)', compute='_compute_da', store=True, readonly=False, tracking=True)
    transport_allowance = fields.Monetary('Transport Allowance', default=0.0, tracking=True)
    medical_allowance = fields.Monetary('Medical Allowance', default=0.0, tracking=True)
    special_allowance = fields.Monetary('Special Allowance', default=0.0, tracking=True)
    other_allowance = fields.Monetary('Other Allowance', default=0.0, tracking=True)

    # Calculated Fields
    gross_salary = fields.Monetary('Gross Salary', compute='_compute_gross_salary', store=True)

    # Deductions Configuration
    pf_employee = fields.Float('PF Employee (%)', default=12.0, help="Employee PF contribution percentage")
    pf_employer = fields.Float('PF Employer (%)', default=12.0, help="Employer PF contribution percentage")
    esi_employee = fields.Float('ESI Employee (%)', default=0.75, help="Employee ESI contribution percentage")
    esi_employer = fields.Float('ESI Employer (%)', default=3.25, help="Employer ESI contribution percentage")
    professional_tax = fields.Monetary('Professional Tax', default=200.0)

    # Tax Configuration
    tax_regime = fields.Selection([
        ('old', 'Old Tax Regime'),
        ('new', 'New Tax Regime'),
    ], string='Tax Regime', default='new', required=True)

    @api.depends('wage')
    def _compute_hra(self):
        """HRA is typically 40% of basic salary"""
        for contract in self:
            if contract.wage:
                contract.hra = contract.wage * 0.40
            else:
                contract.hra = 0.0

    @api.depends('wage')
    def _compute_da(self):
        """DA is typically 20% of basic salary"""
        for contract in self:
            if contract.wage:
                contract.da = contract.wage * 0.20
            else:
                contract.da = 0.0

    @api.depends('wage', 'hra', 'da', 'transport_allowance', 'medical_allowance',
                 'special_allowance', 'other_allowance')
    def _compute_gross_salary(self):
        """Calculate gross salary from all components"""
        for contract in self:
            contract.gross_salary = (
                contract.wage +
                contract.hra +
                contract.da +
                contract.transport_allowance +
                contract.medical_allowance +
                contract.special_allowance +
                contract.other_allowance
            )

    @api.constrains('wage', 'hra', 'da', 'transport_allowance', 'medical_allowance',
                    'special_allowance', 'other_allowance')
    def _check_salary_components(self):
        """Validate salary components are positive"""
        for contract in self:
            if contract.wage < 0:
                raise ValidationError(_('Basic salary cannot be negative.'))
            if any(amount < 0 for amount in [contract.hra, contract.da, contract.transport_allowance,
                                              contract.medical_allowance, contract.special_allowance,
                                              contract.other_allowance]):
                raise ValidationError(_('Allowances cannot be negative.'))

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        """Validate contract dates"""
        for contract in self:
            if contract.date_end and contract.date_start and contract.date_end < contract.date_start:
                raise ValidationError(_('Contract end date must be greater than or equal to start date.'))

    def name_get(self):
        """Custom display name for contract"""
        result = []
        for contract in self:
            name = f"{contract.name} - {contract.employee_id.name}"
            result.append((contract.id, name))
        return result

    def action_start_contract(self):
        """Activate the contract"""
        self.write({'state': 'open'})

    def action_close_contract(self):
        """Close/Expire the contract"""
        self.write({'state': 'close', 'active': False})

    def action_cancel_contract(self):
        """Cancel the contract"""
        self.write({'state': 'cancel', 'active': False})
