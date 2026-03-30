# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class HrProbationReview(models.Model):
    _name = 'hr.probation.review'
    _description = 'Probation Review'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'review_date desc'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, ondelete='cascade', tracking=True,
    )
    reviewer_id = fields.Many2one(
        'hr.employee', string='Reviewer', tracking=True,
    )
    review_date = fields.Date(string='Review Date', required=True, default=fields.Date.today)
    probation_end_date = fields.Date(
        related='employee_id.probation_end_date', string='Probation Ends',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed - Pass'),
        ('extended', 'Extended'),
        ('terminated', 'Terminated'),
    ], string='Decision', default='draft', tracking=True)
    extension_months = fields.Integer(string='Extension (Months)')
    new_end_date = fields.Date(string='New End Date')
    performance_rating = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Below Average'),
        ('3', 'Average'),
        ('4', 'Good'),
        ('5', 'Excellent'),
    ], string='Performance Rating')
    strengths = fields.Text(string='Strengths')
    areas_for_improvement = fields.Text(string='Areas for Improvement')
    notes = fields.Text(string='Review Notes')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company,
    )

    @api.depends('employee_id', 'review_date')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Review - {rec.employee_id.name} ({rec.review_date})" if rec.employee_id else 'New Review'

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'
            rec.employee_id.probation_state = 'confirmed'

    def action_extend(self):
        for rec in self:
            if rec.extension_months and rec.employee_id.probation_end_date:
                from dateutil.relativedelta import relativedelta
                rec.new_end_date = rec.employee_id.probation_end_date + relativedelta(
                    months=rec.extension_months,
                )
                rec.employee_id.probation_end_date = rec.new_end_date
                rec.employee_id.probation_state = 'extended'
            rec.state = 'extended'

    def action_terminate(self):
        for rec in self:
            rec.state = 'terminated'
            rec.employee_id.probation_state = 'terminated'

    @api.model
    def _cron_probation_alerts(self):
        """Check for upcoming probation end dates and create alerts."""
        today = fields.Date.today()
        alert_date = today + timedelta(days=14)

        employees = self.env['hr.employee'].search([
            ('probation_state', 'in', ['in_probation', 'extended']),
            ('probation_end_date', '!=', False),
            ('probation_end_date', '<=', alert_date),
            ('probation_end_date', '>=', today),
        ])

        for emp in employees:
            days_left = (emp.probation_end_date - today).days
            emp.activity_schedule(
                'mail.mail_activity_data_warning',
                date_deadline=emp.probation_end_date,
                summary=f'Probation review due in {days_left} days',
                user_id=emp.parent_id.user_id.id or self.env.ref('base.user_admin').id,
            )
            emp.probation_state = 'review_pending'
