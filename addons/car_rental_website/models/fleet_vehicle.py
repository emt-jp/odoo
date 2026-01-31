# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta


class FleetVehicleRental(models.Model):
    _inherit = 'fleet.vehicle'

    # Website Rental Settings
    rental_available = fields.Boolean('Available for Online Rental', default=True)
    rental_daily_rate = fields.Float('Daily Rental Rate', default=0.0)
    rental_weekly_rate = fields.Float('Weekly Rate (7+ days)', default=0.0,
        help='Discounted rate for rentals of 7 days or more')
    rental_monthly_rate = fields.Float('Monthly Rate (30+ days)', default=0.0,
        help='Discounted rate for rentals of 30 days or more')

    # Website Display
    website_published = fields.Boolean('Published on Website', default=True)
    website_sequence = fields.Integer('Website Sequence', default=10)
    website_description = fields.Html('Website Description', translate=True)
    website_short_description = fields.Char('Short Description', translate=True)

    # Features for display
    feature_ids = fields.Many2many('fleet.vehicle.feature', string='Features')

    # Images
    image_ids = fields.One2many('fleet.vehicle.image', 'vehicle_id', string='Gallery Images')

    # Specifications for display
    spec_engine = fields.Char('Engine')
    spec_horsepower = fields.Char('Horsepower')
    spec_acceleration = fields.Char('0-100 km/h')
    spec_top_speed = fields.Char('Top Speed')
    spec_trunk_capacity = fields.Char('Trunk Capacity')

    # Availability
    min_rental_days = fields.Integer('Minimum Rental Days', default=1)
    max_rental_days = fields.Integer('Maximum Rental Days', default=30)
    advance_booking_days = fields.Integer('Advance Booking Required (days)', default=0)

    # Location
    current_location_id = fields.Many2one('rental.location', string='Current Location')
    home_location_id = fields.Many2one('rental.location', string='Home Location')

    # Booking Stats
    rental_booking_count = fields.Integer('Bookings', compute='_compute_rental_booking_count')

    @api.depends()
    def _compute_rental_booking_count(self):
        for vehicle in self:
            vehicle.rental_booking_count = self.env['rental.booking'].search_count([
                ('vehicle_id', '=', vehicle.id),
            ])

    def get_daily_rate(self, days=1):
        """Get daily rate based on rental duration"""
        self.ensure_one()
        if days >= 30 and self.rental_monthly_rate:
            return self.rental_monthly_rate
        elif days >= 7 and self.rental_weekly_rate:
            return self.rental_weekly_rate
        return self.rental_daily_rate

    # Minimum gap in hours between consecutive bookings
    MIN_CONSECUTIVE_BOOKING_GAP_HOURS = 2

    def get_earliest_available_pickup(self):
        """Get the earliest available pickup time (now + 2 hours)"""
        self.ensure_one()
        return datetime.now() + timedelta(hours=self.MIN_CONSECUTIVE_BOOKING_GAP_HOURS)


class FleetVehicleFeature(models.Model):
    _name = 'fleet.vehicle.feature'
    _description = 'Vehicle Feature'
    _order = 'sequence, name'

    name = fields.Char('Feature Name', required=True, translate=True)
    code = fields.Char('Code')
    sequence = fields.Integer('Sequence', default=10)
    icon = fields.Char('Icon Class', default='fa-check')
    category = fields.Selection([
        ('comfort', 'Comfort'),
        ('safety', 'Safety'),
        ('technology', 'Technology'),
        ('performance', 'Performance'),
    ], string='Category', default='comfort')


class FleetVehicleImage(models.Model):
    _inherit = 'fleet.vehicle.image'
    _description = 'Vehicle Gallery Image'
