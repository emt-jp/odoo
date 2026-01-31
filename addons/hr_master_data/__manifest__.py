# -*- coding: utf-8 -*-
{
    'name': 'HR Master Data',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Master data setup for HR module with comprehensive demo data',
    'description': """
        HR Master Data Module
        ======================

        This module provides comprehensive master data and demo data for HR operations:

        * Departments and hierarchies
        * Job positions across all departments
        * Leave types with allocations
        * Sample employees with various roles
        * Perfect for testing and initial setup of car rental and fleet management operations.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'hr',
        'hr_holidays',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_department_data.xml',
        'data/hr_job_data.xml',
        'data/hr_employee_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
