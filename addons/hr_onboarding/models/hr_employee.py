# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    onboarding_ids = fields.One2many(
        'hr.onboarding', 'employee_id', string='Onboardings',
    )
    onboarding_state = fields.Selection([
        ('none', 'No Onboarding'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
    ], string='Onboarding Status', compute='_compute_onboarding_state',
    )

    def _compute_onboarding_state(self):
        for emp in self:
            active_onboarding = emp.onboarding_ids.filtered(lambda o: o.state == 'in_progress')
            if active_onboarding:
                emp.onboarding_state = 'in_progress'
            elif emp.onboarding_ids.filtered(lambda o: o.state == 'done'):
                emp.onboarding_state = 'done'
            else:
                emp.onboarding_state = 'none'
