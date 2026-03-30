# -*- coding: utf-8 -*-
from odoo import fields, models


class HrOnboardingTemplate(models.Model):
    _name = 'hr.onboarding.template'
    _description = 'Onboarding Template'
    _order = 'sequence, name'

    name = fields.Char(string='Template Name', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    task_ids = fields.One2many(
        'hr.onboarding.template.task', 'template_id', string='Tasks',
    )
    note = fields.Text(string='Description')


class HrOnboardingTemplateTask(models.Model):
    _name = 'hr.onboarding.template.task'
    _description = 'Onboarding Template Task'
    _order = 'sequence, name'

    name = fields.Char(string='Task Name', required=True)
    template_id = fields.Many2one(
        'hr.onboarding.template', string='Template', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    department_id = fields.Many2one('hr.department', string='Responsible Department')
    responsible_user_id = fields.Many2one('res.users', string='Responsible Person')
    days_after_start = fields.Integer(
        string='Days After Start',
        default=0,
        help='Number of days after employee start date to complete this task',
    )
    description = fields.Text(string='Instructions')
    category = fields.Selection([
        ('it', 'IT Setup'),
        ('hr', 'HR / Admin'),
        ('finance', 'Finance'),
        ('training', 'Training'),
        ('other', 'Other'),
    ], string='Category', default='hr')
