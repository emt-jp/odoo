# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class FleetMaintenance(models.Model):
    _name = 'fleet.maintenance'
    _description = 'Fleet Maintenance Management'
    _order = 'scheduled_date desc, name'
    
    name = fields.Char('Maintenance Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    
    # Maintenance Details
    maintenance_type = fields.Selection([
        ('routine', 'Routine Maintenance'),
        ('repair', 'Repair'),
        ('inspection', 'Inspection'),
        ('oil_change', 'Oil Change'),
        ('tire_change', 'Tire Change'),
        ('brake_service', 'Brake Service'),
        ('engine_service', 'Engine Service'),
        ('transmission_service', 'Transmission Service'),
        ('electrical', 'Electrical Service'),
        ('body_work', 'Body Work'),
        ('accident_repair', 'Accident Repair'),
        ('recall', 'Recall Service'),
        ('initial', 'Initial Setup'),
    ], string='Maintenance Type', required=True)
    
    description = fields.Text('Description', required=True)
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='medium')
    
    # Scheduling
    scheduled_date = fields.Datetime('Scheduled Date', required=True)
    service_start_date = fields.Datetime('Service Start Date', help='Planned start date when vehicle will be unavailable for booking')
    service_end_date = fields.Datetime('Service End Date', help='Planned end date when vehicle will become available again')
    actual_start_date = fields.Datetime('Actual Start Date')
    actual_end_date = fields.Datetime('Actual End Date')
    estimated_duration = fields.Float('Estimated Duration (Hours)', digits=(5, 2))
    actual_duration = fields.Float('Actual Duration (Hours)', digits=(5, 2), compute='_compute_actual_duration', store=True)

    # Periodic Service
    is_periodic = fields.Boolean('Periodic Service', default=False, help='Enable for recurring services like monthly, quarterly or annual checks')
    periodic_type = fields.Selection([
        ('monthly', 'Monthly Check'),
        ('quarterly', 'Quarterly Check'),
        ('semi_annual', 'Semi-Annual Check'),
        ('annual', 'Annual Check'),
    ], string='Periodic Type', help='Type of recurring service schedule')
    parent_service_id = fields.Many2one('fleet.maintenance', string='Parent Service', help='Reference to the original periodic service')
    child_service_ids = fields.One2many('fleet.maintenance', 'parent_service_id', string='Generated Services', help='Services generated from this periodic schedule')

    # KM-Based Service
    is_km_based = fields.Boolean('KM-Based Service', default=False, help='This service was auto-generated based on odometer reading')
    km_threshold = fields.Integer('KM Threshold', help='The odometer reading that triggered this service')
    
    # Status
    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ], string='Status', default='scheduled')
    
    @api.constrains('scheduled_date', 'actual_start_date', 'actual_end_date', 'service_start_date', 'service_end_date')
    def _check_maintenance_dates(self):
        """Validate maintenance dates"""
        for maintenance in self:
            if maintenance.actual_start_date and maintenance.scheduled_date:
                if maintenance.actual_start_date < maintenance.scheduled_date:
                    raise ValidationError(_('Actual start date cannot be before scheduled date.'))
            if maintenance.actual_end_date and maintenance.actual_start_date:
                if maintenance.actual_end_date < maintenance.actual_start_date:
                    raise ValidationError(_('Actual end date cannot be before actual start date.'))
            # Validate service dates
            if maintenance.service_start_date and maintenance.service_end_date:
                if maintenance.service_end_date < maintenance.service_start_date:
                    raise ValidationError(_('Service end date cannot be before service start date.'))

    @api.constrains('is_periodic', 'periodic_type')
    def _check_periodic_service(self):
        """Validate periodic service configuration"""
        for maintenance in self:
            if maintenance.is_periodic and not maintenance.periodic_type:
                raise ValidationError(_('Please select a periodic type for periodic service.'))
    
    @api.constrains('labor_hours', 'labor_rate')
    def _check_labor_cost(self):
        """Validate labor cost values"""
        for maintenance in self:
            if maintenance.labor_hours and maintenance.labor_hours < 0:
                raise ValidationError(_('Labor hours cannot be negative.'))
            if maintenance.labor_rate and maintenance.labor_rate < 0:
                raise ValidationError(_('Labor rate cannot be negative.'))
    
    def action_start(self):
        """Start maintenance"""
        for maintenance in self:
            if maintenance.status != 'scheduled':
                raise UserError(_("Only scheduled maintenance can be started."))
            maintenance.write({
                'status': 'in_progress',
                'actual_start_date': fields.Datetime.now()
            })
        return True
    
    def action_complete(self):
        """Complete maintenance"""
        for maintenance in self:
            if maintenance.status != 'in_progress':
                raise UserError(_("Only in-progress maintenance can be completed."))
            maintenance.write({
                'status': 'completed',
                'actual_end_date': fields.Datetime.now()
            })
        return True
    
    # Service Provider
    service_provider_id = fields.Many2one('res.partner', string='Service Provider')
    service_provider_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
        ('dealer', 'Dealer'),
        ('garage', 'Garage'),
    ], string='Service Provider Type', default='internal')
    
    # Technician
    technician_id = fields.Many2one('hr.employee', string='Technician')
    technician_notes = fields.Text('Technician Notes')
    
    # Parts & Materials
    parts_used = fields.One2many('fleet.maintenance.part', 'maintenance_id', string='Parts Used')
    total_parts_cost = fields.Monetary('Total Parts Cost', currency_field='currency_id', compute='_compute_costs', store=True)
    
    # Labor
    labor_hours = fields.Float('Labor Hours', digits=(5, 2))
    labor_rate = fields.Monetary('Labor Rate', currency_field='currency_id')
    total_labor_cost = fields.Monetary('Total Labor Cost', currency_field='currency_id', compute='_compute_costs', store=True)
    
    # Total Costs
    total_cost = fields.Monetary('Total Cost', currency_field='currency_id', compute='_compute_costs', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Mileage
    odometer_reading = fields.Integer('Odometer Reading')
    next_service_odometer = fields.Integer('Next Service Odometer')
    
    # Documentation
    work_order = fields.Binary('Work Order')
    work_order_filename = fields.Char('Work Order Filename')
    inspection_report = fields.Binary('Inspection Report')
    inspection_report_filename = fields.Char('Inspection Report Filename')
    photos = fields.Binary('Photos')
    photos_filename = fields.Char('Photos Filename')
    
    # Quality Control
    quality_check = fields.Boolean('Quality Check Required', default=False)
    quality_check_date = fields.Datetime('Quality Check Date')
    quality_check_by = fields.Many2one('hr.employee', string='Quality Check By')
    quality_notes = fields.Text('Quality Notes')
    
    # Warranty
    warranty_work = fields.Boolean('Warranty Work', default=False)
    warranty_expiry_date = fields.Date('Warranty Expiry Date')
    
    # Enterprise Features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.depends('actual_start_date', 'actual_end_date')
    def _compute_actual_duration(self):
        """Compute actual duration"""
        for maintenance in self:
            if maintenance.actual_start_date and maintenance.actual_end_date:
                duration = maintenance.actual_end_date - maintenance.actual_start_date
                maintenance.actual_duration = duration.total_seconds() / 3600  # Convert to hours
            else:
                maintenance.actual_duration = 0.0
    
    @api.depends('parts_used', 'labor_hours', 'labor_rate')
    def _compute_costs(self):
        """Compute total costs"""
        for maintenance in self:
            # Calculate parts cost
            parts_cost = sum(maintenance.parts_used.mapped('total_cost'))
            maintenance.total_parts_cost = parts_cost
            
            # Calculate labor cost
            labor_cost = maintenance.labor_hours * maintenance.labor_rate if maintenance.labor_hours and maintenance.labor_rate else 0
            maintenance.total_labor_cost = labor_cost
            
            # Calculate total cost
            maintenance.total_cost = parts_cost + labor_cost
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    @api.model
    def create(self, vals):
        """Override create to generate maintenance reference"""
        is_single = isinstance(vals, dict)
        vals_list = [vals] if is_single else list(vals)
        for v in vals_list:
            if v.get('name', _('New')) == _('New'):
                v['name'] = self.env['ir.sequence'].next_by_code('fleet.maintenance') or _('New')
        records = super().create(vals_list)
        return records[0] if is_single else records
    
    def action_start_maintenance(self):
        """Start maintenance"""
        if not self._is_enterprise_available():
            raise UserError(_("Maintenance operations require the Enterprise edition."))
        
        if self.status != 'scheduled':
            raise UserError(_("Only scheduled maintenance can be started."))
        
        self.write({
            'status': 'in_progress',
            'actual_start_date': fields.Datetime.now(),
        })
        
        # Update vehicle status
        self.vehicle_id.write({'availability_status': 'maintenance'})
        
        return True
    
    def action_complete_maintenance(self):
        """Complete maintenance"""
        if not self._is_enterprise_available():
            raise UserError(_("Maintenance operations require the Enterprise edition."))
        
        if self.status != 'in_progress':
            raise UserError(_("Only in-progress maintenance can be completed."))
        
        self.write({
            'status': 'completed',
            'actual_end_date': fields.Datetime.now(),
        })
        
        # Update vehicle status
        self.vehicle_id.write({'availability_status': 'available'})
        
        # Update vehicle service dates
        self.vehicle_id.write({
            'last_service_date': fields.Date.today(),
            'next_service_date': self._calculate_next_service_date(),
        })
        
        # Create quality check if required
        if self.quality_check:
            self._create_quality_check()
        
        return True
    
    def action_cancel_maintenance(self):
        """Cancel maintenance"""
        if not self._is_enterprise_available():
            raise UserError(_("Maintenance operations require the Enterprise edition."))
        
        if self.status in ['completed', 'cancelled']:
            raise UserError(_("Cannot cancel completed or already cancelled maintenance."))
        
        self.write({'status': 'cancelled'})
        
        # Update vehicle status if it was under maintenance
        if self.status == 'in_progress':
            self.vehicle_id.write({'availability_status': 'available'})
        
        return True
    
    def _calculate_next_service_date(self):
        """Calculate next service date"""
        if self.maintenance_type == 'routine':
            # Routine maintenance based on service interval
            if self.vehicle_id.service_interval_days:
                return fields.Date.today() + timedelta(days=self.vehicle_id.service_interval_days)
        elif self.maintenance_type == 'oil_change':
            # Oil change every 3 months
            return fields.Date.today() + relativedelta(months=3)
        
        # Default to 6 months
        return fields.Date.today() + relativedelta(months=6)
    
    def _create_quality_check(self):
        """Create quality check record"""
        self.env['fleet.quality.check'].create({
            'maintenance_id': self.id,
            'vehicle_id': self.vehicle_id.id,
            'check_date': fields.Datetime.now(),
            'checker_id': self.env.user.id,
        })
    
    @api.model
    def get_maintenance_analytics(self, start_date=None, end_date=None):
        """Get maintenance analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Maintenance analytics require the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        maintenance_records = self.search([
            ('scheduled_date', '>=', start_date),
            ('scheduled_date', '<=', end_date),
        ])
        
        total_maintenance = len(maintenance_records)
        completed_maintenance = len(maintenance_records.filtered(lambda m: m.status == 'completed'))
        total_cost = sum(maintenance_records.mapped('total_cost'))
        average_duration = sum(maintenance_records.mapped('actual_duration')) / total_maintenance if total_maintenance > 0 else 0
        
        return {
            'total_maintenance': total_maintenance,
            'completed_maintenance': completed_maintenance,
            'completion_rate': (completed_maintenance / total_maintenance * 100) if total_maintenance > 0 else 0,
            'total_cost': total_cost,
            'average_duration': average_duration,
        }
    
    @api.model
    def get_upcoming_maintenance(self, days=7):
        """Get upcoming maintenance"""
        if not self._is_enterprise_available():
            return self.env['fleet.maintenance']
        
        end_date = fields.Datetime.now() + timedelta(days=days)
        
        return self.search([
            ('status', '=', 'scheduled'),
            ('scheduled_date', '<=', end_date),
            ('scheduled_date', '>=', fields.Datetime.now()),
        ])
    
    @api.model
    def get_overdue_maintenance(self):
        """Get overdue maintenance"""
        if not self._is_enterprise_available():
            return self.env['fleet.maintenance']
        
        return self.search([
            ('status', '=', 'scheduled'),
            ('scheduled_date', '<', fields.Datetime.now()),
        ])
    
    @api.model
    def schedule_routine_maintenance(self):
        """Schedule routine maintenance for all vehicles"""
        if not self._is_enterprise_available():
            return
        
        vehicles = self.env['fleet.vehicle'].search([
            ('is_rental_vehicle', '=', True),
            ('availability_status', '!=', 'out_of_service'),
        ])
        
        for vehicle in vehicles:
            # Check if maintenance is due
            if self._is_maintenance_due(vehicle):
                self._create_routine_maintenance(vehicle)
    
    def _is_maintenance_due(self, vehicle):
        """Check if maintenance is due for vehicle"""
        if not vehicle.next_service_date:
            return True
        
        return vehicle.next_service_date <= fields.Date.today()
    
    def _create_routine_maintenance(self, vehicle):
        """Create routine maintenance for vehicle"""
        self.create({
            'vehicle_id': vehicle.id,
            'maintenance_type': 'routine',
            'description': 'Routine maintenance service',
            'scheduled_date': fields.Datetime.now() + timedelta(hours=1),
            'priority': 'medium',
            'estimated_duration': 2.0,
        })
    
    @api.model
    def get_maintenance_costs_by_type(self):
        """Get maintenance costs by type"""
        if not self._is_enterprise_available():
            return {}
        
        maintenance_records = self.search([
            ('status', '=', 'completed'),
        ])
        
        costs_by_type = {}
        for maintenance in maintenance_records:
            maintenance_type = maintenance.maintenance_type
            if maintenance_type not in costs_by_type:
                costs_by_type[maintenance_type] = 0
            costs_by_type[maintenance_type] += maintenance.total_cost
        
        return costs_by_type
    
    @api.model
    def get_vehicle_maintenance_history(self, vehicle_id):
        """Get maintenance history for vehicle"""
        if not self._is_enterprise_available():
            return []

        maintenance_records = self.search([
            ('vehicle_id', '=', vehicle_id),
        ], order='scheduled_date desc')

        return [{
            'id': record.id,
            'name': record.name,
            'maintenance_type': record.maintenance_type,
            'description': record.description,
            'scheduled_date': record.scheduled_date,
            'actual_end_date': record.actual_end_date,
            'status': record.status,
            'total_cost': record.total_cost,
            'odometer_reading': record.odometer_reading,
        } for record in maintenance_records]

    def action_generate_periodic_services(self):
        """Generate periodic service records for the next 5 years"""
        if not self._is_enterprise_available():
            raise UserError(_("Periodic service generation requires the Enterprise edition."))

        for maintenance in self:
            if not maintenance.is_periodic or not maintenance.periodic_type:
                raise UserError(_("Please enable periodic service and select a periodic type first."))

            if not maintenance.service_start_date or not maintenance.service_end_date:
                raise UserError(_("Please set service start and end dates for the periodic service."))

            # Delete existing child services that are still scheduled
            existing_scheduled = maintenance.child_service_ids.filtered(lambda s: s.status == 'scheduled')
            existing_scheduled.unlink()

            # Calculate interval based on periodic type
            if maintenance.periodic_type == 'monthly':
                interval_months = 1
                description_prefix = 'Monthly Check'
            elif maintenance.periodic_type == 'quarterly':
                interval_months = 3
                description_prefix = 'Quarterly Check'
            elif maintenance.periodic_type == 'semi_annual':
                interval_months = 6
                description_prefix = 'Semi-Annual Check'
            else:  # annual
                interval_months = 12
                description_prefix = 'Annual Check'

            # Calculate service duration
            service_duration = maintenance.service_end_date - maintenance.service_start_date

            # Generate services for next 5 years
            current_date = maintenance.service_start_date
            end_date_limit = maintenance.service_start_date + relativedelta(years=5)
            service_count = 0

            while current_date < end_date_limit:
                # Skip the first occurrence (the parent itself)
                if service_count > 0:
                    service_end = current_date + service_duration
                    self.create({
                        'vehicle_id': maintenance.vehicle_id.id,
                        'maintenance_type': maintenance.maintenance_type,
                        'description': f'{description_prefix} - {maintenance.vehicle_id.name}',
                        'priority': maintenance.priority,
                        'scheduled_date': current_date,
                        'service_start_date': current_date,
                        'service_end_date': service_end,
                        'estimated_duration': maintenance.estimated_duration,
                        'service_provider_id': maintenance.service_provider_id.id if maintenance.service_provider_id else False,
                        'service_provider_type': maintenance.service_provider_type,
                        'is_periodic': False,  # Child services are not periodic themselves
                        'parent_service_id': maintenance.id,
                        'status': 'scheduled',
                    })
                service_count += 1
                current_date = current_date + relativedelta(months=interval_months)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Periodic Services Generated'),
                'message': _('Successfully generated periodic service entries for the next 5 years.'),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def get_vehicle_service_periods(self, vehicle_id, start_date, end_date):
        """Get all service periods for a vehicle within a date range (used for booking availability)"""
        domain = [
            ('vehicle_id', '=', vehicle_id),
            ('status', 'in', ['scheduled', 'in_progress']),
            ('service_start_date', '!=', False),
            ('service_end_date', '!=', False),
            '|',
            '&', ('service_start_date', '<=', start_date), ('service_end_date', '>=', start_date),
            '&', ('service_start_date', '<=', end_date), ('service_end_date', '>=', end_date),
        ]
        return self.search(domain)

    def is_vehicle_available_for_booking(self, vehicle_id, pickup_date, return_date):
        """Check if vehicle is available for booking (not under scheduled service)"""
        conflicting_services = self.search([
            ('vehicle_id', '=', vehicle_id),
            ('status', 'in', ['scheduled', 'in_progress']),
            ('service_start_date', '!=', False),
            ('service_end_date', '!=', False),
            '|',
            '&', ('service_start_date', '<=', pickup_date), ('service_end_date', '>=', pickup_date),
            '&', ('service_start_date', '<=', return_date), ('service_end_date', '>=', return_date),
        ])
        return len(conflicting_services) == 0

    @api.model
    def _cron_generate_km_based_services(self):
        """Cron job to automatically generate km-based service checks.
        Runs daily to check all vehicles and create 5000km interval services.
        Service is scheduled 1 week after threshold is crossed, with 2-day duration.
        """
        _logger.info("Running KM-based service generation cron job")

        # Get all rental vehicles with km service enabled
        vehicles = self.env['fleet.vehicle'].search([
            ('is_rental_vehicle', '=', True),
            ('km_service_enabled', '=', True),
        ])

        for vehicle in vehicles:
            self._check_and_create_km_service(vehicle)

        return True

    def _check_and_create_km_service(self, vehicle):
        """Check if vehicle needs a km-based service and create it if needed"""
        if not vehicle.odometer or vehicle.odometer <= 0:
            return

        km_interval = vehicle.km_service_interval or 5000
        current_odometer = vehicle.odometer

        # Calculate the next km threshold
        last_serviced_km = vehicle.last_km_service_odometer or 0
        next_threshold = ((last_serviced_km // km_interval) + 1) * km_interval

        # Check if current odometer has crossed the threshold
        if current_odometer >= next_threshold:
            # Check if service already exists for this threshold
            existing_service = self.search([
                ('vehicle_id', '=', vehicle.id),
                ('is_km_based', '=', True),
                ('km_threshold', '=', next_threshold),
                ('status', '!=', 'cancelled'),
            ], limit=1)

            if not existing_service:
                # Create new km-based service scheduled 1 week from now
                service_duration_days = vehicle.km_service_duration_days or 2
                service_start = fields.Datetime.now() + timedelta(days=7)
                service_end = service_start + timedelta(days=service_duration_days)

                self.create({
                    'vehicle_id': vehicle.id,
                    'maintenance_type': 'routine',
                    'description': f'5000 KM Service Check - Odometer reached {next_threshold} km',
                    'priority': 'medium',
                    'scheduled_date': service_start,
                    'service_start_date': service_start,
                    'service_end_date': service_end,
                    'estimated_duration': service_duration_days * 8,  # 8 hours per day
                    'is_km_based': True,
                    'km_threshold': next_threshold,
                    'odometer_reading': current_odometer,
                    'status': 'scheduled',
                })

                # Update vehicle's last km service odometer
                vehicle.write({'last_km_service_odometer': next_threshold})

                _logger.info(f"Created KM-based service for vehicle {vehicle.name} at {next_threshold} km")


class FleetMaintenancePart(models.Model):
    _name = 'fleet.maintenance.part'
    _description = 'Fleet Maintenance Parts'

    part_name = fields.Char('Part Name', required=True)
    part_number = fields.Char('Part Number')
    maintenance_id = fields.Many2one('fleet.maintenance', string='Maintenance', required=True, ondelete='cascade')
    part_id = fields.Many2one('product.product', string='Part')
    quantity = fields.Float('Quantity', required=True, default=1.0)
    unit_cost = fields.Monetary('Unit Cost', currency_field='currency_id', required=True)
    unit_price = fields.Monetary('Unit Price', currency_field='currency_id', related='unit_cost')
    total_cost = fields.Monetary('Total Cost', currency_field='currency_id', compute='_compute_total_cost', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='maintenance_id.currency_id')
    
    # Enterprise features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.depends('quantity', 'unit_cost')
    def _compute_total_cost(self):
        """Compute total cost"""
        for part in self:
            part.total_cost = part.quantity * part.unit_cost
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled


class FleetQualityCheck(models.Model):
    _name = 'fleet.quality.check'
    _description = 'Fleet Quality Check'
    
    maintenance_id = fields.Many2one('fleet.maintenance', string='Maintenance', required=True, ondelete='cascade')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    check_date = fields.Datetime('Check Date', required=True, default=fields.Datetime.now)
    checker_id = fields.Many2one('hr.employee', string='Checker', required=True)
    
    # Quality Check Items
    check_items = fields.One2many('fleet.quality.check.item', 'check_id', string='Check Items')
    
    # Overall Results
    overall_score = fields.Float('Overall Score', digits=(5, 2), compute='_compute_overall_score', store=True)
    passed = fields.Boolean('Passed', compute='_compute_passed', store=True)
    
    # Notes
    notes = fields.Text('Notes')
    recommendations = fields.Text('Recommendations')
    
    # Enterprise features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.depends('check_items')
    def _compute_overall_score(self):
        """Compute overall quality score"""
        for check in self:
            if check.check_items:
                total_score = sum(check.check_items.mapped('score'))
                max_score = sum(check.check_items.mapped('max_score'))
                check.overall_score = (total_score / max_score * 100) if max_score > 0 else 0
            else:
                check.overall_score = 0
    
    @api.depends('overall_score')
    def _compute_passed(self):
        """Compute if quality check passed"""
        for check in self:
            check.passed = check.overall_score >= 80.0  # 80% threshold
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled


class FleetQualityCheckItem(models.Model):
    _name = 'fleet.quality.check.item'
    _description = 'Fleet Quality Check Item'
    
    check_id = fields.Many2one('fleet.quality.check', string='Quality Check', required=True, ondelete='cascade')
    item_name = fields.Char('Item Name', required=True)
    description = fields.Text('Description')
    score = fields.Float('Score', required=True, default=0.0)
    max_score = fields.Float('Max Score', required=True, default=10.0)
    notes = fields.Text('Notes')
    
    # Enterprise features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled




