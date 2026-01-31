# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, fields, _
from odoo.http import request
from datetime import datetime, timedelta
import json


class FleetWebsite(http.Controller):

    def _get_vehicle_domain(self):
        """Base domain for rental vehicles"""
        return [
            ('is_rental_vehicle', '=', True),
            ('availability_status', '=', 'available'),
        ]

    def _get_categories_with_count(self):
        """Get vehicle categories with vehicle counts"""
        Vehicle = request.env['fleet.vehicle'].sudo()
        vehicles = Vehicle.search(self._get_vehicle_domain())

        category_counts = {}
        for vehicle in vehicles:
            cat = vehicle.rental_category or 'Standard'
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Map categories to icons
        category_icons = {
            'economy': 'fa-car-side',
            'compact': 'fa-car',
            'sedan': 'fa-car-alt',
            'suv': 'fa-truck',
            'luxury': 'fa-gem',
            'van': 'fa-shuttle-van',
            'sports': 'fa-flag-checkered',
            'electric': 'fa-bolt',
        }

        categories = []
        for name, count in category_counts.items():
            icon = category_icons.get(name.lower(), 'fa-car')
            categories.append({
                'name': name,
                'count': count,
                'icon': icon,
            })

        return sorted(categories, key=lambda x: x['count'], reverse=True)

    # ==================== HOMEPAGE ====================

    @http.route(['/rent', '/rent-a-car'], type='http', auth='public', website=True)
    def rental_home(self, **kw):
        """Car Rental Homepage"""
        Vehicle = request.env['fleet.vehicle'].sudo()

        # Get featured vehicles (available, with images, ordered by daily_rate)
        featured_vehicles = Vehicle.search(
            self._get_vehicle_domain() + [('image_front', '!=', False)],
            limit=8,
            order='daily_rate asc'
        )

        # Get all categories
        all_categories = self._get_categories_with_count()

        # Get unique category names for search dropdown
        categories = list(set(Vehicle.search(self._get_vehicle_domain()).mapped('rental_category')))
        categories = [c for c in categories if c]  # Remove empty

        values = {
            'featured_vehicles': featured_vehicles,
            'all_categories': all_categories,
            'categories': categories,
            'datetime': datetime,
        }

        return request.render('car_rental_fleet.website_rental_home', values)

    # ==================== VEHICLE LISTING ====================

    @http.route(['/fleet', '/fleet/vehicles', '/fleet/page/<int:page>'], type='http', auth='public', website=True)
    def fleet_vehicles(self, page=1, **kw):
        """Display available vehicles for rental with filtering"""
        Vehicle = request.env['fleet.vehicle'].sudo()

        domain = self._get_vehicle_domain()

        # Apply filters
        category = kw.get('category')
        if category:
            domain.append(('rental_category', '=', category))

        max_price = kw.get('max_price')
        if max_price:
            try:
                domain.append(('daily_rate', '<=', float(max_price)))
            except ValueError:
                pass

        transmission = kw.get('transmission')
        if transmission:
            if isinstance(transmission, str):
                domain.append(('transmission', '=', transmission))
            elif isinstance(transmission, list):
                domain.append(('transmission', 'in', transmission))

        # Sorting
        sort = kw.get('sort', 'price_asc')
        order_map = {
            'price_asc': 'daily_rate asc',
            'price_desc': 'daily_rate desc',
            'name': 'name asc',
        }
        order = order_map.get(sort, 'daily_rate asc')

        # Pagination
        vehicle_count = Vehicle.search_count(domain)
        pager = request.website.pager(
            url='/fleet',
            url_args={'category': category, 'max_price': max_price, 'sort': sort},
            total=vehicle_count,
            page=page,
            step=12,
        )

        vehicles = Vehicle.search(domain, order=order, limit=12, offset=pager['offset'])

        # Get all categories for filter
        all_vehicles = Vehicle.search(self._get_vehicle_domain())
        categories = list(set(all_vehicles.mapped('rental_category')))
        categories = [c for c in categories if c]

        values = {
            'vehicles': vehicles,
            'categories': categories,
            'selected_category': category,
            'max_price': max_price,
            'sort': sort,
            'search_count': vehicle_count,
            'pager': pager,
            'pickup_date': kw.get('pickup_date'),
            'return_date': kw.get('return_date'),
            'datetime': datetime,
        }

        return request.render('car_rental_fleet.website_fleet_vehicles', values)

    # ==================== VEHICLE SEARCH ====================

    @http.route(['/fleet/search'], type='http', auth='public', website=True)
    def fleet_search(self, **kw):
        """Search available vehicles by date and category"""
        Vehicle = request.env['fleet.vehicle'].sudo()
        Rental = request.env['fleet.rental'].sudo()
        Maintenance = request.env['fleet.maintenance'].sudo()

        pickup_date = kw.get('pickup_date')
        return_date = kw.get('return_date')
        category = kw.get('category')

        domain = self._get_vehicle_domain()

        if category:
            domain.append(('rental_category', '=', category))

        vehicles = Vehicle.search(domain)

        # Filter by availability if dates provided
        if pickup_date and return_date:
            try:
                pickup_dt = datetime.strptime(pickup_date, '%Y-%m-%d')
                return_dt = datetime.strptime(return_date, '%Y-%m-%d')

                available_vehicles = []
                for vehicle in vehicles:
                    # Check for overlapping rentals
                    overlapping = Rental.search_count([
                        ('vehicle_id', '=', vehicle.id),
                        ('state', 'in', ['confirmed', 'in_progress']),
                        '|',
                        '&', ('start_date', '<=', return_dt), ('end_date', '>=', pickup_dt),
                        '&', ('start_date', '>=', pickup_dt), ('start_date', '<=', return_dt),
                    ])

                    # Check for maintenance
                    maintenance = Maintenance.search_count([
                        ('vehicle_id', '=', vehicle.id),
                        ('status', 'in', ['scheduled', 'in_progress']),
                        ('service_start_date', '!=', False),
                        ('service_end_date', '!=', False),
                        '|',
                        '&', ('service_start_date', '<=', return_dt), ('service_end_date', '>=', pickup_dt),
                        '&', ('service_start_date', '>=', pickup_dt), ('service_start_date', '<=', return_dt),
                    ])

                    if not overlapping and not maintenance:
                        available_vehicles.append(vehicle)

                vehicles = available_vehicles
            except ValueError:
                pass  # Invalid date format, show all

        # Get categories for filter
        all_vehicles = Vehicle.search(self._get_vehicle_domain())
        categories = list(set(all_vehicles.mapped('rental_category')))
        categories = [c for c in categories if c]

        values = {
            'vehicles': vehicles,
            'categories': categories,
            'pickup_date': pickup_date,
            'return_date': return_date,
            'selected_category': category,
            'search_count': len(vehicles) if isinstance(vehicles, list) else vehicles.search_count(domain),
            'datetime': datetime,
        }

        return request.render('car_rental_fleet.website_fleet_vehicles', values)

    # ==================== VEHICLE DETAIL ====================

    @http.route(['/fleet/vehicle/<int:vehicle_id>'], type='http', auth='public', website=True)
    def fleet_vehicle_detail(self, vehicle_id, **kw):
        """Display vehicle details"""
        Vehicle = request.env['fleet.vehicle'].sudo()

        vehicle = Vehicle.browse(vehicle_id)
        if not vehicle.exists() or not vehicle.is_rental_vehicle:
            return request.redirect('/fleet')

        # Get similar vehicles (same category)
        similar_vehicles = Vehicle.search([
            ('id', '!=', vehicle.id),
            ('is_rental_vehicle', '=', True),
            ('availability_status', '=', 'available'),
            ('rental_category', '=', vehicle.rental_category),
        ], limit=4)

        values = {
            'vehicle': vehicle,
            'similar_vehicles': similar_vehicles,
            'pickup_date': kw.get('pickup_date'),
            'return_date': kw.get('return_date'),
            'datetime': datetime,
        }

        return request.render('car_rental_fleet.website_vehicle_detail', values)

    # ==================== BOOKING ====================

    @http.route(['/fleet/book/<int:vehicle_id>'], type='http', auth='user', website=True)
    def fleet_book(self, vehicle_id, **kw):
        """Show booking form"""
        Vehicle = request.env['fleet.vehicle'].sudo()

        vehicle = Vehicle.browse(vehicle_id)
        if not vehicle.exists() or not vehicle.is_rental_vehicle:
            return request.redirect('/fleet')

        pickup_date = kw.get('pickup_date', (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
        return_date = kw.get('return_date', (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'))

        values = {
            'vehicle': vehicle,
            'pickup_date': pickup_date,
            'return_date': return_date,
            'partner': request.env.user.partner_id,
            'datetime': datetime,
        }

        return request.render('car_rental_fleet.website_booking_form', values)

    @http.route(['/fleet/book/submit'], type='http', auth='user', website=True, methods=['POST'])
    def fleet_book_submit(self, **kw):
        """Submit booking"""
        vehicle_id = int(kw.get('vehicle_id'))
        pickup_date = kw.get('pickup_date')
        return_date = kw.get('return_date')
        pickup_location = kw.get('pickup_location')
        return_location = kw.get('return_location')
        contact_phone = kw.get('contact_phone')
        special_requirements = kw.get('special_requirements', '')

        Vehicle = request.env['fleet.vehicle'].sudo()
        Booking = request.env['fleet.booking'].sudo()

        vehicle = Vehicle.browse(vehicle_id)
        if not vehicle.exists():
            return request.redirect('/fleet')

        partner = request.env.user.partner_id

        # Build special requirements with extras
        extras = []
        if kw.get('extra_insurance'):
            extras.append('Full Insurance Coverage')
        if kw.get('extra_gps'):
            extras.append('GPS Navigation')
        if kw.get('extra_child_seat'):
            extras.append('Child Seat')
        if kw.get('extra_driver'):
            extras.append('Additional Driver')

        if extras:
            special_requirements = f"Extras: {', '.join(extras)}\n{special_requirements}"

        if kw.get('license_number'):
            special_requirements = f"License: {kw.get('license_number')}\n{special_requirements}"

        # Create booking
        booking_vals = {
            'customer_id': partner.id,
            'vehicle_type': vehicle.vehicle_type,
            'rental_category': vehicle.rental_category,
            'pickup_date': datetime.strptime(pickup_date + ' 09:00:00', '%Y-%m-%d %H:%M:%S'),
            'return_date': datetime.strptime(return_date + ' 18:00:00', '%Y-%m-%d %H:%M:%S'),
            'pickup_location': pickup_location,
            'return_location': return_location or pickup_location,
            'contact_phone': contact_phone,
            'special_requirements': special_requirements.strip(),
            'assigned_vehicle_id': vehicle_id,
        }

        # Add promo code if provided
        promo_code = kw.get('promo_code')
        if promo_code:
            booking_vals['promo_code'] = promo_code

        booking = Booking.create(booking_vals)

        # Send notification
        template = request.env['fleet.notification.template'].sudo().search([
            ('notification_type', '=', 'booking_confirmed'),
            ('active', '=', True),
        ], limit=1)

        if template:
            try:
                template.send_notification(booking)
            except Exception:
                pass  # Don't fail booking if notification fails

        # Redirect to success page
        return request.render('car_rental_fleet.website_booking_success', {
            'booking': booking,
        })

    # ==================== AJAX ENDPOINTS ====================

    @http.route(['/fleet/check-availability'], type='json', auth='public', website=True)
    def check_availability(self, vehicle_id, pickup_date, return_date, **kw):
        """AJAX endpoint to check vehicle availability"""
        Vehicle = request.env['fleet.vehicle'].sudo()
        Rental = request.env['fleet.rental'].sudo()
        Maintenance = request.env['fleet.maintenance'].sudo()

        vehicle = Vehicle.browse(int(vehicle_id))
        if not vehicle.exists():
            return {'available': False, 'error': 'Vehicle not found'}

        try:
            pickup_dt = datetime.strptime(pickup_date, '%Y-%m-%d')
            return_dt = datetime.strptime(return_date, '%Y-%m-%d')
        except ValueError:
            return {'available': False, 'error': 'Invalid date format'}

        if return_dt <= pickup_dt:
            return {'available': False, 'error': 'Return date must be after pickup date'}

        # Check for overlapping rentals
        overlapping = Rental.search_count([
            ('vehicle_id', '=', vehicle.id),
            ('state', 'in', ['confirmed', 'in_progress']),
            '|',
            '&', ('start_date', '<=', return_dt), ('end_date', '>=', pickup_dt),
            '&', ('start_date', '>=', pickup_dt), ('start_date', '<=', return_dt),
        ])

        # Check for maintenance
        maintenance = Maintenance.search_count([
            ('vehicle_id', '=', vehicle.id),
            ('status', 'in', ['scheduled', 'in_progress']),
            ('service_start_date', '!=', False),
            ('service_end_date', '!=', False),
            '|',
            '&', ('service_start_date', '<=', return_dt), ('service_end_date', '>=', pickup_dt),
            '&', ('service_start_date', '>=', pickup_dt), ('service_start_date', '<=', return_dt),
        ])

        if overlapping or maintenance:
            return {'available': False, 'error': 'Vehicle not available for selected dates'}

        # Calculate price
        days = (return_dt - pickup_dt).days
        if days < 1:
            days = 1

        total_price = vehicle.daily_rate * days

        return {
            'available': True,
            'daily_rate': vehicle.daily_rate,
            'days': days,
            'total_price': total_price,
        }

    @http.route(['/fleet/calculate-price'], type='json', auth='public', website=True)
    def calculate_price(self, vehicle_id, pickup_date, return_date, promo_code=None, extras=None, **kw):
        """AJAX endpoint to calculate rental price with discounts"""
        Vehicle = request.env['fleet.vehicle'].sudo()
        PricingRule = request.env['fleet.pricing.rule'].sudo()

        vehicle = Vehicle.browse(int(vehicle_id))
        if not vehicle.exists():
            return {'error': 'Vehicle not found'}

        try:
            pickup_dt = datetime.strptime(pickup_date, '%Y-%m-%d')
            return_dt = datetime.strptime(return_date, '%Y-%m-%d')
        except ValueError:
            return {'error': 'Invalid date format'}

        days = (return_dt - pickup_dt).days
        if days < 1:
            days = 1

        base_rate = vehicle.daily_rate
        base_total = base_rate * days

        # Apply pricing rules
        rules = PricingRule.search([
            ('active', '=', True),
        ], order='sequence')

        total_discount = 0
        applied_rules = []

        for rule in rules:
            if hasattr(rule, 'is_applicable') and rule.is_applicable(vehicle, pickup_dt, return_dt, None, promo_code):
                if hasattr(rule, 'calculate_adjustment'):
                    adjustment = rule.calculate_adjustment(base_rate, days)
                    if adjustment < 0:
                        total_discount += abs(adjustment) * days
                        applied_rules.append({
                            'name': rule.name,
                            'discount': abs(adjustment) * days,
                        })

        # Calculate extras
        extras_total = 0
        extras_breakdown = []
        if extras:
            extra_prices = {
                'insurance': 15,
                'gps': 5,
                'child_seat': 8,
                'driver': 10,
            }
            for extra in extras:
                if extra in extra_prices:
                    cost = extra_prices[extra] * days
                    extras_total += cost
                    extras_breakdown.append({
                        'name': extra.replace('_', ' ').title(),
                        'cost': cost,
                    })

        final_total = base_total - total_discount + extras_total

        return {
            'base_rate': base_rate,
            'days': days,
            'base_total': base_total,
            'discount': total_discount,
            'applied_rules': applied_rules,
            'extras': extras_breakdown,
            'extras_total': extras_total,
            'final_total': final_total,
        }

    @http.route(['/fleet/apply-promo'], type='json', auth='public', website=True)
    def apply_promo_code(self, promo_code, vehicle_id=None, **kw):
        """AJAX endpoint to validate and apply promo code"""
        PricingRule = request.env['fleet.pricing.rule'].sudo()

        rule = PricingRule.search([
            ('rule_type', '=', 'promo_code'),
            ('promo_code', '=', promo_code.upper()),
            ('active', '=', True),
        ], limit=1)

        if not rule:
            return {'valid': False, 'error': 'Invalid promo code'}

        # Check validity dates
        today = fields.Date.today()
        if rule.valid_from and today < rule.valid_from:
            return {'valid': False, 'error': 'Promo code not yet active'}
        if rule.valid_until and today > rule.valid_until:
            return {'valid': False, 'error': 'Promo code has expired'}

        # Check usage limit
        if rule.max_uses and rule.current_uses >= rule.max_uses:
            return {'valid': False, 'error': 'Promo code usage limit reached'}

        return {
            'valid': True,
            'name': rule.name,
            'discount_type': rule.adjustment_type,
            'discount_value': abs(rule.adjustment_value),
            'message': f'Promo code applied: {rule.name}',
        }
