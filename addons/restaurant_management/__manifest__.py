# -*- coding: utf-8 -*-
{
    'name': 'Restaurant Management System',
    'version': '1.0.0',
    'category': 'Sales/Restaurant',
    'summary': 'Complete restaurant management with tables, orders, kitchen display, and analytics',
    'description': """
        Restaurant Management System
        ============================

        A comprehensive restaurant management solution with:

        **Core Features:**
        - Table Management (floor plans, table status, capacity)
        - Menu Management (categories, items, pricing, modifiers)
        - Order Management (dine-in, takeout, delivery)
        - Kitchen Display System (real-time order tracking)
        - Reservations & Bookings
        - Billing & Payment Processing
        - Staff Management (waiters, chefs, shifts)

        **Analytics & Reporting:**
        - Real-time dashboard with KPIs
        - Sales analytics by time, menu item, waiter
        - Table turnover reports
        - Popular menu items analysis
        - Revenue tracking

        **Modern UI/UX:**
        - Intuitive kanban views for orders and reservations
        - Color-coded status badges
        - Visual table layouts
        - Quick action buttons
        - Mobile-responsive design
    """,
    'depends': [
        'base',
        'web',
        'sale',
        'account',
        'stock',
        'product',
        'mail',
        'calendar',
        'hr',
    ],
    'data': [
        'security/restaurant_security.xml',
        'security/ir.model.access.csv',
        'data/menu_categories_data.xml',
        'views/dashboard_views.xml',
        'views/restaurant_table_views.xml',
        'views/restaurant_floor_views.xml',
        'views/restaurant_order_views.xml',
        'views/restaurant_reservation_views.xml',
        'views/kitchen_display_views.xml',
        'views/menu_item_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'post_init_hook': 'post_init_hook',
}
