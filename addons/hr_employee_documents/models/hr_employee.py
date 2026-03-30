# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    document_ids = fields.One2many(
        'hr.employee.document', 'employee_id', string='Documents',
    )
    document_count = fields.Integer(
        compute='_compute_document_count', string='Document Count',
    )

    def _compute_document_count(self):
        for employee in self:
            employee.document_count = len(employee.document_ids)
