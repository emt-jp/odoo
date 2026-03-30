# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class HrOnboarding(models.Model):
    _name = 'hr.onboarding'
    _description = 'Employee Onboarding'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, ondelete='cascade', tracking=True,
    )
    template_id = fields.Many2one(
        'hr.onboarding.template', string='Template', tracking=True,
    )
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.today)
    state = fields.Selection([
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='in_progress', tracking=True)
    task_ids = fields.One2many(
        'hr.onboarding.task', 'onboarding_id', string='Tasks',
    )
    progress = fields.Float(compute='_compute_progress', string='Progress', store=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company,
    )

    @api.depends('employee_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Onboarding - {rec.employee_id.name}" if rec.employee_id else 'New Onboarding'

    @api.depends('task_ids.state')
    def _compute_progress(self):
        for rec in self:
            total = len(rec.task_ids)
            done = len(rec.task_ids.filtered(lambda t: t.state == 'done'))
            rec.progress = (done / total * 100) if total else 0

    def action_generate_tasks(self):
        """Generate onboarding tasks from template."""
        for rec in self:
            if not rec.template_id:
                continue
            for tmpl_task in rec.template_id.task_ids:
                deadline = rec.start_date + timedelta(days=tmpl_task.days_after_start) if rec.start_date else False
                self.env['hr.onboarding.task'].create({
                    'onboarding_id': rec.id,
                    'name': tmpl_task.name,
                    'sequence': tmpl_task.sequence,
                    'category': tmpl_task.category,
                    'responsible_user_id': tmpl_task.responsible_user_id.id,
                    'department_id': tmpl_task.department_id.id,
                    'deadline': deadline,
                    'description': tmpl_task.description,
                })

    def action_mark_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class HrOnboardingTask(models.Model):
    _name = 'hr.onboarding.task'
    _description = 'Onboarding Task'
    _order = 'sequence, deadline'

    name = fields.Char(string='Task', required=True)
    onboarding_id = fields.Many2one(
        'hr.onboarding', string='Onboarding', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    state = fields.Selection([
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('skipped', 'Skipped'),
    ], string='Status', default='todo')
    category = fields.Selection([
        ('it', 'IT Setup'),
        ('hr', 'HR / Admin'),
        ('finance', 'Finance'),
        ('training', 'Training'),
        ('other', 'Other'),
    ], string='Category', default='hr')
    responsible_user_id = fields.Many2one('res.users', string='Assigned To')
    department_id = fields.Many2one('hr.department', string='Department')
    deadline = fields.Date(string='Deadline')
    completion_date = fields.Date(string='Completed On')
    description = fields.Text(string='Instructions')
    note = fields.Text(string='Notes')

    def action_done(self):
        self.write({'state': 'done', 'completion_date': fields.Date.today()})
        for task in self:
            if all(t.state in ('done', 'skipped') for t in task.onboarding_id.task_ids):
                task.onboarding_id.action_mark_done()

    def action_skip(self):
        self.write({'state': 'skipped'})
