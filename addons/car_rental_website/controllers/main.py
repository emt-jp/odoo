# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class CarRentalWebsite(http.Controller):

    # ==================== CAR LISTING ====================

    @http.route('/cars', type='http', auth='public', website=True)
    def car_list(self, **kwargs):
        """List all available cars"""
        domain = [
            ('rental_available', '=', True),
            ('website_published', '=', True),
        ]

        # Filters
        if kwargs.get('category'):
            domain.append(('category_id', '=', int(kwargs['category'])))
        if kwargs.get('transmission'):
            domain.append(('transmission', '=', kwargs['transmission']))
        if kwargs.get('fuel_type'):
            domain.append(('fuel_type', '=', kwargs['fuel_type']))
        if kwargs.get('seats'):
            domain.append(('seats', '>=', int(kwargs['seats'])))

        # Price filter
        if kwargs.get('price_max'):
            domain.append(('rental_daily_rate', '<=', float(kwargs['price_max'])))

        vehicles = request.env['fleet.vehicle'].sudo().search(
            domain, order='website_sequence, rental_daily_rate')

        # Get filter options
        categories = request.env['fleet.vehicle.model.category'].sudo().search([])
        locations = request.env['rental.location'].sudo().search([('active', '=', True)])

        return request.render('car_rental_website.car_list', {
            'vehicles': vehicles,
            'categories': categories,
            'locations': locations,
            'search': kwargs,
        })

    @http.route('/cars/<int:vehicle_id>', type='http', auth='public', website=True)
    def car_detail(self, vehicle_id, **kwargs):
        """Car detail page"""
        vehicle = request.env['fleet.vehicle'].sudo().browse(vehicle_id)
        if not vehicle.exists() or not vehicle.rental_available:
            return request.redirect('/cars')

        locations = request.env['rental.location'].sudo().search([('active', '=', True)])
        insurances = request.env['rental.insurance'].sudo().search([('active', '=', True)])
        extras = request.env['rental.extra'].sudo().search([('active', '=', True)])

        # Filter extras compatible with this vehicle
        compatible_extras = extras.filtered(lambda e: e.is_compatible_with_vehicle(vehicle))

        return request.render('car_rental_website.car_detail', {
            'vehicle': vehicle,
            'locations': locations,
            'insurances': insurances,
            'extras': compatible_extras,
        })

    # ==================== SEARCH & AVAILABILITY ====================

    @http.route('/cars/search', type='http', auth='public', website=True)
    def car_search(self, **kwargs):
        """Search cars with date filters"""
        pickup_date = kwargs.get('pickup_date')
        dropoff_date = kwargs.get('dropoff_date')
        pickup_location = kwargs.get('pickup_location')

        domain = [
            ('rental_available', '=', True),
            ('website_published', '=', True),
        ]

        vehicles = request.env['fleet.vehicle'].sudo().search(domain)

        # Filter by availability if dates provided
        if pickup_date and dropoff_date:
            pickup_dt = datetime.strptime(pickup_date, '%Y-%m-%d')
            dropoff_dt = datetime.strptime(dropoff_date, '%Y-%m-%d')
            vehicles = vehicles.filtered(lambda v: v.is_available(pickup_dt, dropoff_dt))

        locations = request.env['rental.location'].sudo().search([('active', '=', True)])
        categories = request.env['fleet.vehicle.model.category'].sudo().search([])

        return request.render('car_rental_website.car_list', {
            'vehicles': vehicles,
            'categories': categories,
            'locations': locations,
            'search': kwargs,
        })

    @http.route('/cars/check-availability', type='json', auth='public')
    def check_availability(self, vehicle_id, pickup_date, dropoff_date):
        """Check vehicle availability (AJAX)"""
        vehicle = request.env['fleet.vehicle'].sudo().browse(int(vehicle_id))
        if not vehicle.exists():
            return {'available': False, 'error': 'Vehicle not found'}

        pickup_dt = datetime.strptime(pickup_date, '%Y-%m-%d')
        dropoff_dt = datetime.strptime(dropoff_date, '%Y-%m-%d')

        available = vehicle.is_available(pickup_dt, dropoff_dt)
        days = (dropoff_dt - pickup_dt).days or 1
        daily_rate = vehicle.get_daily_rate(days)

        return {
            'available': available,
            'days': days,
            'daily_rate': daily_rate,
            'total': daily_rate * days,
        }

    # ==================== BOOKING FLOW ====================

    @http.route('/cars/<int:vehicle_id>/book', type='http', auth='public', website=True)
    def booking_form(self, vehicle_id, **kwargs):
        """Booking form page"""
        vehicle = request.env['fleet.vehicle'].sudo().browse(vehicle_id)
        if not vehicle.exists() or not vehicle.rental_available:
            return request.redirect('/cars')

        locations = request.env['rental.location'].sudo().search([('active', '=', True)])
        insurances = request.env['rental.insurance'].sudo().search([('active', '=', True)])
        extras = request.env['rental.extra'].sudo().search([('active', '=', True)])

        # Pre-fill dates if provided
        pickup_date = kwargs.get('pickup_date', '')
        dropoff_date = kwargs.get('dropoff_date', '')

        return request.render('car_rental_website.booking_form', {
            'vehicle': vehicle,
            'locations': locations,
            'insurances': insurances,
            'extras': extras.filtered(lambda e: e.is_compatible_with_vehicle(vehicle)),
            'pickup_date': pickup_date,
            'dropoff_date': dropoff_date,
        })

    @http.route('/cars/book/submit', type='http', auth='public', website=True, methods=['POST'])
    def booking_submit(self, **kwargs):
        """Process booking submission"""
        try:
            vehicle_id = int(kwargs.get('vehicle_id'))
            vehicle = request.env['fleet.vehicle'].sudo().browse(vehicle_id)

            if not vehicle.exists():
                return request.redirect('/cars')

            # Parse dates
            pickup_date = datetime.strptime(kwargs['pickup_date'] + ' ' + kwargs.get('pickup_time', '10:00'), '%Y-%m-%d %H:%M')
            dropoff_date = datetime.strptime(kwargs['dropoff_date'] + ' ' + kwargs.get('dropoff_time', '10:00'), '%Y-%m-%d %H:%M')

            # Check availability
            if not vehicle.is_available(pickup_date, dropoff_date):
                return request.render('car_rental_website.booking_error', {
                    'error': _('This vehicle is not available for the selected dates.'),
                })

            # Get or create partner
            partner = self._get_or_create_partner(kwargs)

            # Calculate daily rate
            days = max(1, (dropoff_date - pickup_date).days)
            daily_rate = vehicle.get_daily_rate(days)

            # Create booking
            booking_vals = {
                'partner_id': partner.id,
                'vehicle_id': vehicle.id,
                'pickup_date': pickup_date,
                'dropoff_date': dropoff_date,
                'pickup_location_id': int(kwargs['pickup_location']),
                'dropoff_location_id': int(kwargs['dropoff_location']),
                'daily_rate': daily_rate,
                'customer_notes': kwargs.get('notes', ''),
            }

            # Insurance
            if kwargs.get('insurance'):
                booking_vals['insurance_id'] = int(kwargs['insurance'])

            booking = request.env['rental.booking'].sudo().create(booking_vals)

            # Add extras
            extra_ids = kwargs.getlist('extras') if hasattr(kwargs, 'getlist') else []
            if not extra_ids and kwargs.get('extras'):
                extra_ids = [kwargs.get('extras')] if isinstance(kwargs.get('extras'), str) else kwargs.get('extras', [])

            for extra_id in extra_ids:
                if extra_id:
                    extra = request.env['rental.extra'].sudo().browse(int(extra_id))
                    quantity = int(kwargs.get(f'extra_qty_{extra_id}', 1))
                    request.env['rental.booking.extra'].sudo().create({
                        'booking_id': booking.id,
                        'extra_id': extra.id,
                        'quantity': quantity,
                        'unit_price': extra.price,
                    })

            # Redirect to checkout
            return request.redirect(f'/cars/book/checkout/{booking.id}?access_token={booking.access_token}')

        except Exception as e:
            _logger.error(f'Booking error: {e}')
            return request.render('car_rental_website.booking_error', {
                'error': str(e),
            })

    def _get_or_create_partner(self, kwargs):
        """Get existing partner or create new one"""
        email = kwargs.get('email')
        if not email:
            if request.env.user._is_public():
                raise ValidationError(_('Email is required'))
            return request.env.user.partner_id

        partner = request.env['res.partner'].sudo().search([
            ('email', '=', email)
        ], limit=1)

        if not partner:
            partner = request.env['res.partner'].sudo().create({
                'name': kwargs.get('name', email.split('@')[0]),
                'email': email,
                'phone': kwargs.get('phone'),
                'is_rental_customer': True,
            })

        return partner

    # ==================== CHECKOUT & PAYMENT ====================

    @http.route('/cars/book/checkout/<int:booking_id>', type='http', auth='public', website=True)
    def booking_checkout(self, booking_id, access_token=None, **kwargs):
        """Checkout page with payment"""
        booking = request.env['rental.booking'].sudo().browse(booking_id)

        if not booking.exists() or booking.access_token != access_token:
            return request.redirect('/cars')

        if booking.state not in ['draft', 'pending']:
            return request.redirect(f'/my/rental/{booking.id}?access_token={access_token}')

        company = booking.company_id
        stripe_enabled = company.stripe_enabled and company.stripe_publishable_key

        return request.render('car_rental_website.booking_checkout', {
            'booking': booking,
            'stripe_enabled': stripe_enabled,
            'stripe_key': company.stripe_publishable_key if stripe_enabled else '',
        })

    @http.route('/cars/book/pay/<int:booking_id>', type='http', auth='public', website=True, methods=['POST'])
    def booking_pay(self, booking_id, access_token=None, **kwargs):
        """Process payment"""
        booking = request.env['rental.booking'].sudo().browse(booking_id)

        if not booking.exists() or booking.access_token != access_token:
            return request.redirect('/cars')

        payment_method = kwargs.get('payment_method', 'stripe')

        if payment_method == 'stripe':
            # Create Stripe checkout session
            try:
                checkout_url = booking.create_stripe_checkout()
                return request.redirect(checkout_url)
            except Exception as e:
                return request.render('car_rental_website.booking_error', {
                    'error': str(e),
                })
        else:
            # Other payment methods
            booking.write({
                'payment_method': payment_method,
                'state': 'pending',
            })
            return request.redirect(f'/my/rental/{booking.id}?access_token={booking.access_token}')

    @http.route('/rental/payment/success', type='http', auth='public', website=True)
    def payment_success(self, booking_id=None, session_id=None, **kwargs):
        """Stripe payment success callback"""
        if booking_id:
            booking = request.env['rental.booking'].sudo().browse(int(booking_id))
            if booking.exists() and booking.stripe_checkout_session == session_id:
                booking.write({
                    'payment_state': 'paid',
                    'amount_paid': booking.total_amount,
                    'state': 'confirmed',
                })
                booking._send_confirmation_email()

        return request.render('car_rental_website.payment_success', {
            'booking': booking if booking_id else None,
        })

    @http.route('/rental/payment/cancel', type='http', auth='public', website=True)
    def payment_cancel(self, booking_id=None, **kwargs):
        """Stripe payment cancelled"""
        booking = None
        if booking_id:
            booking = request.env['rental.booking'].sudo().browse(int(booking_id))

        return request.render('car_rental_website.payment_cancel', {
            'booking': booking,
        })

    # ==================== STRIPE WEBHOOK ====================

    @http.route('/rental/stripe/webhook', type='json', auth='public', csrf=False, methods=['POST'])
    def stripe_webhook(self):
        """Handle Stripe webhooks for rental bookings"""
        payload = request.httprequest.data
        sig_header = request.httprequest.headers.get('Stripe-Signature')

        try:
            import stripe
        except ImportError:
            return {'status': 'error'}

        company = request.env['res.company'].sudo().search([
            ('stripe_enabled', '=', True),
            ('stripe_webhook_secret', '!=', False),
        ], limit=1)

        if not company:
            return {'status': 'error'}

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, company.stripe_webhook_secret
            )
        except Exception:
            return {'status': 'error'}

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            booking_id = session.get('metadata', {}).get('booking_id')
            if booking_id:
                booking = request.env['rental.booking'].sudo().browse(int(booking_id))
                if booking.exists():
                    booking.write({
                        'payment_state': 'paid',
                        'amount_paid': booking.total_amount,
                        'state': 'confirmed',
                        'stripe_payment_intent': session.get('payment_intent'),
                    })
                    booking._send_confirmation_email()

        return {'status': 'success'}

    # ==================== EMAIL VERIFICATION ====================

    @http.route('/rental/verify-email/<token>', type='http', auth='public', website=True)
    def verify_email(self, token, **kwargs):
        """Verify customer email"""
        partner = request.env['res.partner'].sudo().search([
            ('email_verification_token', '=', token)
        ], limit=1)

        if partner and partner.verify_email(token):
            return request.render('car_rental_website.email_verified', {
                'success': True,
            })
        else:
            return request.render('car_rental_website.email_verified', {
                'success': False,
            })

    # ==================== LOCATIONS API ====================

    @http.route('/rental/locations', type='json', auth='public')
    def get_locations(self):
        """Get all active locations (AJAX)"""
        locations = request.env['rental.location'].sudo().search([('active', '=', True)])
        return [{
            'id': loc.id,
            'name': loc.name,
            'address': loc.get_full_address(),
            'type': loc.location_type,
            'pickup_fee': loc.pickup_fee,
            'dropoff_fee': loc.dropoff_fee,
        } for loc in locations]
