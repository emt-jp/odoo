# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Car Rental & Fleet Management',
    'version': '2.0.0',
    'category': 'Fleet',
    'summary': 'Complete car rental and fleet management solution with portal',
    'description': """
        Car Rental & Fleet Management Module
        ====================================

        This module provides a comprehensive solution for managing car rentals
        and fleet operations with enterprise-grade features.

        Features:
        - Vehicle Fleet Management
        - Car Rental Operations
        - Booking & Reservation System
        - Maintenance & Service Management (with periodic scheduling)
        - Driver Management
        - GPS Tracking & Telematics
        - Fuel Management
        - Insurance & Documentation
        - Financial Management
        - Analytics & Reporting Dashboard
        - Damage Inspection Checklists
        - Dynamic Pricing Rules (seasonal, promo codes, discounts)
        - Email/SMS Notifications
        - Customer Portal for Online Bookings
        - Website Integration
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
        'portal',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_data.xml',
        'views/vehicle_views.xml',
        'views/insurance_views.xml',
        'views/booking_views.xml',
        'views/rental_views.xml',
        'views/maintenance_views.xml',
        'views/fuel_gps_views.xml',
        'views/damage_inspection_views.xml',
        'views/pricing_views.xml',
        'views/notification_views.xml',
        'views/dashboard_views.xml',
        'views/portal_templates.xml',
        'views/website_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
}




