# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    probation_start_date = fields.Date(string='Probation Start')
    probation_end_date = fields.Date(string='Probation End')
    probation_duration_months = fields.Integer(
        string='Probation Duration (Months)', default=3,
    )
    probation_state = fields.Selection([
        ('none', 'No Probation'),
        ('in_probation', 'In Probation'),
        ('review_pending', 'Review Pending'),
        ('confirmed', 'Confirmed'),
        ('extended', 'Extended'),
        ('terminated', 'Terminated'),
    ], string='Probation Status', default='none', tracking=True)
    probation_review_ids = fields.One2many(
        'hr.probation.review', 'employee_id', string='Probation Reviews',
    )

    @api.onchange('probation_start_date', 'probation_duration_months')
    def _onchange_probation_dates(self):
        if self.probation_start_date and self.probation_duration_months:
            from dateutil.relativedelta import relativedelta
            self.probation_end_date = self.probation_start_date + relativedelta(
                months=self.probation_duration_months,
            )
