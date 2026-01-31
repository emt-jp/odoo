# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import uuid
import json


class RentalBooking(models.Model):
    _name = 'rental.booking'
    _description = 'Car Rental Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'

    name = fields.Char('Booking Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))

    # Customer
    partner_id = fields.Many2one('res.partner', string='Customer', required=True,
        tracking=True, domain=[('is_company', '=', False)])
    partner_email = fields.Char(related='partner_id.email', string='Email')
    partner_phone = fields.Char(related='partner_id.phone', string='Phone')

    # Vehicle
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True,
        tracking=True, domain=[('rental_available', '=', True)])
    vehicle_image = fields.Binary(related='vehicle_id.image_128')
    vehicle_name = fields.Char(related='vehicle_id.name', string='Vehicle Name')

    # Dates
    pickup_date = fields.Datetime('Pickup Date/Time', required=True, tracking=True)
    dropoff_date = fields.Datetime('Dropoff Date/Time', required=True, tracking=True)
    rental_days = fields.Integer('Rental Days', compute='_compute_rental_days', store=True)

    # Locations
    pickup_location_id = fields.Many2one('rental.location', string='Pickup Location',
        required=True, tracking=True)
    dropoff_location_id = fields.Many2one('rental.location', string='Dropoff Location',
        required=True, tracking=True)
    same_location = fields.Boolean('Same Dropoff Location',
        compute='_compute_same_location', store=True)

    # Insurance
    insurance_id = fields.Many2one('rental.insurance', string='Insurance Plan',
        tracking=True)
    insurance_total = fields.Float('Insurance Total', compute='_compute_totals', store=True)

    # Extras
    extra_line_ids = fields.One2many('rental.booking.extra', 'booking_id', string='Extras')
    extras_total = fields.Float('Extras Total', compute='_compute_totals', store=True)

    # Pricing
    currency_id = fields.Many2one('res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)
    daily_rate = fields.Float('Daily Rate', required=True)
    vehicle_total = fields.Float('Vehicle Total', compute='_compute_totals', store=True)
    location_fee = fields.Float('Location Fee', compute='_compute_totals', store=True)
    subtotal = fields.Float('Subtotal', compute='_compute_totals', store=True)
    tax_amount = fields.Float('Tax', compute='_compute_totals', store=True)
    tax_rate = fields.Float('Tax Rate (%)', default=10.0)
    total_amount = fields.Float('Total Amount', compute='_compute_totals', store=True)

    # Payment
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ], string='Payment Status', default='not_paid', tracking=True)
    payment_method = fields.Selection([
        ('stripe', 'Stripe (Credit Card)'),
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
    ], string='Payment Method')
    stripe_payment_intent = fields.Char('Stripe Payment Intent')
    stripe_checkout_session = fields.Char('Stripe Checkout Session')
    amount_paid = fields.Float('Amount Paid', default=0.0)

    # Status
    state = fields.Selection([
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='new', tracking=True)

    # Cancellation
    cancelled_date = fields.Datetime('Cancelled Date')
    cancellation_reason = fields.Text('Cancellation Reason')
    refund_amount = fields.Float('Refund Amount')

    # Portal
    access_token = fields.Char('Access Token', copy=False)

    # Notes
    customer_notes = fields.Text('Customer Notes')
    internal_notes = fields.Text('Internal Notes')

    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('rental.booking') or _('New')
            if not vals.get('access_token'):
                vals['access_token'] = str(uuid.uuid4())
        return super().create(vals_list)

    @api.depends('pickup_date', 'dropoff_date')
    def _compute_rental_days(self):
        for booking in self:
            if booking.pickup_date and booking.dropoff_date:
                delta = booking.dropoff_date - booking.pickup_date
                booking.rental_days = max(1, delta.days + (1 if delta.seconds > 0 else 0))
            else:
                booking.rental_days = 0

    @api.depends('pickup_location_id', 'dropoff_location_id')
    def _compute_same_location(self):
        for booking in self:
            booking.same_location = booking.pickup_location_id == booking.dropoff_location_id

    @api.depends('daily_rate', 'rental_days', 'insurance_id', 'extra_line_ids',
                 'pickup_location_id', 'dropoff_location_id', 'same_location', 'tax_rate')
    def _compute_totals(self):
        for booking in self:
            # Vehicle cost
            booking.vehicle_total = booking.daily_rate * booking.rental_days

            # Insurance cost
            if booking.insurance_id:
                booking.insurance_total = booking.insurance_id.daily_rate * booking.rental_days
            else:
                booking.insurance_total = 0.0

            # Extras cost
            extras_total = 0.0
            for line in booking.extra_line_ids:
                extras_total += line.subtotal
            booking.extras_total = extras_total

            # Location fees
            location_fee = 0.0
            if booking.pickup_location_id:
                location_fee += booking.pickup_location_id.pickup_fee
            if booking.dropoff_location_id:
                location_fee += booking.dropoff_location_id.dropoff_fee
                if not booking.same_location:
                    location_fee += booking.dropoff_location_id.different_location_fee
            booking.location_fee = location_fee

            # Subtotal
            booking.subtotal = (booking.vehicle_total + booking.insurance_total +
                               booking.extras_total + booking.location_fee)

            # Tax
            booking.tax_amount = booking.subtotal * (booking.tax_rate / 100)

            # Total
            booking.total_amount = booking.subtotal + booking.tax_amount

    # Minimum gap in hours between booking time and pickup time
    MIN_BOOKING_PICKUP_GAP_HOURS = 2
    # Minimum gap in hours between consecutive bookings of the same car
    MIN_CONSECUTIVE_BOOKING_GAP_HOURS = 2

    @api.constrains('pickup_date', 'dropoff_date')
    def _check_dates(self):
        for booking in self:
            if booking.pickup_date and booking.dropoff_date:
                if booking.dropoff_date <= booking.pickup_date:
                    raise ValidationError(_('Dropoff date must be after pickup date'))

                # Check minimum 2 hours gap between booking time and pickup time
                if booking.state == 'draft':
                    now = fields.Datetime.now()
                    min_pickup_time = now + timedelta(hours=self.MIN_BOOKING_PICKUP_GAP_HOURS)
                    if booking.pickup_date < min_pickup_time:
                        raise ValidationError(
                            _('Pickup time must be at least %d hours from now. '
                              'Earliest available pickup: %s') % (
                                self.MIN_BOOKING_PICKUP_GAP_HOURS,
                                min_pickup_time.strftime('%Y-%m-%d %H:%M')
                            )
                        )

    @api.constrains('vehicle_id', 'pickup_date', 'dropoff_date', 'state')
    def _check_vehicle_availability(self):
        """Check vehicle availability with 2-hour gap between consecutive bookings"""
        for booking in self:
            if booking.state in ['cancelled', 'completed']:
                continue
            if not booking.vehicle_id or not booking.pickup_date or not booking.dropoff_date:
                continue

            # Add 2-hour buffer to check for conflicts
            buffer_hours = timedelta(hours=self.MIN_CONSECUTIVE_BOOKING_GAP_HOURS)
            check_pickup = booking.pickup_date - buffer_hours
            check_dropoff = booking.dropoff_date + buffer_hours

            # Find conflicting bookings
            domain = [
                ('id', '!=', booking.id),
                ('vehicle_id', '=', booking.vehicle_id.id),
                ('state', 'not in', ['cancelled', 'completed']),
                '|',
                '&', ('pickup_date', '<=', check_dropoff), ('dropoff_date', '>=', check_pickup),
                '&', ('pickup_date', '>=', check_pickup), ('pickup_date', '<=', check_dropoff),
            ]

            conflicting = self.search(domain, limit=1)
            if conflicting:
                raise ValidationError(
                    _('This vehicle is not available for the selected dates. '
                      'There must be at least %d hours gap between bookings. '
                      'Conflicting booking: %s (%s - %s)') % (
                        self.MIN_CONSECUTIVE_BOOKING_GAP_HOURS,
                        conflicting.name,
                        conflicting.pickup_date.strftime('%Y-%m-%d %H:%M'),
                        conflicting.dropoff_date.strftime('%Y-%m-%d %H:%M')
                    )
                )

    def action_confirm(self):
        """Confirm booking - admin confirms the booking"""
        for booking in self:
            if booking.state != 'new':
                raise UserError(_('Only new bookings can be confirmed'))
            booking.write({'state': 'confirmed'})
            booking._send_status_email('confirmed')

    def action_mark_paid(self):
        """Mark booking as paid"""
        for booking in self:
            if booking.state != 'confirmed':
                raise UserError(_('Only confirmed bookings can be marked as paid'))
            booking.write({
                'state': 'paid',
                'payment_state': 'paid',
                'amount_paid': booking.total_amount,
            })
            booking._send_status_email('paid')

    def action_start_rental(self):
        """Mark rental as in progress"""
        for booking in self:
            if booking.state != 'paid':
                raise UserError(_('Only paid bookings can be started'))
            booking.write({'state': 'in_progress'})
            booking._send_status_email('in_progress')

    def action_complete(self):
        """Complete the rental"""
        for booking in self:
            if booking.state != 'in_progress':
                raise UserError(_('Only in-progress rentals can be completed'))
            booking.write({'state': 'completed'})
            booking._send_completion_email()

    def action_cancel(self):
        """Cancel the booking"""
        for booking in self:
            if booking.state in ['completed', 'cancelled']:
                raise UserError(_('Cannot cancel completed or already cancelled bookings'))

            refund = 0.0
            if booking.payment_state == 'paid':
                # Calculate refund based on cancellation policy
                hours_until_pickup = (booking.pickup_date - fields.Datetime.now()).total_seconds() / 3600
                if hours_until_pickup > 48:
                    refund = booking.amount_paid  # Full refund (100%)
                elif hours_until_pickup > 24:
                    refund = booking.amount_paid * 0.90  # 10% penalty, 90% refund
                else:
                    refund = booking.amount_paid * 0.85  # 15% penalty, 85% refund

            booking.write({
                'state': 'cancelled',
                'cancelled_date': fields.Datetime.now(),
                'refund_amount': refund,
            })

            booking._send_status_email('cancelled')

            if refund > 0:
                booking._process_refund()

    def _send_status_email(self, status):
        """Send email notification for status change"""
        template_map = {
            'new': 'car_rental_website.email_template_booking_new',
            'confirmed': 'car_rental_website.email_template_booking_confirmed',
            'paid': 'car_rental_website.email_template_booking_paid',
            'in_progress': 'car_rental_website.email_template_booking_started',
            'cancelled': 'car_rental_website.email_template_booking_cancelled',
        }
        template_ref = template_map.get(status)
        if template_ref:
            template = self.env.ref(template_ref, raise_if_not_found=False)
            if template:
                template.send_mail(self.id, force_send=True)

    def _send_completion_email(self):
        """Send thank you email with survey on completion"""
        # Send thank you email
        template = self.env.ref('car_rental_website.email_template_booking_completed',
                               raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

        # Send survey email (separate template)
        survey_template = self.env.ref('car_rental_website.email_template_booking_survey',
                                       raise_if_not_found=False)
        if survey_template:
            survey_template.send_mail(self.id, force_send=True)

    def _process_refund(self):
        """Process refund through payment provider"""
        # Implement Stripe refund logic
        pass

    def get_portal_url(self):
        """Get portal URL for customer"""
        self.ensure_one()
        return f'/my/rental/{self.id}?access_token={self.access_token}'

    def create_stripe_checkout(self):
        """Create Stripe checkout session"""
        self.ensure_one()
        company = self.company_id

        if not company.stripe_enabled or not company.stripe_secret_key:
            raise UserError(_('Stripe is not configured'))

        try:
            import stripe
            stripe.api_key = company.stripe_secret_key

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': self.currency_id.name.lower(),
                        'unit_amount': int(self.total_amount * 100),
                        'product_data': {
                            'name': f'Car Rental: {self.vehicle_name}',
                            'description': f'{self.rental_days} days rental - {self.pickup_date.strftime("%Y-%m-%d")} to {self.dropoff_date.strftime("%Y-%m-%d")}',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'{base_url}/rental/payment/success?booking_id={self.id}&session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f'{base_url}/rental/payment/cancel?booking_id={self.id}',
                customer_email=self.partner_email,
                metadata={
                    'booking_id': str(self.id),
                    'booking_ref': self.name,
                },
            )

            self.write({
                'stripe_checkout_session': session.id,
                'state': 'pending',
            })

            return session.url

        except ImportError:
            raise UserError(_('Stripe library not installed'))
        except Exception as e:
            raise UserError(_('Stripe error: %s') % str(e))


class RentalBookingExtra(models.Model):
    _name = 'rental.booking.extra'
    _description = 'Rental Booking Extra Line'

    booking_id = fields.Many2one('rental.booking', string='Booking',
        required=True, ondelete='cascade')
    extra_id = fields.Many2one('rental.extra', string='Extra', required=True)
    quantity = fields.Integer('Quantity', default=1)
    unit_price = fields.Float('Unit Price')
    subtotal = fields.Float('Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('quantity', 'unit_price', 'booking_id.rental_days', 'extra_id.price_type')
    def _compute_subtotal(self):
        for line in self:
            if line.extra_id and line.booking_id:
                days = line.booking_id.rental_days or 1
                line.subtotal = line.extra_id.get_price_for_rental(days, line.quantity)
            else:
                line.subtotal = 0.0

    @api.onchange('extra_id')
    def _onchange_extra_id(self):
        if self.extra_id:
            self.unit_price = self.extra_id.price
