# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Advanced Analytics',
    'version': '1.0.0',
    'category': 'Analytics',
    'summary': 'Advanced analytics and reporting features',
    'description': """
        Advanced Analytics Module
        ========================
        
        This module provides advanced analytics and reporting features
        that are typically found in enterprise editions.
        
        Features:
        - Advanced Sales Analytics
        - Revenue Forecasting
        - Customer Analytics
        - Product Performance Analysis
        - Custom Dashboards
        - Interactive Charts
        - Export to Excel/PDF
    """,
    'depends': [
        'base',
        'web',
        'sale',
        'account',
        'crm',
        'stock',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/analytics_views.xml',
    ],
    'demo': [],
    'assets': {
        'web.assets_backend': [
            'advanced_analytics/static/src/components/**/*',
            'advanced_analytics/static/src/xml/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
}




