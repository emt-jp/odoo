# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Advanced Inventory',
    'version': '1.0.0',
    'category': 'Inventory',
    'summary': 'Advanced inventory management features',
    'description': """
        Advanced Inventory Module
        =========================
        
        This module provides advanced inventory management features
        that are typically found in enterprise editions.
        
        Features:
        - Advanced Warehouse Management
        - Multi-Location Inventory
        - Barcode Scanning
        - Cycle Counting
        - Demand Forecasting
        - Reorder Point Management
        - Advanced Picking Strategies
        - Inventory Analytics
        - Quality Control
        - Serial Number Tracking
    """,
    'depends': [
        'base',
        'web',
        'stock',
        'product',
        'purchase',
        'sale',
        'account',
        'mail',
    ],
    'data': [],
    'demo': [],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
}




