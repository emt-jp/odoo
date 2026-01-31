# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class AccountBudget(models.Model):
    _name = 'account.budget'
    _description = 'Budget Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char('Budget Name', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company, required=True)
    user_id = fields.Many2one('res.users', string='Responsible',
                               default=lambda self: self.env.user, tracking=True)
    date_from = fields.Date('Start Date', required=True, tracking=True)
    date_to = fields.Date('End Date', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('validated', 'Validated'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    budget_line_ids = fields.One2many('account.budget.line', 'budget_id', string='Budget Lines')

    total_planned = fields.Monetary('Total Planned', compute='_compute_totals', store=True)
    total_actual = fields.Monetary('Total Actual', compute='_compute_totals', store=True)
    total_variance = fields.Monetary('Total Variance', compute='_compute_totals', store=True)
    variance_percentage = fields.Float('Variance %', compute='_compute_totals', store=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    notes = fields.Text('Notes')

    @api.depends('budget_line_ids.planned_amount', 'budget_line_ids.actual_amount')
    def _compute_totals(self):
        for budget in self:
            budget.total_planned = sum(budget.budget_line_ids.mapped('planned_amount'))
            budget.total_actual = sum(budget.budget_line_ids.mapped('actual_amount'))
            budget.total_variance = budget.total_planned - budget.total_actual
            if budget.total_planned:
                budget.variance_percentage = (budget.total_variance / budget.total_planned) * 100
            else:
                budget.variance_percentage = 0

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for budget in self:
            if budget.date_from and budget.date_to:
                if budget.date_from > budget.date_to:
                    raise ValidationError(_('End date must be after start date.'))

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_validate(self):
        self.write({'state': 'validated'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_compute_actual(self):
        """Compute actual amounts from journal entries"""
        for budget in self:
            for line in budget.budget_line_ids:
                line._compute_actual_amount()


class AccountBudgetLine(models.Model):
    _name = 'account.budget.line'
    _description = 'Budget Line'

    budget_id = fields.Many2one('account.budget', string='Budget', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Account', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    planned_amount = fields.Monetary('Planned Amount', required=True)
    actual_amount = fields.Monetary('Actual Amount', compute='_compute_actual_amount', store=True)
    variance = fields.Monetary('Variance', compute='_compute_variance', store=True)
    variance_percentage = fields.Float('Variance %', compute='_compute_variance', store=True)

    currency_id = fields.Many2one('res.currency', related='budget_id.currency_id')
    company_id = fields.Many2one('res.company', related='budget_id.company_id')
    date_from = fields.Date(related='budget_id.date_from')
    date_to = fields.Date(related='budget_id.date_to')
    notes = fields.Char('Notes')

    @api.depends('budget_id.date_from', 'budget_id.date_to', 'account_id', 'analytic_account_id')
    def _compute_actual_amount(self):
        for line in self:
            if not line.account_id or not line.date_from or not line.date_to:
                line.actual_amount = 0
                continue

            domain = [
                ('account_id', '=', line.account_id.id),
                ('date', '>=', line.date_from),
                ('date', '<=', line.date_to),
                ('parent_state', '=', 'posted'),
            ]

            if line.analytic_account_id:
                domain.append(('analytic_distribution', 'ilike', str(line.analytic_account_id.id)))

            move_lines = self.env['account.move.line'].search(domain)
            line.actual_amount = sum(move_lines.mapped('balance'))

    @api.depends('planned_amount', 'actual_amount')
    def _compute_variance(self):
        for line in self:
            line.variance = line.planned_amount - line.actual_amount
            if line.planned_amount:
                line.variance_percentage = (line.variance / line.planned_amount) * 100
            else:
                line.variance_percentage = 0
