# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import io
import base64

try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False


class FinancialReportWizard(models.TransientModel):
    _name = 'financial.report.wizard'
    _description = 'Financial Report Wizard'

    report_type = fields.Selection([
        ('profit_loss', 'Profit & Loss'),
        ('balance_sheet', 'Balance Sheet'),
        ('trial_balance', 'Trial Balance'),
        ('general_ledger', 'General Ledger'),
        ('cash_flow', 'Cash Flow Statement'),
    ], string='Report Type', required=True, default='profit_loss')

    date_from = fields.Date('From Date', required=True)
    date_to = fields.Date('To Date', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company, required=True)

    # Filter options
    account_ids = fields.Many2many('account.account', string='Accounts')
    partner_ids = fields.Many2many('res.partner', string='Partners')
    analytic_account_ids = fields.Many2many('account.analytic.account', string='Analytic Accounts')

    # Comparison options
    enable_comparison = fields.Boolean('Enable Comparison')
    comparison_date_from = fields.Date('Comparison From')
    comparison_date_to = fields.Date('Comparison To')

    # Display options
    show_zero_balance = fields.Boolean('Show Zero Balance', default=False)
    hierarchy = fields.Boolean('Show Account Hierarchy', default=True)

    # Output format
    output_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
        ('html', 'HTML Preview'),
    ], string='Output Format', default='html')

    @api.onchange('report_type')
    def _onchange_report_type(self):
        """Set default dates based on report type"""
        today = fields.Date.today()
        if self.report_type == 'profit_loss':
            # Default to current month
            self.date_from = today.replace(day=1)
            self.date_to = today
        elif self.report_type == 'balance_sheet':
            # Default to year start to today
            self.date_from = today.replace(month=1, day=1)
            self.date_to = today

    def action_generate_report(self):
        """Generate the selected report"""
        self.ensure_one()

        if self.output_format == 'html':
            return self._generate_html_report()
        elif self.output_format == 'xlsx':
            return self._generate_xlsx_report()
        else:
            return self._generate_pdf_report()

    def _get_profit_loss_data(self):
        """Get Profit & Loss report data"""
        company_id = self.company_id.id

        # Revenue accounts
        revenue_accounts = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_ids', 'in', [company_id]),
        ])

        # Expense accounts
        expense_accounts = self.env['account.account'].search([
            ('account_type', '=', 'expense'),
            ('company_ids', 'in', [company_id]),
        ])

        data = {
            'revenue': [],
            'expenses': [],
            'total_revenue': 0,
            'total_expenses': 0,
            'net_profit': 0,
        }

        # Calculate revenue
        for account in revenue_accounts:
            balance = self._get_account_balance(account)
            if balance != 0 or self.show_zero_balance:
                data['revenue'].append({
                    'code': account.code,
                    'name': account.name,
                    'balance': -balance,  # Revenue is credit, so negate
                })
                data['total_revenue'] += -balance

        # Calculate expenses
        for account in expense_accounts:
            balance = self._get_account_balance(account)
            if balance != 0 or self.show_zero_balance:
                data['expenses'].append({
                    'code': account.code,
                    'name': account.name,
                    'balance': balance,
                })
                data['total_expenses'] += balance

        data['net_profit'] = data['total_revenue'] - data['total_expenses']
        return data

    def _get_balance_sheet_data(self):
        """Get Balance Sheet report data"""
        company_id = self.company_id.id

        data = {
            'assets': {'current': [], 'non_current': [], 'total': 0},
            'liabilities': {'current': [], 'non_current': [], 'total': 0},
            'equity': {'items': [], 'total': 0},
        }

        # Asset accounts
        asset_types = ['asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed']
        for asset_type in asset_types:
            accounts = self.env['account.account'].search([
                ('account_type', '=', asset_type),
                ('company_ids', 'in', [company_id]),
            ])
            for account in accounts:
                balance = self._get_account_balance(account)
                if balance != 0 or self.show_zero_balance:
                    category = 'current' if 'current' in asset_type or asset_type in ['asset_cash', 'asset_receivable'] else 'non_current'
                    data['assets'][category].append({
                        'code': account.code,
                        'name': account.name,
                        'balance': balance,
                    })
                    data['assets']['total'] += balance

        # Liability accounts
        liability_types = ['liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current']
        for liability_type in liability_types:
            accounts = self.env['account.account'].search([
                ('account_type', '=', liability_type),
                ('company_ids', 'in', [company_id]),
            ])
            for account in accounts:
                balance = self._get_account_balance(account)
                if balance != 0 or self.show_zero_balance:
                    category = 'current' if 'current' in liability_type or liability_type == 'liability_payable' else 'non_current'
                    data['liabilities'][category].append({
                        'code': account.code,
                        'name': account.name,
                        'balance': -balance,  # Liabilities are credit
                    })
                    data['liabilities']['total'] += -balance

        # Equity accounts
        equity_types = ['equity', 'equity_unaffected']
        for equity_type in equity_types:
            accounts = self.env['account.account'].search([
                ('account_type', '=', equity_type),
                ('company_ids', 'in', [company_id]),
            ])
            for account in accounts:
                balance = self._get_account_balance(account)
                if balance != 0 or self.show_zero_balance:
                    data['equity']['items'].append({
                        'code': account.code,
                        'name': account.name,
                        'balance': -balance,  # Equity is credit
                    })
                    data['equity']['total'] += -balance

        return data

    def _get_trial_balance_data(self):
        """Get Trial Balance report data"""
        company_id = self.company_id.id

        accounts = self.env['account.account'].search([
            ('company_ids', 'in', [company_id]),
        ], order='code')

        data = {
            'accounts': [],
            'total_debit': 0,
            'total_credit': 0,
        }

        for account in accounts:
            balance = self._get_account_balance(account)
            if balance != 0 or self.show_zero_balance:
                debit = balance if balance > 0 else 0
                credit = -balance if balance < 0 else 0
                data['accounts'].append({
                    'code': account.code,
                    'name': account.name,
                    'debit': debit,
                    'credit': credit,
                })
                data['total_debit'] += debit
                data['total_credit'] += credit

        return data

    def _get_account_balance(self, account):
        """Get account balance for the selected period"""
        domain = [
            ('account_id', '=', account.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('parent_state', '=', 'posted'),
        ]

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        move_lines = self.env['account.move.line'].search(domain)
        return sum(move_lines.mapped('balance'))

    def _generate_html_report(self):
        """Generate HTML preview"""
        if self.report_type == 'profit_loss':
            data = self._get_profit_loss_data()
            template = 'custom_accounting.report_profit_loss'
        elif self.report_type == 'balance_sheet':
            data = self._get_balance_sheet_data()
            template = 'custom_accounting.report_balance_sheet'
        elif self.report_type == 'trial_balance':
            data = self._get_trial_balance_data()
            template = 'custom_accounting.report_trial_balance'
        else:
            raise UserError(_('Report type not yet implemented'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Financial Report'),
            'res_model': 'financial.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'report_data': data},
        }

    def _generate_xlsx_report(self):
        """Generate Excel report"""
        if not XLSXWRITER_AVAILABLE:
            raise UserError(_('xlsxwriter library is required for Excel export'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Report')

        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
        })
        number_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        text_format = workbook.add_format({'border': 1})

        if self.report_type == 'profit_loss':
            data = self._get_profit_loss_data()
            self._write_profit_loss_xlsx(worksheet, data, header_format, number_format, text_format)
        elif self.report_type == 'balance_sheet':
            data = self._get_balance_sheet_data()
            self._write_balance_sheet_xlsx(worksheet, data, header_format, number_format, text_format)
        elif self.report_type == 'trial_balance':
            data = self._get_trial_balance_data()
            self._write_trial_balance_xlsx(worksheet, data, header_format, number_format, text_format)

        workbook.close()
        output.seek(0)

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'{self.report_type}_{self.date_from}_{self.date_to}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _write_profit_loss_xlsx(self, worksheet, data, header_format, number_format, text_format):
        """Write P&L data to Excel"""
        row = 0
        worksheet.write(row, 0, 'Code', header_format)
        worksheet.write(row, 1, 'Account', header_format)
        worksheet.write(row, 2, 'Amount', header_format)

        row += 1
        worksheet.write(row, 0, 'REVENUE', header_format)
        worksheet.merge_range(row, 1, row, 2, '', header_format)

        for item in data['revenue']:
            row += 1
            worksheet.write(row, 0, item['code'], text_format)
            worksheet.write(row, 1, item['name'], text_format)
            worksheet.write(row, 2, item['balance'], number_format)

        row += 1
        worksheet.write(row, 1, 'Total Revenue', header_format)
        worksheet.write(row, 2, data['total_revenue'], number_format)

        row += 2
        worksheet.write(row, 0, 'EXPENSES', header_format)

        for item in data['expenses']:
            row += 1
            worksheet.write(row, 0, item['code'], text_format)
            worksheet.write(row, 1, item['name'], text_format)
            worksheet.write(row, 2, item['balance'], number_format)

        row += 1
        worksheet.write(row, 1, 'Total Expenses', header_format)
        worksheet.write(row, 2, data['total_expenses'], number_format)

        row += 2
        worksheet.write(row, 1, 'NET PROFIT', header_format)
        worksheet.write(row, 2, data['net_profit'], number_format)

        worksheet.set_column(0, 0, 15)
        worksheet.set_column(1, 1, 40)
        worksheet.set_column(2, 2, 15)

    def _write_balance_sheet_xlsx(self, worksheet, data, header_format, number_format, text_format):
        """Write Balance Sheet data to Excel"""
        row = 0
        worksheet.write(row, 0, 'Code', header_format)
        worksheet.write(row, 1, 'Account', header_format)
        worksheet.write(row, 2, 'Amount', header_format)

        # Assets
        row += 1
        worksheet.write(row, 0, 'ASSETS', header_format)

        for item in data['assets']['current'] + data['assets']['non_current']:
            row += 1
            worksheet.write(row, 0, item['code'], text_format)
            worksheet.write(row, 1, item['name'], text_format)
            worksheet.write(row, 2, item['balance'], number_format)

        row += 1
        worksheet.write(row, 1, 'Total Assets', header_format)
        worksheet.write(row, 2, data['assets']['total'], number_format)

        # Liabilities
        row += 2
        worksheet.write(row, 0, 'LIABILITIES', header_format)

        for item in data['liabilities']['current'] + data['liabilities']['non_current']:
            row += 1
            worksheet.write(row, 0, item['code'], text_format)
            worksheet.write(row, 1, item['name'], text_format)
            worksheet.write(row, 2, item['balance'], number_format)

        row += 1
        worksheet.write(row, 1, 'Total Liabilities', header_format)
        worksheet.write(row, 2, data['liabilities']['total'], number_format)

        # Equity
        row += 2
        worksheet.write(row, 0, 'EQUITY', header_format)

        for item in data['equity']['items']:
            row += 1
            worksheet.write(row, 0, item['code'], text_format)
            worksheet.write(row, 1, item['name'], text_format)
            worksheet.write(row, 2, item['balance'], number_format)

        row += 1
        worksheet.write(row, 1, 'Total Equity', header_format)
        worksheet.write(row, 2, data['equity']['total'], number_format)

        worksheet.set_column(0, 0, 15)
        worksheet.set_column(1, 1, 40)
        worksheet.set_column(2, 2, 15)

    def _write_trial_balance_xlsx(self, worksheet, data, header_format, number_format, text_format):
        """Write Trial Balance data to Excel"""
        row = 0
        worksheet.write(row, 0, 'Code', header_format)
        worksheet.write(row, 1, 'Account', header_format)
        worksheet.write(row, 2, 'Debit', header_format)
        worksheet.write(row, 3, 'Credit', header_format)

        for item in data['accounts']:
            row += 1
            worksheet.write(row, 0, item['code'], text_format)
            worksheet.write(row, 1, item['name'], text_format)
            worksheet.write(row, 2, item['debit'], number_format)
            worksheet.write(row, 3, item['credit'], number_format)

        row += 1
        worksheet.write(row, 1, 'TOTAL', header_format)
        worksheet.write(row, 2, data['total_debit'], number_format)
        worksheet.write(row, 3, data['total_credit'], number_format)

        worksheet.set_column(0, 0, 15)
        worksheet.set_column(1, 1, 40)
        worksheet.set_column(2, 3, 15)

    def _generate_pdf_report(self):
        """Generate PDF report - placeholder"""
        raise UserError(_('PDF generation requires additional setup. Please use Excel or HTML format.'))
