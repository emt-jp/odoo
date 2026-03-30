# -*- coding: utf-8 -*-
{
    'name': 'HR Onboarding Checklist',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Automated onboarding checklists for new employees',
    'description': """
        HR Onboarding Checklist
        =======================

        Automated onboarding workflow:

        * Define checklist templates with tasks
        * Auto-create checklist when employee is hired
        * Assign tasks to different departments (IT, HR, Finance)
        * Track completion progress
        * Deadline management
    """,
    'author': 'EMT-JP',
    'depends': [
        'hr',
        'hr_recruitment',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/onboarding_template_data.xml',
        'views/hr_onboarding_template_views.xml',
        'views/hr_onboarding_views.xml',
        'views/hr_employee_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
