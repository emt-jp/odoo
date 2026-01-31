# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class RentalBooking(models.Model):
    _inherit = 'rental.booking'

    # Driver Assignment
    driver_employee_id = fields.Many2one('hr.employee', string='Assigned Driver',
                                          domain=[('is_driver', '=', True), ('active', '=', True)],
                                          tracking=True)
    driver_required = fields.Boolean('Driver Required', default=False)
    driver_assignment_status = fields.Selection([
        ('not_required', 'Driver Not Required'),
        ('pending', 'Pending Assignment'),
        ('assigned', 'Driver Assigned'),
        ('confirmed', 'Driver Confirmed'),
    ], string='Driver Assignment Status', default='not_required',
       compute='_compute_driver_assignment_status', store=True)

    # Driver Availability Check
    driver_availability_checked = fields.Boolean('Availability Checked', default=False)
    driver_availability_check_date = fields.Datetime('Check Date')
    driver_availability_notes = fields.Text('Availability Notes')

    @api.depends('driver_required', 'driver_employee_id')
    def _compute_driver_assignment_status(self):
        """Compute driver assignment status"""
        for booking in self:
            if not booking.driver_required:
                booking.driver_assignment_status = 'not_required'
            elif not booking.driver_employee_id:
                booking.driver_assignment_status = 'pending'
            elif booking.driver_employee_id and booking.state in ['confirmed', 'assigned']:
                booking.driver_assignment_status = 'assigned'
            elif booking.state == 'in_progress':
                booking.driver_assignment_status = 'confirmed'
            else:
                booking.driver_assignment_status = 'pending'

    @api.constrains('driver_employee_id', 'pickup_date', 'return_date')
    def _check_driver_availability(self):
        """Validate driver availability before assignment"""
        for booking in self:
            if booking.driver_employee_id and booking.driver_required:
                # Check if driver is available
                if not booking.driver_employee_id.is_available_for_driving:
                    raise ValidationError(
                        _('Driver %s is not available for assignment.') %
                        booking.driver_employee_id.name
                    )

                # Check if driver is on leave
                leave = self.env['hr.leave'].search([
                    ('employee_id', '=', booking.driver_employee_id.id),
                    ('state', '=', 'validate'),
                    ('date_from', '<=', booking.return_date),
                    ('date_to', '>=', booking.pickup_date),
                ], limit=1)

                if leave:
                    raise ValidationError(
                        _('Driver %s is on leave from %s to %s.') %
                        (booking.driver_employee_id.name,
                         leave.date_from, leave.date_to)
                    )

                # Check for conflicting bookings
                conflicting = self.search([
                    ('id', '!=', booking.id),
                    ('driver_employee_id', '=', booking.driver_employee_id.id),
                    ('state', 'in', ['confirmed', 'assigned', 'in_progress']),
                    '|',
                    '&', ('pickup_date', '<=', booking.pickup_date),
                         ('return_date', '>=', booking.pickup_date),
                    '&', ('pickup_date', '<=', booking.return_date),
                         ('return_date', '>=', booking.return_date),
                ], limit=1)

                if conflicting:
                    raise ValidationError(
                        _('Driver %s is already assigned to booking %s from %s to %s.') %
                        (booking.driver_employee_id.name, conflicting.name or conflicting.id,
                         conflicting.pickup_date, conflicting.return_date)
                    )

    def action_confirm(self):
        """Override confirm to check driver availability"""
        res = super().action_confirm()

        for booking in self:
            if booking.driver_required and not booking.driver_employee_id:
                # Try to auto-assign driver
                booking._auto_assign_driver()

        return res

    def _auto_assign_driver(self):
        """Automatically assign an available driver"""
        self.ensure_one()

        if not self.driver_required:
            return

        # Get available drivers
        available_drivers = self.env['hr.employee'].get_available_drivers(
            self.pickup_date,
            self.return_date,
            license_type='car'
        )

        if not available_drivers:
            _logger.warning(f'No available drivers for booking {self.name}')
            return

        # Select first available driver
        best_driver = available_drivers[0]

        self.driver_employee_id = best_driver.id
        self.driver_availability_checked = True
        self.driver_availability_check_date = fields.Datetime.now()

        _logger.info(f'Auto-assigned driver {best_driver.name} to booking {self.name}')

        # Send notification
        self.message_post(
            body=_('Driver %s has been automatically assigned to this booking.') %
                 best_driver.name,
            subject=_('Driver Assigned'),
            message_type='notification',
        )
