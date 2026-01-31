# -*- coding: utf-8 -*-
{
    'name': 'Car Rental Website Platform',
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Online Car Rental Booking Platform with Stripe Payments',
    'description': """
Car Rental Website Platform
===========================
Complete online car rental booking system with:

Customer Features:
- Sign up with email verification
- Upload driving license
- Browse and search available cars
- Book cars with date/time selection
- Select pickup and dropoff locations
- Choose insurance plans (None, Basic, Full)
- Add extras (child seat, GPS, etc.)
- Pay securely with Stripe
- Manage bookings in customer portal
- Cancel bookings

Admin Features:
- Manage pickup/dropoff locations
- Configure insurance plans and pricing
- Manage rental extras
- View and manage all bookings
- Process payments and refunds
    """,
    'author': 'Custom Development',
    'website': '',
    'depends': [
        'website',
        'website_sale',
        'portal',
        'fleet',
        'car_rental_fleet',
        'auth_signup',
        'mail',
    ],
    'data': [
        'security/rental_security.xml',
        'security/ir.model.access.csv',
        'data/rental_data.xml',
        'data/email_templates.xml',
        'views/rental_location_views.xml',
        'views/rental_insurance_views.xml',
        'views/rental_extra_views.xml',
        'views/rental_booking_views.xml',
        'views/res_partner_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/fleet_maintenance_views.xml',
        'views/website_templates.xml',
        'views/portal_templates.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'car_rental_website/static/src/css/rental.css',
            'car_rental_website/static/src/js/rental.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
