# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Car Rental & Fleet Management',
    'version': '1.0.0',
    'category': 'Fleet',
    'summary': 'Complete car rental and fleet management solution',
    'description': """
        Car Rental & Fleet Management Module
        ====================================
        
        This module provides a comprehensive solution for managing car rentals
        and fleet operations with enterprise-grade features.
        
        Features:
        - Vehicle Fleet Management
        - Car Rental Operations
        - Booking & Reservation System
        - Maintenance & Service Management
        - Driver Management
        - GPS Tracking & Telematics
        - Fuel Management
        - Insurance & Documentation
        - Financial Management
        - Analytics & Reporting
        - Mobile App Integration
        - API Integration
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
        'calendar',
        'hr',
        'fleet',
        'project',
    ],
    'data': [],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
}




