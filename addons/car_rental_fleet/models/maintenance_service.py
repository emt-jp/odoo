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
    actual_start_date = fields.Datetime('Actual Start Date')
    actual_end_date = fields.Datetime('Actual End Date')
    estimated_duration = fields.Float('Estimated Duration (Hours)', digits=(5, 2))
    actual_duration = fields.Float('Actual Duration (Hours)', digits=(5, 2), compute='_compute_actual_duration', store=True)
    
    # Status
    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ], string='Status', default='scheduled')
    
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
        return self.env.context.get('is_enterprise', True)
    
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


class FleetMaintenancePart(models.Model):
    _name = 'fleet.maintenance.part'
    _description = 'Fleet Maintenance Parts'
    
    maintenance_id = fields.Many2one('fleet.maintenance', string='Maintenance', required=True, ondelete='cascade')
    part_id = fields.Many2one('product.product', string='Part', required=True)
    quantity = fields.Float('Quantity', required=True, default=1.0)
    unit_price = fields.Monetary('Unit Price', currency_field='currency_id', required=True)
    total_cost = fields.Monetary('Total Cost', currency_field='currency_id', compute='_compute_total_cost', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='maintenance_id.currency_id')
    
    # Enterprise features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.depends('quantity', 'unit_price')
    def _compute_total_cost(self):
        """Compute total cost"""
        for part in self:
            part.total_cost = part.quantity * part.unit_price
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return self.env.context.get('is_enterprise', True)


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
        return self.env.context.get('is_enterprise', True)


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
        return self.env.context.get('is_enterprise', True)




