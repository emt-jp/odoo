# -*- coding: utf-8 -*-
{
    'name': 'HR Employee Documents',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee document management with types, expiry tracking, and portal access',
    'description': """
        HR Employee Documents
        =====================

        Manage employee documents with:

        * Document types (passport, visa, contract, certificates, etc.)
        * Expiry date tracking with automated alerts
        * Document upload from employee form
        * Employee portal access for document viewing/uploading
        * Dashboard for expiring documents
    """,
    'author': 'EMT-JP',
    'depends': [
        'hr',
        'portal',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/document_type_data.xml',
        'data/cron_data.xml',
        'views/hr_document_type_views.xml',
        'views/hr_employee_document_views.xml',
        'views/hr_employee_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
