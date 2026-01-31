# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class FleetMaintenanceRental(models.Model):
    _inherit = 'fleet.maintenance'

    # Rental integration fields
    blocks_rental = fields.Boolean('Blocks Rental', default=True,
        help='If checked, vehicle will not be available for rental during maintenance period')
    maintenance_duration_days = fields.Integer('Duration (Days)', default=1,
        help='Number of days the vehicle will be unavailable for rental')
    end_date = fields.Datetime('End Date', compute='_compute_end_date', store=True)

    # Recurrence settings
    is_recurring = fields.Boolean('Recurring Maintenance', default=False)
    recurrence_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly (Every 3 months)'),
        ('semi_annual', 'Semi-Annual (Every 6 months)'),
        ('annual', 'Annual'),
    ], string='Recurrence', default='annual')
    recurrence_count = fields.Integer('Number of Occurrences', default=1,
        help='How many times to repeat (0 = unlimited)')
    next_occurrence_date = fields.Datetime('Next Occurrence', compute='_compute_next_occurrence')

    # Auto-generated maintenance tracking
    parent_maintenance_id = fields.Many2one('fleet.maintenance', string='Parent Maintenance',
        help='Reference to the original recurring maintenance')
    child_maintenance_ids = fields.One2many('fleet.maintenance', 'parent_maintenance_id',
        string='Generated Maintenances')
    occurrence_number = fields.Integer('Occurrence #', default=0)

    @api.depends('scheduled_date', 'maintenance_duration_days')
    def _compute_end_date(self):
        for maintenance in self:
            if maintenance.scheduled_date and maintenance.maintenance_duration_days:
                maintenance.end_date = maintenance.scheduled_date + timedelta(days=maintenance.maintenance_duration_days)
            else:
                maintenance.end_date = maintenance.scheduled_date

    @api.depends('scheduled_date', 'recurrence_type', 'is_recurring')
    def _compute_next_occurrence(self):
        for maintenance in self:
            if maintenance.is_recurring and maintenance.scheduled_date:
                maintenance.next_occurrence_date = maintenance._get_next_date(maintenance.scheduled_date)
            else:
                maintenance.next_occurrence_date = False

    def _get_next_date(self, from_date):
        """Calculate next occurrence date based on recurrence type"""
        if not from_date:
            return False

        if self.recurrence_type == 'monthly':
            return from_date + relativedelta(months=1)
        elif self.recurrence_type == 'quarterly':
            return from_date + relativedelta(months=3)
        elif self.recurrence_type == 'semi_annual':
            return from_date + relativedelta(months=6)
        elif self.recurrence_type == 'annual':
            return from_date + relativedelta(years=1)
        return False

    def action_generate_recurring(self):
        """Generate future maintenance occurrences"""
        self.ensure_one()
        if not self.is_recurring:
            return

        count = self.recurrence_count or 12  # Default 12 occurrences if unlimited
        current_date = self.scheduled_date

        for i in range(1, count + 1):
            next_date = self._get_next_date(current_date)
            if not next_date:
                break

            # Check if already exists
            existing = self.search([
                ('parent_maintenance_id', '=', self.id),
                ('scheduled_date', '=', next_date),
            ], limit=1)

            if not existing:
                self.copy({
                    'scheduled_date': next_date,
                    'parent_maintenance_id': self.id,
                    'is_recurring': False,  # Children are not recurring themselves
                    'occurrence_number': i,
                    'status': 'scheduled',
                })

            current_date = next_date

    @api.model
    def cron_generate_recurring_maintenance(self):
        """Cron job to auto-generate recurring maintenance"""
        # Find all recurring maintenance templates
        recurring = self.search([
            ('is_recurring', '=', True),
            ('status', 'in', ['scheduled', 'completed']),
        ])

        for maintenance in recurring:
            # Generate next 12 months of occurrences
            maintenance.action_generate_recurring()


class FleetVehicleMaintenanceIntegration(models.Model):
    _inherit = 'fleet.vehicle'

    maintenance_ids = fields.One2many('fleet.maintenance', 'vehicle_id', string='Maintenance Records')
    scheduled_maintenance_count = fields.Integer('Scheduled Maintenance',
        compute='_compute_scheduled_maintenance_count')

    @api.depends('maintenance_ids.status')
    def _compute_scheduled_maintenance_count(self):
        for vehicle in self:
            vehicle.scheduled_maintenance_count = self.env['fleet.maintenance'].search_count([
                ('vehicle_id', '=', vehicle.id),
                ('status', '=', 'scheduled'),
            ])

    def is_available(self, pickup_date, dropoff_date, exclude_booking_id=None):
        """Check vehicle availability including maintenance blocks"""
        self.ensure_one()

        if not self.rental_available or not self.website_published:
            return False

        # Check for maintenance blocks
        if self._has_maintenance_conflict(pickup_date, dropoff_date):
            return False

        # Check for booking conflicts (existing logic)
        buffer = timedelta(hours=self.MIN_CONSECUTIVE_BOOKING_GAP_HOURS)
        check_pickup = pickup_date - buffer
        check_dropoff = dropoff_date + buffer

        domain = [
            ('vehicle_id', '=', self.id),
            ('state', 'not in', ['cancelled', 'completed']),
            '|',
            '&', ('pickup_date', '<=', check_dropoff), ('dropoff_date', '>=', check_pickup),
            '&', ('pickup_date', '>=', check_pickup), ('pickup_date', '<=', check_dropoff),
        ]

        if exclude_booking_id:
            domain.append(('id', '!=', exclude_booking_id))

        conflicting = self.env['rental.booking'].search_count(domain)
        return conflicting == 0

    def _has_maintenance_conflict(self, pickup_date, dropoff_date):
        """Check if there's a maintenance scheduled during the rental period"""
        self.ensure_one()

        # Find scheduled/in-progress maintenance that blocks rental
        maintenances = self.env['fleet.maintenance'].search([
            ('vehicle_id', '=', self.id),
            ('status', 'in', ['scheduled', 'in_progress']),
            ('blocks_rental', '=', True),
        ])

        for maintenance in maintenances:
            if not maintenance.scheduled_date:
                continue

            maint_start = maintenance.scheduled_date
            maint_end = maintenance.end_date or (maint_start + timedelta(days=1))

            # Check for overlap
            if pickup_date < maint_end and dropoff_date > maint_start:
                return True

        return False

    def get_maintenance_blocks(self, start_date, end_date):
        """Get list of maintenance blocks for calendar display"""
        self.ensure_one()

        maintenances = self.env['fleet.maintenance'].search([
            ('vehicle_id', '=', self.id),
            ('status', 'in', ['scheduled', 'in_progress']),
            ('blocks_rental', '=', True),
            ('scheduled_date', '<=', end_date),
            '|',
            ('end_date', '>=', start_date),
            ('end_date', '=', False),
        ])

        blocks = []
        for m in maintenances:
            maint_start = m.scheduled_date
            maint_end = m.end_date or (maint_start + timedelta(days=1))

            blocks.append({
                'id': m.id,
                'name': m.name,
                'type': m.maintenance_type,
                'start': maint_start.strftime('%Y-%m-%d'),
                'end': maint_end.strftime('%Y-%m-%d'),
            })

        return blocks

    def get_unavailable_dates(self, month_start, month_end):
        """Get list of unavailable dates including maintenance"""
        self.ensure_one()

        unavailable = []

        # Get booking unavailable dates
        bookings = self.env['rental.booking'].search([
            ('vehicle_id', '=', self.id),
            ('state', 'not in', ['cancelled']),
            ('pickup_date', '<=', month_end),
            ('dropoff_date', '>=', month_start),
        ])

        for booking in bookings:
            current = max(booking.pickup_date, month_start)
            end = min(booking.dropoff_date, month_end)
            while current <= end:
                date_str = current.strftime('%Y-%m-%d')
                if date_str not in unavailable:
                    unavailable.append(date_str)
                current += timedelta(days=1)

        # Get maintenance unavailable dates
        maintenances = self.env['fleet.maintenance'].search([
            ('vehicle_id', '=', self.id),
            ('status', 'in', ['scheduled', 'in_progress']),
            ('blocks_rental', '=', True),
            ('scheduled_date', '<=', month_end),
        ])

        for maintenance in maintenances:
            maint_start = maintenance.scheduled_date
            maint_end = maintenance.end_date or (maint_start + timedelta(days=1))

            current = max(maint_start, month_start)
            end = min(maint_end, month_end)

            while current <= end:
                date_str = current.strftime('%Y-%m-%d')
                if date_str not in unavailable:
                    unavailable.append(date_str)
                current += timedelta(days=1)

        return unavailable
