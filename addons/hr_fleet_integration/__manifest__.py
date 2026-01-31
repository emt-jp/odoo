# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'HR Fleet Integration',
    'version': '1.0.0',
    'category': 'Human Resources/Fleet',
    'summary': 'Integration between HR and Car Rental Fleet Management',
    'description': """
        HR Fleet Integration Module
        ============================

        This module provides comprehensive integration between HR and Car Rental Fleet systems:

        Features:
        - Driver Management: Link fleet drivers with HR employees
        - Leave Integration: Check driver availability before booking assignments
        - Payroll Integration: Track driver trips for incentive calculation
        - Attendance Integration: GPS-based attendance and check-in/check-out
        - Performance Tracking: Monitor driver performance metrics
        - Auto-reassignment: Automatic booking reassignment on emergency leave
        - Driver availability calendar dashboard
        - Overtime calculation for long-distance trips
        - Fuel allowance and trip bonuses
        - Working hours tracking from trip duration
    """,
    'depends': [
        'hr',
        'hr_attendance',
        'hr_holidays',
        'car_rental_fleet',
        'car_rental_website',
        'calendar',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
