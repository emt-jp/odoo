# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrSalaryRule(models.Model):
    _name = 'hr.salary.rule'
    _description = 'Salary Rule'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    code = fields.Char('Code', required=True, help="Unique code for this rule")
    sequence = fields.Integer('Sequence', default=10,
                               help="Use to arrange calculation sequence")
    category_id = fields.Many2one('hr.salary.rule.category', string='Category', required=True)
    active = fields.Boolean('Active', default=True)

    # Condition
    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('python', 'Python Expression'),
    ], string='Condition Based on', required=True, default='none')
    condition_python = fields.Text('Python Condition', default='''# Available variables:
# payslip, employee, contract, worked_days, categories, rules
# result = True if condition is met
result = True''')

    # Amount calculation
    amount_select = fields.Selection([
        ('code', 'Python Code'),
        ('percentage', 'Percentage (%)'),
        ('fix', 'Fixed Amount'),
    ], string='Amount Type', required=True, default='code')

    amount_fix = fields.Float('Fixed Amount', digits='Payroll')
    amount_percentage = fields.Float('Percentage (%)', digits='Payroll Rate')
    amount_percentage_base = fields.Char('Percentage based on',
                                          help='Enter the code of another rule, or BASIC, GROSS, etc.')
    amount_python_compute = fields.Text('Python Code', default='''# Available variables:
# payslip, employee, contract, worked_days, categories, rules
# BASIC, HRA, DA, TRANSPORT, MEDICAL, SPECIAL, OTHER, GROSS
# Assign the result to the variable 'result'
result = contract.wage''')

    # Quantity
    quantity = fields.Char('Quantity', default='1.0',
                            help="Python code to calculate quantity. Use 'worked_days' for prorated amounts.")

    # Structure relationship
    struct_id = fields.Many2one('hr.salary.structure', string='Salary Structure')

    note = fields.Text('Description')
