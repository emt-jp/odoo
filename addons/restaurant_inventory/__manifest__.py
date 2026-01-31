# -*- coding: utf-8 -*-
{
    'name': 'Restaurant Inventory Management',
    'version': '1.0.0',
    'category': 'Inventory/Restaurant',
    'summary': 'Manage restaurant ingredients, supplies, and track consumption',
    'description': """
        Restaurant Inventory Management
        ================================

        Comprehensive inventory management for restaurants:

        **Features:**
        - Ingredient inventory tracking
        - Recipe management with BOM (Bill of Materials)
        - Automatic inventory consumption when orders are placed
        - Low stock alerts and notifications
        - Supplier management and purchase orders
        - Waste tracking and reporting
        - Kitchen requisitions
        - Inventory valuation (FIFO/AVCO)
        - Expiration date tracking for perishables
        - Batch/lot tracking
        - Stock take/physical inventory
        - Cost analysis per dish

        **Dashboards:**
        - Current stock levels
        - Fast-moving vs slow-moving items
        - Stock value
        - Waste analysis
        - Purchase recommendations
    """,
    'depends': [
        'stock',
        'stock_account',
        'purchase',
        'purchase_stock',
        'restaurant_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/product_categories.xml',
        'data/stock_locations.xml',
        'views/product_template_views.xml',
        'views/stock_move_views.xml',
        'views/recipe_views.xml',
        'views/waste_tracking_views.xml',
        'views/stock_alert_views.xml',
        'views/inventory_dashboard_views.xml',
        'views/menu_views.xml',
        'reports/inventory_reports.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
}
