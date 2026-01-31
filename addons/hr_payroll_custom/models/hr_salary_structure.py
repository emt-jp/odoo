# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrSalaryStructure(models.Model):
    _name = 'hr.salary.structure'
    _description = 'Salary Structure'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code')
    active = fields.Boolean('Active', default=True)
    is_default = fields.Boolean('Default Structure', help="If checked, this structure will be used by default for new payslips")

    rule_ids = fields.One2many('hr.salary.rule', 'struct_id', string='Salary Rules', copy=True)

    note = fields.Text('Description')

    @api.model
    def create(self, vals_list):
        """If is_default is True, unset other default structures"""
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        for vals in vals_list:
            if vals.get('is_default'):
                self.search([('is_default', '=', True)]).write({'is_default': False})
                break

        return super().create(vals_list)

    def write(self, vals):
        """If is_default is set, unset other default structures"""
        if vals.get('is_default'):
            self.search([('id', 'not in', self.ids), ('is_default', '=', True)]).write({'is_default': False})
        return super().write(vals)
