# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Driver Fields
    is_driver = fields.Boolean('Is Driver', default=False, tracking=True)

    # Driver License Information
    driver_license_number = fields.Char('Driver License Number', tracking=True)
    driver_license_type = fields.Selection([
        ('car', 'Car'),
        ('motorcycle', 'Motorcycle'),
        ('truck', 'Truck'),
        ('bus', 'Bus'),
        ('commercial', 'Commercial'),
    ], string='Driver License Type', tracking=True)
    driver_license_issue_date = fields.Date('License Issue Date')
    driver_license_expiry_date = fields.Date('License Expiry Date', tracking=True)
    driver_license_state = fields.Selection([
        ('valid', 'Valid'),
        ('expired', 'Expired'),
        ('expiring_soon', 'Expiring Soon'),
        ('suspended', 'Suspended'),
        ('revoked', 'Revoked'),
    ], string='License Status', compute='_compute_license_state', store=True)

    # Driver Availability
    is_available_for_driving = fields.Boolean('Available for Driving',
                                               compute='_compute_driver_availability',
                                               store=False)
    current_driving_status = fields.Selection([
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('on_leave', 'On Leave'),
        ('not_available', 'Not Available'),
    ], string='Driving Status', compute='_compute_driving_status', store=True)

    # Driver Statistics
    total_trips = fields.Integer('Total Trips', compute='_compute_driver_stats', store=True)
    total_distance_driven = fields.Float('Total Distance (km)',
                                         compute='_compute_driver_stats', store=True)
    average_trip_rating = fields.Float('Average Rating',
                                        compute='_compute_driver_stats', store=True)

    # Relationships
    assigned_booking_ids = fields.One2many('rental.booking', 'driver_employee_id',
                                            string='Assigned Bookings')

    @api.depends('driver_license_expiry_date')
    def _compute_license_state(self):
        """Compute driver license state based on expiry date"""
        today = fields.Date.today()
        for employee in self:
            if not employee.driver_license_expiry_date:
                employee.driver_license_state = False
            elif employee.driver_license_expiry_date < today:
                employee.driver_license_state = 'expired'
            elif employee.driver_license_expiry_date <= today + timedelta(days=30):
                employee.driver_license_state = 'expiring_soon'
            else:
                employee.driver_license_state = 'valid'

    @api.depends('assigned_booking_ids', 'assigned_booking_ids.state')
    def _compute_driver_stats(self):
        """Compute driver statistics from bookings"""
        for employee in self:
            if employee.is_driver:
                completed_bookings = employee.assigned_booking_ids.filtered(
                    lambda b: b.state == 'completed'
                )
                employee.total_trips = len(completed_bookings)
                employee.total_distance_driven = sum(completed_bookings.mapped('total_distance') or [0])

                # Calculate average rating if available
                ratings = [b.customer_rating for b in completed_bookings if hasattr(b, 'customer_rating') and b.customer_rating > 0]
                employee.average_trip_rating = sum(ratings) / len(ratings) if ratings else 0.0
            else:
                employee.total_trips = 0
                employee.total_distance_driven = 0.0
                employee.average_trip_rating = 0.0

    @api.depends('is_driver', 'driver_license_state', 'active')
    def _compute_driver_availability(self):
        """Check if driver is available for assignments"""
        for employee in self:
            if not employee.is_driver or not employee.active:
                employee.is_available_for_driving = False
                continue

            # Check license validity
            if employee.driver_license_state not in ['valid', 'expiring_soon']:
                employee.is_available_for_driving = False
                continue

            # Check if on leave
            if employee._is_on_leave():
                employee.is_available_for_driving = False
                continue

            # Check if already on an active booking
            if employee._is_on_active_booking():
                employee.is_available_for_driving = False
                continue

            employee.is_available_for_driving = True

    @api.depends('is_driver', 'assigned_booking_ids', 'assigned_booking_ids.state')
    def _compute_driving_status(self):
        """Compute current driving status"""
        for employee in self:
            if not employee.is_driver:
                employee.current_driving_status = 'not_available'
                continue

            # Check if on active booking
            active_bookings = employee.assigned_booking_ids.filtered(
                lambda b: b.state in ['assigned', 'in_progress']
            )
            if active_bookings:
                employee.current_driving_status = 'on_trip'
                continue

            # Check if on leave
            if employee._is_on_leave():
                employee.current_driving_status = 'on_leave'
                continue

            # Check availability
            if employee.is_available_for_driving:
                employee.current_driving_status = 'available'
            else:
                employee.current_driving_status = 'not_available'

    def _is_on_leave(self):
        """Check if employee is currently on leave"""
        self.ensure_one()

        # Check approved leaves
        leave = self.env['hr.leave'].search([
            ('employee_id', '=', self.id),
            ('state', '=', 'validate'),
            ('date_from', '<=', fields.Datetime.now()),
            ('date_to', '>=', fields.Datetime.now()),
        ], limit=1)

        return bool(leave)

    def _is_on_active_booking(self):
        """Check if employee is currently on an active booking"""
        self.ensure_one()
        active_booking = self.assigned_booking_ids.filtered(
            lambda b: b.state in ['assigned', 'in_progress']
        )
        return bool(active_booking)

    @api.constrains('driver_license_expiry_date', 'is_driver')
    def _check_driver_license_expiry(self):
        """Validate driver license is not expired"""
        for employee in self:
            if employee.is_driver and employee.driver_license_expiry_date:
                if employee.driver_license_expiry_date < fields.Date.today():
                    raise ValidationError(
                        _('Cannot activate driver with expired license. '
                          'Employee: %s, Expiry Date: %s') %
                        (employee.name, employee.driver_license_expiry_date)
                    )

    def action_view_bookings(self):
        """Open assigned bookings"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assigned Bookings'),
            'res_model': 'rental.booking',
            'view_mode': 'tree,form',
            'domain': [('driver_employee_id', '=', self.id)],
            'context': {'default_driver_employee_id': self.id},
        }

    @api.model
    def get_available_drivers(self, date_from, date_to, license_type=None):
        """Get available drivers for a specific period"""
        domain = [
            ('is_driver', '=', True),
            ('active', '=', True),
            ('driver_license_state', 'in', ['valid', 'expiring_soon']),
        ]

        if license_type:
            domain.append(('driver_license_type', '=', license_type))

        drivers = self.search(domain)

        # Filter out drivers on leave or on booking during the period
        available_drivers = self.env['hr.employee']
        for driver in drivers:
            # Check leaves
            leave = self.env['hr.leave'].search([
                ('employee_id', '=', driver.id),
                ('state', '=', 'validate'),
                ('date_from', '<=', date_to),
                ('date_to', '>=', date_from),
            ], limit=1)

            if leave:
                continue

            # Check bookings
            booking = self.env['rental.booking'].search([
                ('driver_employee_id', '=', driver.id),
                ('state', 'in', ['confirmed', 'assigned', 'in_progress']),
                ('pickup_date', '<=', date_to),
                ('return_date', '>=', date_from),
            ], limit=1)

            if not booking:
                available_drivers |= driver

        return available_drivers
