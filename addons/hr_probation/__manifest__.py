# -*- coding: utf-8 -*-
{
    'name': 'HR Probation Tracking',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Track employee probation periods with automated alerts',
    'description': """
        HR Probation Tracking
        =====================

        Track and manage employee probation:

        * Probation start/end dates on employee profile
        * Probation duration configuration
        * Automated alerts before probation expires
        * Probation review workflow
        * Dashboard for upcoming probation reviews
    """,
    'author': 'EMT-JP',
    'depends': [
        'hr',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_data.xml',
        'views/hr_employee_views.xml',
        'views/hr_probation_review_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
