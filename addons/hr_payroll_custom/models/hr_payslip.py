# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta

class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _description = 'Employee Payslip'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char('Payslip Name', required=True, readonly=True,
                       states={'draft': [('readonly', False)]})
    number = fields.Char('Reference', readonly=True, copy=False,
                         states={'draft': [('readonly', False)]})

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,
                                   readonly=True, states={'draft': [('readonly', False)]},
                                   tracking=True)
    contract_id = fields.Many2one('hr.payroll.contract', string='Contract', required=True,
                                   readonly=True, states={'draft': [('readonly', False)]},
                                   domain="[('employee_id', '=', employee_id), ('state', '=', 'open')]")

    date_from = fields.Date('Date From', required=True, readonly=True,
                             states={'draft': [('readonly', False)]},
                             default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('Date To', required=True, readonly=True,
                           states={'draft': [('readonly', False)]},
                           default=lambda self: (fields.Date.today().replace(day=1) + relativedelta(months=1, days=-1)))

    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting for Approval'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    line_ids = fields.One2many('hr.payslip.line', 'payslip_id', string='Payslip Lines',
                                readonly=True, states={'draft': [('readonly', False)]})

    # Computed amounts
    basic_wage = fields.Monetary('Basic Salary', compute='_compute_amounts', store=True,
                                   currency_field='currency_id')
    gross_wage = fields.Monetary('Gross Salary', compute='_compute_amounts', store=True,
                                   currency_field='currency_id')
    net_wage = fields.Monetary('Net Salary', compute='_compute_amounts', store=True,
                                currency_field='currency_id')
    total_deductions = fields.Monetary('Total Deductions', compute='_compute_amounts', store=True,
                                        currency_field='currency_id')

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   related='company_id.currency_id', readonly=True)

    payslip_run_id = fields.Many2one('hr.payslip.run', string='Payslip Batch',
                                      readonly=True, copy=False, ondelete='cascade')

    # Tracking fields
    struct_id = fields.Many2one('hr.salary.structure', string='Salary Structure',
                                 readonly=True, states={'draft': [('readonly', False)]})

    paid = fields.Boolean('Made Payment Entry', readonly=True, copy=False)

    # Portal access
    def _compute_access_url(self):
        super()._compute_access_url()
        for payslip in self:
            payslip.access_url = f'/my/payslips/{payslip.id}'

    @api.depends('line_ids.total', 'contract_id.wage')
    def _compute_amounts(self):
        """Calculate payslip amounts from lines"""
        for payslip in self:
            payslip.basic_wage = payslip.contract_id.wage if payslip.contract_id else 0.0

            earning_lines = payslip.line_ids.filtered(lambda l: l.category_id.code == 'EARNING')
            deduction_lines = payslip.line_ids.filtered(lambda l: l.category_id.code == 'DEDUCTION')

            payslip.gross_wage = sum(earning_lines.mapped('total'))
            payslip.total_deductions = sum(deduction_lines.mapped('total'))
            payslip.net_wage = payslip.gross_wage - payslip.total_deductions

    @api.onchange('employee_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        """Auto-fill contract and name when employee changes"""
        if self.employee_id:
            contracts = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open'),
                ('date_start', '<=', self.date_to),
                '|',
                ('date_end', '=', False),
                ('date_end', '>=', self.date_from),
            ], limit=1)

            if contracts:
                self.contract_id = contracts[0]

            # Auto-generate name
            if self.date_from and self.date_to:
                self.name = f"Payslip for {self.employee_id.name} - {self.date_from.strftime('%B %Y')}"

    def action_compute_sheet(self):
        """Compute payslip lines from salary rules"""
        for payslip in self:
            if not payslip.contract_id:
                raise UserError(_('No contract found for employee %s') % payslip.employee_id.name)

            # Clear existing lines
            payslip.line_ids.unlink()

            # Get salary structure
            struct = payslip.contract_id.struct_id or payslip.struct_id
            if not struct:
                # Use default structure
                struct = self.env['hr.salary.structure'].search([('is_default', '=', True)], limit=1)
                if not struct:
                    raise UserError(_('No salary structure found. Please configure salary structure first.'))
                payslip.struct_id = struct

            # Generate payslip lines from rules
            lines = []
            for rule in struct.rule_ids.sorted(key=lambda r: r.sequence):
                line_vals = payslip._get_payslip_line_values(rule)
                if line_vals:
                    lines.append((0, 0, line_vals))

            payslip.line_ids = lines

        return True

    def _get_payslip_line_values(self, rule):
        """Calculate payslip line values for a given rule"""
        self.ensure_one()

        # Prepare context for rule evaluation
        localdict = self._get_localdict()

        # Evaluate condition
        if rule.condition_select == 'python':
            try:
                safe_eval(rule.condition_python, localdict, mode='exec', nocopy=True)
                if not localdict.get('result', False):
                    return None
            except Exception as e:
                raise UserError(_('Error in rule condition: %s\n%s') % (rule.name, str(e)))

        # Calculate amount
        if rule.amount_select == 'code':
            try:
                safe_eval(rule.amount_python_compute, localdict, mode='exec', nocopy=True)
                amount = localdict.get('result', 0.0)
            except Exception as e:
                raise UserError(_('Error in rule amount calculation: %s\n%s') % (rule.name, str(e)))
        elif rule.amount_select == 'percentage':
            basis = self._get_basis_amount(rule.amount_percentage_base, localdict)
            amount = basis * rule.amount_percentage / 100
        else:  # fix
            amount = rule.amount_fix

        if amount == 0:
            return None

        # Get quantity (usually 1.0 or working days)
        quantity = 1.0
        if rule.quantity:
            try:
                safe_eval(rule.quantity, localdict, mode='exec', nocopy=True)
                quantity = localdict.get('result', 1.0)
            except:
                quantity = 1.0

        return {
            'name': rule.name,
            'code': rule.code,
            'category_id': rule.category_id.id,
            'sequence': rule.sequence,
            'salary_rule_id': rule.id,
            'contract_id': self.contract_id.id,
            'employee_id': self.employee_id.id,
            'rate': amount,
            'quantity': quantity,
            'total': amount * quantity,
        }

    def _get_localdict(self):
        """Get local dictionary for rule evaluation"""
        self.ensure_one()

        contract = self.contract_id
        employee = self.employee_id

        # Calculate working days
        working_days = self._get_working_days()

        return {
            'contract': contract,
            'employee': employee,
            'payslip': self,
            'worked_days': working_days,
            'categories': {},
            'rules': {},
            'result': 0.0,
            # Salary components
            'BASIC': contract.wage,
            'HRA': contract.hra,
            'DA': contract.da,
            'TRANSPORT': contract.transport_allowance,
            'MEDICAL': contract.medical_allowance,
            'SPECIAL': contract.special_allowance,
            'OTHER': contract.other_allowance,
            'GROSS': contract.gross_salary,
        }

    def _get_working_days(self):
        """Calculate working days in the period"""
        # Simplified: assume full month = 30 days
        # In production, integrate with hr_attendance
        return 30.0

    def _get_basis_amount(self, basis_code, localdict):
        """Get basis amount for percentage calculations"""
        if basis_code in localdict:
            return localdict[basis_code]
        return 0.0

    def action_payslip_draft(self):
        """Set payslip to draft"""
        return self.write({'state': 'draft'})

    def action_payslip_verify(self):
        """Submit payslip for verification"""
        for payslip in self:
            if not payslip.line_ids:
                raise UserError(_('Please compute the payslip first.'))
        return self.write({'state': 'verify'})

    def action_payslip_done(self):
        """Approve and finalize payslip"""
        for payslip in self:
            if not payslip.number:
                payslip.number = self.env['ir.sequence'].next_by_code('hr.payslip') or _('New')
        return self.write({'state': 'done'})

    def action_payslip_cancel(self):
        """Cancel/reject payslip"""
        return self.write({'state': 'cancel'})

    def _get_portal_return_action(self):
        """Return action for portal view"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/my/payslips',
            'target': 'self',
        }


# Safe eval import
from odoo.tools.safe_eval import safe_eval
