# -*- coding: utf-8 -*-
{
    'name': 'HR Payroll Custom',
    'version': '1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Complete payroll system with salary management and employee payslip portal',
    'description': """
        HR Payroll Custom Module
        =========================

        Complete payroll management system with:

        * Admin can set employee salaries (base salary, allowances, deductions)
        * Configure salary components (HRA, DA, Transport, Medical, etc.)
        * Configure deductions (Tax, PF, ESI, Professional Tax, LOP, etc.)
        * Process monthly payroll in batches
        * Generate payslips with detailed breakdown
        * Employees can view and download their payslips from portal
        * PDF payslip reports
        * Salary history tracking
        * Multi-currency support
    """,
    'author': 'Your Company',
    'depends': [
        'hr',
        'hr_holidays',
        'portal',
        'hr_master_data',
    ],
    'data': [
        'security/payroll_security.xml',
        'security/ir.model.access.csv',
        'data/salary_structure_data.xml',
        'data/salary_rule_data.xml',
        'views/menu_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_employee_views.xml',
        'views/portal_payslip_views.xml',
        'wizard/payslip_batch_wizard_views.xml',
        'report/payslip_report.xml',
        'report/payslip_report_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
