# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Advanced CRM',
    'version': '1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Advanced CRM features and automation',
    'description': """
        Advanced CRM Module
        ===================
        
        This module provides advanced CRM features that are typically
        found in enterprise editions.
        
        Features:
        - Lead Scoring
        - Email Tracking
        - Social Media Integration
        - Advanced Pipeline Management
        - Customer Segmentation
        - Automated Workflows
        - Advanced Reporting
        - API Integration
    """,
    'depends': [
        'base',
        'web',
        'crm',
        'sale',
        'mail',
        'contacts',
        'utm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_views.xml',
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




