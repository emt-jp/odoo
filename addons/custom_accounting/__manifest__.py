# -*- coding: utf-8 -*-
{
    'name': 'Custom Accounting',
    'version': '19.0.1.2.0',
    'category': 'Accounting/Accounting',
    'summary': 'Extended Accounting with Japanese Invoice System, Hanko & Online Payments',
    'description': """
Custom Accounting Module
========================
This module extends the base accounting functionality with:

Financial Features:
- Financial Dashboard
- Budget Management
- Profit & Loss Reports
- Balance Sheet Reports
- Cash Flow Analysis
- Bank Reconciliation Tools
- Aging Reports
- Custom Invoice Templates

Japanese Invoice System (インボイス制度):
- Qualified Invoice Issuer Registration (適格請求書発行事業者)
- T-Number Management (T + 13 digits)
- Tax Breakdown by Rate (8% / 10%)
- Japanese Invoice Report Template

Hanko (会社印) & Receipts:
- Company Seal (Hanko) upload and display
- Japanese Receipt template with Hanko stamp
- Receipt generation for paid invoices

Online Payment Integration:
- Stripe Payment Gateway
- PayPay Integration (Japan)
- AirPay Integration (Japan)
- Webhook support for automatic payment reconciliation
- Payment link generation and email sending
    """,
    'author': 'Custom Development',
    'website': '',
    'depends': [
        'account',
        'account_payment',
        'mail',
        'web',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/account_security.xml',
        'wizard/financial_report_wizard_views.xml',
        'views/account_dashboard_views.xml',
        'views/budget_views.xml',
        'views/financial_report_views.xml',
        'views/menu_views.xml',
        'views/res_partner_t_number_views.xml',
        'views/res_company_t_number_views.xml',
        'views/account_move_t_number_views.xml',
        'views/payment_views.xml',
        'report/report_invoice_t_number.xml',
        'report/report_receipt_hanko.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
