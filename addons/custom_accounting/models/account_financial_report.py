# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class AccountFinancialReport(models.Model):
    _name = 'account.financial.report.custom'
    _description = 'Custom Financial Report'
    _order = 'sequence, id'

    name = fields.Char('Report Name', required=True)
    sequence = fields.Integer('Sequence', default=10)
    parent_id = fields.Many2one('account.financial.report.custom', string='Parent')
    child_ids = fields.One2many('account.financial.report.custom', 'parent_id', string='Children')
    report_type = fields.Selection([
        ('sum', 'Sum of Children'),
        ('accounts', 'Account Balance'),
        ('account_type', 'Account Type Balance'),
        ('report', 'Report Value'),
    ], string='Type', default='sum', required=True)

    account_ids = fields.Many2many('account.account', string='Accounts')
    # In Odoo 19, account types are stored as selection on account.account
    # Use a char field to store comma-separated account types
    account_types = fields.Char(
        'Account Types',
        help='Comma-separated account types (e.g., income,expense,asset_receivable)'
    )
    sign = fields.Selection([
        ('positive', 'Positive'),
        ('negative', 'Negative'),
    ], string='Sign', default='positive', required=True)

    display_detail = fields.Selection([
        ('no_detail', 'No Detail'),
        ('detail_flat', 'Display Children Flat'),
        ('detail_with_hierarchy', 'Display Children with Hierarchy'),
    ], string='Display Details', default='no_detail')

    level = fields.Integer('Level', compute='_compute_level', store=True)
    style_overwrite = fields.Selection([
        ('auto', 'Automatic'),
        ('title1', 'Main Title 1'),
        ('title2', 'Title 2'),
        ('title3', 'Title 3'),
        ('normal', 'Normal'),
        ('italic', 'Italic'),
        ('bold', 'Bold'),
    ], string='Style', default='auto')

    @api.depends('parent_id', 'parent_id.level')
    def _compute_level(self):
        for report in self:
            if report.parent_id:
                report.level = report.parent_id.level + 1
            else:
                report.level = 0

    def _get_balance(self, date_from, date_to, company_id, analytic_account_id=False):
        """Calculate the balance for this report line"""
        self.ensure_one()
        balance = 0.0

        if self.report_type == 'accounts':
            balance = self._compute_account_balance(
                date_from, date_to, company_id, analytic_account_id
            )
        elif self.report_type == 'account_type':
            balance = self._compute_account_type_balance(
                date_from, date_to, company_id, analytic_account_id
            )
        elif self.report_type == 'sum':
            for child in self.child_ids:
                balance += child._get_balance(
                    date_from, date_to, company_id, analytic_account_id
                )
        elif self.report_type == 'report':
            # Reference another report - can be extended
            pass

        sign_multiplier = 1 if self.sign == 'positive' else -1
        return balance * sign_multiplier

    def _compute_account_balance(self, date_from, date_to, company_id, analytic_account_id=False):
        """Compute balance from specific accounts"""
        if not self.account_ids:
            return 0.0

        domain = [
            ('account_id', 'in', self.account_ids.ids),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', company_id),
            ('parent_state', '=', 'posted'),
        ]

        if analytic_account_id:
            domain.append(('analytic_distribution', 'ilike', str(analytic_account_id)))

        move_lines = self.env['account.move.line'].search(domain)
        return sum(move_lines.mapped('balance'))

    def _compute_account_type_balance(self, date_from, date_to, company_id, analytic_account_id=False):
        """Compute balance from account types"""
        if not self.account_types:
            return 0.0

        # Parse comma-separated account types
        account_type_list = [t.strip() for t in self.account_types.split(',') if t.strip()]
        if not account_type_list:
            return 0.0

        accounts = self.env['account.account'].search([
            ('account_type', 'in', account_type_list),
            ('company_ids', 'in', [company_id]),
        ])

        if not accounts:
            return 0.0

        domain = [
            ('account_id', 'in', accounts.ids),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', company_id),
            ('parent_state', '=', 'posted'),
        ]

        if analytic_account_id:
            domain.append(('analytic_distribution', 'ilike', str(analytic_account_id)))

        move_lines = self.env['account.move.line'].search(domain)
        return sum(move_lines.mapped('balance'))


class AccountFinancialDashboard(models.Model):
    _name = 'account.financial.dashboard'
    _description = 'Financial Dashboard'

    name = fields.Char('Dashboard Name', default='Financial Overview')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    # Period selection
    date_from = fields.Date('From Date')
    date_to = fields.Date('To Date')

    # Summary fields (computed)
    total_revenue = fields.Monetary('Total Revenue', compute='_compute_dashboard_values')
    total_expenses = fields.Monetary('Total Expenses', compute='_compute_dashboard_values')
    net_profit = fields.Monetary('Net Profit', compute='_compute_dashboard_values')
    profit_margin = fields.Float('Profit Margin %', compute='_compute_dashboard_values')

    total_receivables = fields.Monetary('Total Receivables', compute='_compute_dashboard_values')
    total_payables = fields.Monetary('Total Payables', compute='_compute_dashboard_values')
    cash_balance = fields.Monetary('Cash Balance', compute='_compute_dashboard_values')

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_dashboard_values(self):
        for dashboard in self:
            if not dashboard.date_from or not dashboard.date_to:
                dashboard.total_revenue = 0
                dashboard.total_expenses = 0
                dashboard.net_profit = 0
                dashboard.profit_margin = 0
                dashboard.total_receivables = 0
                dashboard.total_payables = 0
                dashboard.cash_balance = 0
                continue

            company_id = dashboard.company_id.id

            # Revenue (Income accounts - typically credit balance, so we negate)
            revenue_accounts = self.env['account.account'].search([
                ('account_type', '=', 'income'),
                ('company_ids', 'in', [company_id]),
            ])
            revenue_lines = self.env['account.move.line'].search([
                ('account_id', 'in', revenue_accounts.ids),
                ('date', '>=', dashboard.date_from),
                ('date', '<=', dashboard.date_to),
                ('parent_state', '=', 'posted'),
            ])
            dashboard.total_revenue = -sum(revenue_lines.mapped('balance'))

            # Expenses
            expense_accounts = self.env['account.account'].search([
                ('account_type', '=', 'expense'),
                ('company_ids', 'in', [company_id]),
            ])
            expense_lines = self.env['account.move.line'].search([
                ('account_id', 'in', expense_accounts.ids),
                ('date', '>=', dashboard.date_from),
                ('date', '<=', dashboard.date_to),
                ('parent_state', '=', 'posted'),
            ])
            dashboard.total_expenses = sum(expense_lines.mapped('balance'))

            # Net profit
            dashboard.net_profit = dashboard.total_revenue - dashboard.total_expenses
            if dashboard.total_revenue:
                dashboard.profit_margin = (dashboard.net_profit / dashboard.total_revenue) * 100
            else:
                dashboard.profit_margin = 0

            # Receivables
            receivable_accounts = self.env['account.account'].search([
                ('account_type', '=', 'asset_receivable'),
                ('company_ids', 'in', [company_id]),
            ])
            receivable_lines = self.env['account.move.line'].search([
                ('account_id', 'in', receivable_accounts.ids),
                ('parent_state', '=', 'posted'),
            ])
            dashboard.total_receivables = sum(receivable_lines.mapped('balance'))

            # Payables
            payable_accounts = self.env['account.account'].search([
                ('account_type', '=', 'liability_payable'),
                ('company_ids', 'in', [company_id]),
            ])
            payable_lines = self.env['account.move.line'].search([
                ('account_id', 'in', payable_accounts.ids),
                ('parent_state', '=', 'posted'),
            ])
            dashboard.total_payables = -sum(payable_lines.mapped('balance'))

            # Cash balance
            cash_accounts = self.env['account.account'].search([
                ('account_type', 'in', ['asset_cash', 'asset_current']),
                ('company_ids', 'in', [company_id]),
            ])
            cash_lines = self.env['account.move.line'].search([
                ('account_id', 'in', cash_accounts.ids),
                ('parent_state', '=', 'posted'),
            ])
            dashboard.cash_balance = sum(cash_lines.mapped('balance'))

    def action_refresh(self):
        """Refresh dashboard data"""
        self._compute_dashboard_values()
        return True

    def action_set_this_month(self):
        """Set period to current month"""
        today = fields.Date.today()
        self.date_from = today.replace(day=1)
        self.date_to = (today.replace(day=1) + relativedelta(months=1)) - timedelta(days=1)
        return True

    def action_set_this_quarter(self):
        """Set period to current quarter"""
        today = fields.Date.today()
        quarter = (today.month - 1) // 3
        self.date_from = today.replace(month=quarter * 3 + 1, day=1)
        self.date_to = (self.date_from + relativedelta(months=3)) - timedelta(days=1)
        return True

    def action_set_this_year(self):
        """Set period to current year"""
        today = fields.Date.today()
        self.date_from = today.replace(month=1, day=1)
        self.date_to = today.replace(month=12, day=31)
        return True


class AccountAgingReport(models.Model):
    _name = 'account.aging.report'
    _description = 'Aging Report'

    name = fields.Char('Report Name', required=True)
    report_type = fields.Selection([
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
    ], string='Report Type', required=True, default='receivable')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    as_of_date = fields.Date('As of Date', default=fields.Date.today)

    line_ids = fields.One2many('account.aging.report.line', 'report_id', string='Report Lines')

    # Summary totals
    total_current = fields.Monetary('Current', compute='_compute_totals')
    total_1_30 = fields.Monetary('1-30 Days', compute='_compute_totals')
    total_31_60 = fields.Monetary('31-60 Days', compute='_compute_totals')
    total_61_90 = fields.Monetary('61-90 Days', compute='_compute_totals')
    total_90_plus = fields.Monetary('90+ Days', compute='_compute_totals')
    total_amount = fields.Monetary('Total', compute='_compute_totals')

    @api.depends('line_ids')
    def _compute_totals(self):
        for report in self:
            report.total_current = sum(report.line_ids.mapped('current'))
            report.total_1_30 = sum(report.line_ids.mapped('days_1_30'))
            report.total_31_60 = sum(report.line_ids.mapped('days_31_60'))
            report.total_61_90 = sum(report.line_ids.mapped('days_61_90'))
            report.total_90_plus = sum(report.line_ids.mapped('days_90_plus'))
            report.total_amount = sum(report.line_ids.mapped('total'))

    def action_compute(self):
        """Compute aging report"""
        self.ensure_one()
        self.line_ids.unlink()

        account_type = 'asset_receivable' if self.report_type == 'receivable' else 'liability_payable'

        # Get all partners with open balances
        domain = [
            ('account_id.account_type', '=', account_type),
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
            ('reconciled', '=', False),
        ]

        move_lines = self.env['account.move.line'].search(domain)
        partner_data = {}

        for line in move_lines:
            partner_id = line.partner_id.id or 0
            if partner_id not in partner_data:
                partner_data[partner_id] = {
                    'partner_id': line.partner_id.id,
                    'current': 0,
                    'days_1_30': 0,
                    'days_31_60': 0,
                    'days_61_90': 0,
                    'days_90_plus': 0,
                }

            # Calculate days overdue
            if line.date_maturity:
                days = (self.as_of_date - line.date_maturity).days
            else:
                days = (self.as_of_date - line.date).days

            amount = abs(line.amount_residual)

            if days <= 0:
                partner_data[partner_id]['current'] += amount
            elif days <= 30:
                partner_data[partner_id]['days_1_30'] += amount
            elif days <= 60:
                partner_data[partner_id]['days_31_60'] += amount
            elif days <= 90:
                partner_data[partner_id]['days_61_90'] += amount
            else:
                partner_data[partner_id]['days_90_plus'] += amount

        # Create report lines
        for partner_id, data in partner_data.items():
            self.env['account.aging.report.line'].create({
                'report_id': self.id,
                'partner_id': data['partner_id'],
                'current': data['current'],
                'days_1_30': data['days_1_30'],
                'days_31_60': data['days_31_60'],
                'days_61_90': data['days_61_90'],
                'days_90_plus': data['days_90_plus'],
            })

        return True


class AccountAgingReportLine(models.Model):
    _name = 'account.aging.report.line'
    _description = 'Aging Report Line'

    report_id = fields.Many2one('account.aging.report', string='Report', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner')
    currency_id = fields.Many2one('res.currency', related='report_id.currency_id')

    current = fields.Monetary('Current')
    days_1_30 = fields.Monetary('1-30 Days')
    days_31_60 = fields.Monetary('31-60 Days')
    days_61_90 = fields.Monetary('61-90 Days')
    days_90_plus = fields.Monetary('90+ Days')
    total = fields.Monetary('Total', compute='_compute_total')

    @api.depends('current', 'days_1_30', 'days_31_60', 'days_61_90', 'days_90_plus')
    def _compute_total(self):
        for line in self:
            line.total = (line.current + line.days_1_30 + line.days_31_60 +
                         line.days_61_90 + line.days_90_plus)
