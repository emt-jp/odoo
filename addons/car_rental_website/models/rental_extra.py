# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class RentalExtra(models.Model):
    _name = 'rental.extra'
    _description = 'Rental Extra/Add-on'
    _order = 'sequence, name'

    name = fields.Char('Name', required=True, translate=True)
    code = fields.Char('Code', required=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)

    # Pricing
    price_type = fields.Selection([
        ('per_day', 'Per Day'),
        ('per_rental', 'Per Rental (One-time)'),
        ('per_unit_day', 'Per Unit Per Day'),
    ], string='Pricing Type', required=True, default='per_day')
    price = fields.Float('Price', required=True, default=0.0)
    max_price_per_rental = fields.Float('Max Price Per Rental', default=0.0,
        help='Maximum price to charge regardless of rental duration (0 = no max)')
    currency_id = fields.Many2one('res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)

    # Category
    category = fields.Selection([
        ('child_seat', 'Child Seat'),
        ('navigation', 'Navigation/GPS'),
        ('connectivity', 'WiFi/Connectivity'),
        ('driver', 'Additional Driver'),
        ('fuel', 'Fuel Options'),
        ('equipment', 'Equipment'),
        ('winter', 'Winter Equipment'),
        ('service', 'Service'),
        ('other', 'Other'),
    ], string='Category', default='equipment')

    # Availability
    max_quantity = fields.Integer('Max Quantity', default=1,
        help='Maximum quantity that can be added (0 = unlimited)')
    requires_quantity = fields.Boolean('Requires Quantity Selection', default=False)

    # Description
    description = fields.Text('Description', translate=True)
    short_description = fields.Char('Short Description', translate=True)
    image = fields.Binary('Image')
    icon = fields.Char('Icon Class', default='fa-plus-circle',
        help='FontAwesome icon class')

    # Compatibility
    vehicle_type_ids = fields.Many2many('fleet.vehicle.model.category',
        string='Compatible Vehicle Types',
        help='Leave empty for all vehicle types')
    compatible_category_ids = fields.Many2many('fleet.vehicle.model.category',
        'rental_extra_category_rel', 'extra_id', 'category_id',
        string='Compatible Categories')
    min_seats = fields.Integer('Minimum Seats', default=0,
        help='Minimum number of seats required (0 = no minimum)')

    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company)

    def get_price_for_rental(self, days, quantity=1):
        """Calculate price for given rental duration"""
        self.ensure_one()
        if self.price_type == 'per_day':
            return self.price * days
        elif self.price_type == 'per_rental':
            return self.price
        elif self.price_type == 'per_unit_day':
            return self.price * days * quantity
        return 0.0

    def is_compatible_with_vehicle(self, vehicle):
        """Check if extra is compatible with vehicle"""
        self.ensure_one()
        if not self.vehicle_type_ids:
            return True
        return vehicle.category_id.id in self.vehicle_type_ids.ids

    def toggle_active(self):
        """Toggle active status"""
        for record in self:
            record.active = not record.active
