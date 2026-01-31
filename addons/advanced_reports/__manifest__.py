# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Advanced Reports',
    'version': '1.0.0',
    'category': 'Reporting',
    'summary': 'Advanced reporting and analytics features',
    'description': """
        Advanced Reports Module
        ======================
        
        This module provides advanced reporting and analytics features
        that are typically found in enterprise editions.
        
        Features:
        - Custom Report Builder
        - Advanced Financial Reports
        - Sales Performance Reports
        - Inventory Reports
        - CRM Reports
        - Interactive Dashboards
        - Scheduled Reports
        - Export to Multiple Formats
        - Report Templates
        - Data Visualization
    """,
    'depends': [
        'base',
        'web',
        'sale',
        'account',
        'crm',
        'stock',
        'product',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/report_views.xml',
    ],
    'demo': [],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
}




