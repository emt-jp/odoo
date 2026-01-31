# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class RentalBookingWizard(models.TransientModel):
    _name = 'rental.booking.wizard'
    _description = 'Rental Booking Wizard'
    
    # Customer Information
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    customer_name = fields.Char('Customer Name', related='customer_id.name', readonly=True)
    customer_phone = fields.Char('Customer Phone', related='customer_id.phone', readonly=True)
    customer_email = fields.Char('Customer Email', related='customer_id.email', readonly=True)
    
    # Rental Period
    pickup_date = fields.Datetime('Pickup Date', required=True)
    return_date = fields.Datetime('Return Date', required=True)
    pickup_location = fields.Char('Pickup Location', required=True)
    return_location = fields.Char('Return Location', required=True)
    
    # Vehicle Preferences
    vehicle_type = fields.Selection([
        ('sedan', 'Sedan'),
        ('suv', 'SUV'),
        ('hatchback', 'Hatchback'),
        ('coupe', 'Coupe'),
        ('convertible', 'Convertible'),
        ('wagon', 'Wagon'),
        ('truck', 'Truck'),
        ('van', 'Van'),
        ('motorcycle', 'Motorcycle'),
        ('bus', 'Bus'),
    ], string='Vehicle Type')
    
    rental_category = fields.Selection([
        ('economy', 'Economy'),
        ('compact', 'Compact'),
        ('intermediate', 'Intermediate'),
        ('standard', 'Standard'),
        ('full_size', 'Full Size'),
        ('premium', 'Premium'),
        ('luxury', 'Luxury'),
        ('suv', 'SUV'),
        ('minivan', 'Minivan'),
        ('convertible', 'Convertible'),
    ], string='Rental Category')
    
    # Special Requirements
    special_requirements = fields.Text('Special Requirements')
    additional_drivers = fields.Integer('Additional Drivers', default=0)
    child_seats = fields.Integer('Child Seats', default=0)
    gps_required = fields.Boolean('GPS Required', default=False)
    insurance_required = fields.Boolean('Insurance Required', default=True)
    
    # Available Vehicles
    available_vehicles = fields.Many2many('fleet.vehicle', string='Available Vehicles', compute='_compute_available_vehicles')
    selected_vehicle_id = fields.Many2one('fleet.vehicle', string='Selected Vehicle')
    
    # Pricing
    daily_rate = fields.Monetary('Daily Rate', currency_field='currency_id', compute='_compute_pricing', store=True)
    weekly_rate = fields.Monetary('Weekly Rate', currency_field='currency_id', compute='_compute_pricing', store=True)
    monthly_rate = fields.Monetary('Monthly Rate', currency_field='currency_id', compute='_compute_pricing', store=True)
    estimated_total = fields.Monetary('Estimated Total', currency_field='currency_id', compute='_compute_pricing', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Enterprise Features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.depends('pickup_date', 'return_date', 'vehicle_type', 'rental_category')
    def _compute_available_vehicles(self):
        """Compute available vehicles based on criteria"""
        for wizard in self:
            if wizard._is_enterprise_available() and wizard.pickup_date and wizard.return_date:
                wizard.available_vehicles = wizard._get_available_vehicles()
            else:
                wizard.available_vehicles = self.env['fleet.vehicle']
    
    @api.depends('selected_vehicle_id', 'pickup_date', 'return_date')
    def _compute_pricing(self):
        """Compute pricing based on selected vehicle and dates"""
        for wizard in self:
            if wizard.selected_vehicle_id and wizard.pickup_date and wizard.return_date:
                wizard.daily_rate = wizard.selected_vehicle_id.daily_rate
                wizard.weekly_rate = wizard.selected_vehicle_id.weekly_rate
                wizard.monthly_rate = wizard.selected_vehicle_id.monthly_rate
                
                # Calculate estimated total
                duration = (wizard.return_date - wizard.pickup_date).days
                if duration >= 30 and wizard.monthly_rate:
                    months = duration // 30
                    days = duration % 30
                    wizard.estimated_total = (months * wizard.monthly_rate) + (days * wizard.daily_rate)
                elif duration >= 7 and wizard.weekly_rate:
                    weeks = duration // 7
                    days = duration % 7
                    wizard.estimated_total = (weeks * wizard.weekly_rate) + (days * wizard.daily_rate)
                else:
                    wizard.estimated_total = duration * wizard.daily_rate
            else:
                wizard.daily_rate = 0.0
                wizard.weekly_rate = 0.0
                wizard.monthly_rate = 0.0
                wizard.estimated_total = 0.0
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    def _get_available_vehicles(self):
        """Get available vehicles based on criteria"""
        if not self._is_enterprise_available():
            return self.env['fleet.vehicle']
        
        domain = [
            ('availability_status', '=', 'available'),
            ('is_rental_vehicle', '=', True),
        ]
        
        if self.vehicle_type:
            domain.append(('vehicle_type', '=', self.vehicle_type))
        
        if self.rental_category:
            domain.append(('rental_category', '=', self.rental_category))
        
        vehicles = self.env['fleet.vehicle'].search(domain)
        
        # Filter by availability for the specific dates
        available_vehicles = []
        for vehicle in vehicles:
            if self._is_vehicle_available(vehicle.id):
                available_vehicles.append(vehicle)
        
        return self.env['fleet.vehicle'].browse([v.id for v in available_vehicles])
    
    def _is_vehicle_available(self, vehicle_id):
        """Check if vehicle is available for the booking dates"""
        # Check for overlapping rentals
        overlapping_rentals = self.env['fleet.rental'].search([
            ('vehicle_id', '=', vehicle_id),
            ('state', 'in', ['confirmed', 'in_progress']),
            '|',
            '&', ('start_date', '<=', self.pickup_date), ('end_date', '>=', self.pickup_date),
            '&', ('start_date', '<=', self.return_date), ('end_date', '>=', self.return_date),
        ])
        
        return len(overlapping_rentals) == 0
    
    def action_create_booking(self):
        """Create booking from wizard"""
        if not self._is_enterprise_available():
            raise UserError(_("Booking creation requires the Enterprise edition."))
        
        if not self.selected_vehicle_id:
            raise UserError(_("Please select a vehicle."))
        
        # Validate dates
        if self.pickup_date >= self.return_date:
            raise UserError(_("Pickup date must be before return date."))
        
        if self.pickup_date < fields.Datetime.now():
            raise UserError(_("Pickup date cannot be in the past."))
        
        # Create booking
        booking_data = {
            'customer_id': self.customer_id.id,
            'pickup_date': self.pickup_date,
            'return_date': self.return_date,
            'pickup_location': self.pickup_location,
            'return_location': self.return_location,
            'vehicle_type': self.vehicle_type,
            'rental_category': self.rental_category,
            'special_requirements': self.special_requirements,
            'additional_drivers': self.additional_drivers,
            'child_seats': self.child_seats,
            'gps_required': self.gps_required,
            'insurance_required': self.insurance_required,
        }
        
        booking = self.env['fleet.booking'].create(booking_data)
        
        # Assign vehicle
        booking.action_assign_vehicle(self.selected_vehicle_id.id)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.booking',
            'res_id': booking.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_create_rental(self):
        """Create rental directly from wizard"""
        if not self._is_enterprise_available():
            raise UserError(_("Rental creation requires the Enterprise edition."))
        
        if not self.selected_vehicle_id:
            raise UserError(_("Please select a vehicle."))
        
        # Validate dates
        if self.pickup_date >= self.return_date:
            raise UserError(_("Pickup date must be before return date."))
        
        if self.pickup_date < fields.Datetime.now():
            raise UserError(_("Pickup date cannot be in the past."))
        
        # Create rental
        rental_data = {
            'vehicle_id': self.selected_vehicle_id.id,
            'customer_id': self.customer_id.id,
            'start_date': self.pickup_date,
            'end_date': self.return_date,
            'pickup_location': self.pickup_location,
            'return_location': self.return_location,
            'daily_rate': self.daily_rate,
            'weekly_rate': self.weekly_rate,
            'monthly_rate': self.monthly_rate,
            'pickup_instructions': self.special_requirements,
            'insurance_required': self.insurance_required,
        }
        
        rental = self.env['fleet.rental'].create(rental_data)
        
        # Confirm rental
        rental.action_confirm()
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.rental',
            'res_id': rental.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_search_vehicles(self):
        """Search for available vehicles"""
        if not self._is_enterprise_available():
            raise UserError(_("Vehicle search requires the Enterprise edition."))
        
        # Update available vehicles
        self._compute_available_vehicles()
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.available_vehicles.ids)],
            'target': 'new',
            'context': {'search_default_available': 1},
        }
    
    def action_get_vehicle_recommendations(self):
        """Get vehicle recommendations"""
        if not self._is_enterprise_available():
            raise UserError(_("Vehicle recommendations require the Enterprise edition."))
        
        # Get customer preferences
        preferences = {
            'vehicle_type': self.vehicle_type,
            'rental_category': self.rental_category,
            'max_daily_rate': self.estimated_total / max(1, (self.return_date - self.pickup_date).days) if self.return_date and self.pickup_date else 0,
        }
        
        recommendations = self.env['fleet.vehicle'].get_vehicle_recommendations(preferences)
        
        # Update available vehicles with recommendations
        self.available_vehicles = self.env['fleet.vehicle'].browse([r.id for r in recommendations])
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.available_vehicles.ids)],
            'target': 'new',
            'context': {'search_default_recommended': 1},
        }
    
    def action_calculate_pricing(self):
        """Calculate detailed pricing"""
        if not self._is_enterprise_available():
            raise UserError(_("Pricing calculation requires the Enterprise edition."))
        
        if not self.selected_vehicle_id:
            raise UserError(_("Please select a vehicle first."))
        
        # Calculate detailed pricing breakdown
        duration = (self.return_date - self.pickup_date).days
        base_amount = self.estimated_total
        
        # Calculate additional charges
        additional_charges = []
        
        if self.gps_required:
            additional_charges.append({
                'name': 'GPS Navigation',
                'amount': duration * 5.0,  # $5 per day
            })
        
        if self.child_seats > 0:
            additional_charges.append({
                'name': f'Child Seats ({self.child_seats})',
                'amount': duration * self.child_seats * 3.0,  # $3 per seat per day
            })
        
        if self.additional_drivers > 0:
            additional_charges.append({
                'name': f'Additional Drivers ({self.additional_drivers})',
                'amount': duration * self.additional_drivers * 2.0,  # $2 per driver per day
            })
        
        total_additional_charges = sum(charge['amount'] for charge in additional_charges)
        total_amount = base_amount + total_additional_charges
        
        # Show pricing breakdown
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.rental',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_vehicle_id': self.selected_vehicle_id.id,
                'default_customer_id': self.customer_id.id,
                'default_start_date': self.pickup_date,
                'default_end_date': self.return_date,
                'default_pickup_location': self.pickup_location,
                'default_return_location': self.return_location,
                'default_daily_rate': self.daily_rate,
                'default_weekly_rate': self.weekly_rate,
                'default_monthly_rate': self.monthly_rate,
                'default_base_amount': base_amount,
                'default_total_amount': total_amount,
                'pricing_breakdown': {
                    'base_amount': base_amount,
                    'additional_charges': additional_charges,
                    'total_additional_charges': total_additional_charges,
                    'total_amount': total_amount,
                },
            },
        }




