# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class RentalLocation(models.Model):
    _name = 'rental.location'
    _description = 'Rental Pickup/Dropoff Location'
    _order = 'sequence, name'

    name = fields.Char('Location Name', required=True, translate=True)
    code = fields.Char('Code', required=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)

    # Address
    street = fields.Char('Street')
    street2 = fields.Char('Street 2')
    city = fields.Char('City', required=True)
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char('ZIP')
    country_id = fields.Many2one('res.country', string='Country', required=True)

    # Contact
    phone = fields.Char('Phone')
    email = fields.Char('Email')

    # Operating Hours
    monday_open = fields.Float('Monday Open', default=8.0)
    monday_close = fields.Float('Monday Close', default=20.0)
    tuesday_open = fields.Float('Tuesday Open', default=8.0)
    tuesday_close = fields.Float('Tuesday Close', default=20.0)
    wednesday_open = fields.Float('Wednesday Open', default=8.0)
    wednesday_close = fields.Float('Wednesday Close', default=20.0)
    thursday_open = fields.Float('Thursday Open', default=8.0)
    thursday_close = fields.Float('Thursday Close', default=20.0)
    friday_open = fields.Float('Friday Open', default=8.0)
    friday_close = fields.Float('Friday Close', default=20.0)
    saturday_open = fields.Float('Saturday Open', default=9.0)
    saturday_close = fields.Float('Saturday Close', default=18.0)
    sunday_open = fields.Float('Sunday Open', default=10.0)
    sunday_close = fields.Float('Sunday Close', default=16.0)

    # Location Type
    location_type = fields.Selection([
        ('airport', 'Airport'),
        ('city', 'City Center'),
        ('station', 'Train Station'),
        ('hotel', 'Hotel'),
        ('other', 'Other'),
    ], string='Location Type', default='city')

    # Fees
    pickup_fee = fields.Float('Pickup Fee', default=0.0)
    dropoff_fee = fields.Float('Dropoff Fee', default=0.0)
    different_location_fee = fields.Float('Different Dropoff Location Fee', default=0.0,
        help='Extra fee when customer drops off at a different location')

    # Coordinates for map
    latitude = fields.Float('Latitude', digits=(10, 7))
    longitude = fields.Float('Longitude', digits=(10, 7))

    # Description
    description = fields.Html('Description', translate=True)
    image = fields.Binary('Image')
    notes = fields.Text('Notes')

    # Statistics
    booking_count = fields.Integer('Bookings', compute='_compute_booking_count')

    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company)

    @api.depends()
    def _compute_booking_count(self):
        for location in self:
            pickup_count = self.env['rental.booking'].search_count([
                ('pickup_location_id', '=', location.id)
            ])
            dropoff_count = self.env['rental.booking'].search_count([
                ('dropoff_location_id', '=', location.id)
            ])
            location.booking_count = pickup_count + dropoff_count

    def get_full_address(self):
        """Return formatted full address"""
        self.ensure_one()
        parts = [self.street, self.street2, self.city]
        if self.state_id:
            parts.append(self.state_id.name)
        parts.append(self.zip)
        if self.country_id:
            parts.append(self.country_id.name)
        return ', '.join(filter(None, parts))

    def get_operating_hours(self, day):
        """Get operating hours for a specific day (0=Monday, 6=Sunday)"""
        self.ensure_one()
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        day_name = days[day]
        return {
            'open': getattr(self, f'{day_name}_open'),
            'close': getattr(self, f'{day_name}_close'),
        }
