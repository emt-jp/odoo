# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class FleetAnalytics(models.Model):
    _name = 'fleet.analytics'
    _description = 'Fleet Analytics & Reporting'
    
    # Analytics Configuration
    name = fields.Char('Analytics Name', required=True)
    report_type = fields.Selection([
        ('fleet_overview', 'Fleet Overview'),
        ('vehicle_performance', 'Vehicle Performance'),
        ('rental_analytics', 'Rental Analytics'),
        ('maintenance_analytics', 'Maintenance Analytics'),
        ('fuel_analytics', 'Fuel Analytics'),
        ('driver_analytics', 'Driver Analytics'),
        ('financial_analytics', 'Financial Analytics'),
        ('custom', 'Custom Report'),
    ], string='Report Type', required=True)
    
    # Date Range
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    
    # Filters
    vehicle_ids = fields.Many2many('fleet.vehicle', string='Vehicles')
    driver_ids = fields.Many2many('fleet.driver', string='Drivers')
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
    
    # Report Data
    report_data = fields.Text('Report Data', help='JSON data of the report')
    chart_config = fields.Text('Chart Configuration', help='JSON configuration for charts')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('scheduled', 'Scheduled'),
    ], string='Status', default='draft')
    
    # Enterprise Features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)

    # Dashboard KPI Fields (computed)
    total_vehicles = fields.Integer('Total Vehicles', compute='_compute_dashboard_kpis', store=False)
    available_vehicles = fields.Integer('Available', compute='_compute_dashboard_kpis', store=False)
    rented_vehicles = fields.Integer('Rented', compute='_compute_dashboard_kpis', store=False)
    maintenance_vehicles = fields.Integer('In Maintenance', compute='_compute_dashboard_kpis', store=False)
    utilization_rate = fields.Float('Utilization %', compute='_compute_dashboard_kpis', store=False)

    total_rentals_count = fields.Integer('Total Rentals', compute='_compute_dashboard_kpis', store=False)
    completed_rentals_count = fields.Integer('Completed', compute='_compute_dashboard_kpis', store=False)
    in_progress_rentals_count = fields.Integer('In Progress', compute='_compute_dashboard_kpis', store=False)
    total_revenue = fields.Float('Total Revenue', compute='_compute_dashboard_kpis', store=False)

    pending_maintenance_count = fields.Integer('Pending Maintenance', compute='_compute_dashboard_kpis', store=False)
    overdue_maintenance_count = fields.Integer('Overdue', compute='_compute_dashboard_kpis', store=False)
    total_maintenance_cost = fields.Float('Maintenance Cost', compute='_compute_dashboard_kpis', store=False)

    expiring_documents_count = fields.Integer('Expiring Soon', compute='_compute_dashboard_kpis', store=False)
    expired_documents_count = fields.Integer('Expired', compute='_compute_dashboard_kpis', store=False)

    pending_bookings_count = fields.Integer('Pending Bookings', compute='_compute_dashboard_kpis', store=False)
    confirmed_bookings_count = fields.Integer('Confirmed', compute='_compute_dashboard_kpis', store=False)

    @api.depends()
    def _compute_dashboard_kpis(self):
        """Compute dashboard KPIs"""
        for record in self:
            # Fleet metrics
            vehicles = self.env['fleet.vehicle'].search([('is_rental_vehicle', '=', True)])
            record.total_vehicles = len(vehicles)
            record.available_vehicles = len(vehicles.filtered(lambda v: v.availability_status == 'available'))
            record.rented_vehicles = len(vehicles.filtered(lambda v: v.availability_status == 'rented'))
            record.maintenance_vehicles = len(vehicles.filtered(lambda v: v.availability_status == 'maintenance'))
            record.utilization_rate = (record.rented_vehicles / record.total_vehicles * 100) if record.total_vehicles > 0 else 0

            # Rental metrics
            rentals = self.env['fleet.rental'].search([])
            record.total_rentals_count = len(rentals)
            record.completed_rentals_count = len(rentals.filtered(lambda r: r.state == 'completed'))
            record.in_progress_rentals_count = len(rentals.filtered(lambda r: r.state == 'in_progress'))
            record.total_revenue = sum(rentals.mapped('total_amount'))

            # Maintenance metrics
            maintenance = self.env['fleet.maintenance'].search([('status', 'in', ['pending', 'scheduled'])])
            record.pending_maintenance_count = len(maintenance)
            overdue = maintenance.filtered(lambda m: m.scheduled_date and m.scheduled_date < fields.Date.today())
            record.overdue_maintenance_count = len(overdue)
            all_maintenance = self.env['fleet.maintenance'].search([])
            record.total_maintenance_cost = sum(all_maintenance.mapped('total_cost'))

            # Document metrics
            documents = self.env['fleet.vehicle.document'].search([])
            record.expiring_documents_count = len(documents.filtered(lambda d: 0 < d.days_to_expiry <= 30))
            record.expired_documents_count = len(documents.filtered(lambda d: d.is_expired))

            # Booking metrics
            bookings = self.env['fleet.booking'].search([('state', 'in', ['draft', 'confirmed'])])
            record.pending_bookings_count = len(bookings.filtered(lambda b: b.state == 'draft'))
            record.confirmed_bookings_count = len(bookings.filtered(lambda b: b.state == 'confirmed'))

    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    @api.model
    def generate_fleet_overview(self, start_date=None, end_date=None):
        """Generate fleet overview analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Fleet analytics require the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        # Get fleet data
        vehicles = self.env['fleet.vehicle'].search([('is_rental_vehicle', '=', True)])
        rentals = self.env['fleet.rental'].search([
            ('start_date', '>=', start_date),
            ('start_date', '<=', end_date),
        ])
        maintenance_records = self.env['fleet.maintenance'].search([
            ('scheduled_date', '>=', start_date),
            ('scheduled_date', '<=', end_date),
        ])
        fuel_records = self.env['fleet.fuel.management'].search([
            ('refuel_date', '>=', start_date),
            ('refuel_date', '<=', end_date),
        ])
        
        # Calculate metrics
        total_vehicles = len(vehicles)
        available_vehicles = len(vehicles.filtered(lambda v: v.availability_status == 'available'))
        rented_vehicles = len(vehicles.filtered(lambda v: v.availability_status == 'rented'))
        maintenance_vehicles = len(vehicles.filtered(lambda v: v.availability_status == 'maintenance'))
        
        total_rentals = len(rentals)
        completed_rentals = len(rentals.filtered(lambda r: r.state == 'completed'))
        total_revenue = sum(rentals.mapped('total_amount'))
        
        total_maintenance_cost = sum(maintenance_records.mapped('total_cost'))
        total_fuel_cost = sum(fuel_records.mapped('total_cost'))
        
        # Calculate utilization rate
        utilization_rate = (rented_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0
        
        # Calculate average rating
        ratings = rentals.mapped('customer_rating')
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        return {
            'fleet_metrics': {
                'total_vehicles': total_vehicles,
                'available_vehicles': available_vehicles,
                'rented_vehicles': rented_vehicles,
                'maintenance_vehicles': maintenance_vehicles,
                'utilization_rate': utilization_rate,
            },
            'rental_metrics': {
                'total_rentals': total_rentals,
                'completed_rentals': completed_rentals,
                'completion_rate': (completed_rentals / total_rentals * 100) if total_rentals > 0 else 0,
                'total_revenue': total_revenue,
                'avg_rating': avg_rating,
            },
            'cost_metrics': {
                'total_maintenance_cost': total_maintenance_cost,
                'total_fuel_cost': total_fuel_cost,
                'total_operating_cost': total_maintenance_cost + total_fuel_cost,
            },
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
        }
    
    @api.model
    def generate_vehicle_performance(self, vehicle_id, start_date=None, end_date=None):
        """Generate vehicle performance analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Vehicle performance analytics require the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        vehicle = self.env['fleet.vehicle'].browse(vehicle_id)
        if not vehicle.exists():
            raise UserError(_("Vehicle not found."))
        
        # Get vehicle data
        rentals = self.env['fleet.rental'].search([
            ('vehicle_id', '=', vehicle_id),
            ('start_date', '>=', start_date),
            ('start_date', '<=', end_date),
        ])
        maintenance_records = self.env['fleet.maintenance'].search([
            ('vehicle_id', '=', vehicle_id),
            ('scheduled_date', '>=', start_date),
            ('scheduled_date', '<=', end_date),
        ])
        fuel_records = self.env['fleet.fuel.management'].search([
            ('vehicle_id', '=', vehicle_id),
            ('refuel_date', '>=', start_date),
            ('refuel_date', '<=', end_date),
        ])
        
        # Calculate performance metrics
        total_rentals = len(rentals)
        total_revenue = sum(rentals.mapped('total_amount'))
        avg_rating = sum(rentals.mapped('customer_rating')) / total_rentals if total_rentals > 0 else 0
        
        total_maintenance_cost = sum(maintenance_records.mapped('total_cost'))
        total_fuel_cost = sum(fuel_records.mapped('total_cost'))
        
        # Calculate utilization
        rental_days = sum(rentals.mapped('rental_duration'))
        total_days = (end_date - start_date).days
        utilization_rate = (rental_days / total_days * 100) if total_days > 0 else 0
        
        # Calculate fuel efficiency
        avg_fuel_efficiency = 0
        if fuel_records:
            efficiencies = fuel_records.mapped('fuel_efficiency')
            avg_fuel_efficiency = sum(efficiencies) / len(efficiencies)
        
        return {
            'vehicle_info': {
                'id': vehicle.id,
                'name': vehicle.name,
                'type': vehicle.vehicle_type,
                'category': vehicle.rental_category,
            },
            'performance_metrics': {
                'total_rentals': total_rentals,
                'total_revenue': total_revenue,
                'avg_rating': avg_rating,
                'utilization_rate': utilization_rate,
                'avg_fuel_efficiency': avg_fuel_efficiency,
            },
            'cost_metrics': {
                'total_maintenance_cost': total_maintenance_cost,
                'total_fuel_cost': total_fuel_cost,
                'total_operating_cost': total_maintenance_cost + total_fuel_cost,
                'net_profit': total_revenue - (total_maintenance_cost + total_fuel_cost),
            },
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
        }
    
    @api.model
    def generate_rental_analytics(self, start_date=None, end_date=None):
        """Generate rental analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Rental analytics require the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        rentals = self.env['fleet.rental'].search([
            ('start_date', '>=', start_date),
            ('start_date', '<=', end_date),
        ])
        
        # Calculate rental metrics
        total_rentals = len(rentals)
        completed_rentals = len(rentals.filtered(lambda r: r.state == 'completed'))
        cancelled_rentals = len(rentals.filtered(lambda r: r.state == 'cancelled'))
        
        total_revenue = sum(rentals.mapped('total_amount'))
        avg_rental_duration = sum(rentals.mapped('rental_duration')) / total_rentals if total_rentals > 0 else 0
        
        # Calculate by vehicle category
        category_analytics = {}
        for rental in rentals:
            category = rental.vehicle_id.rental_category
            if category not in category_analytics:
                category_analytics[category] = {
                    'count': 0,
                    'revenue': 0,
                    'avg_duration': 0,
                }
            
            category_analytics[category]['count'] += 1
            category_analytics[category]['revenue'] += rental.total_amount
        
        # Calculate average duration by category
        for category in category_analytics:
            category_rentals = rentals.filtered(lambda r: r.vehicle_id.rental_category == category)
            if category_rentals:
                category_analytics[category]['avg_duration'] = sum(category_rentals.mapped('rental_duration')) / len(category_rentals)
        
        return {
            'rental_metrics': {
                'total_rentals': total_rentals,
                'completed_rentals': completed_rentals,
                'cancelled_rentals': cancelled_rentals,
                'completion_rate': (completed_rentals / total_rentals * 100) if total_rentals > 0 else 0,
                'cancellation_rate': (cancelled_rentals / total_rentals * 100) if total_rentals > 0 else 0,
                'total_revenue': total_revenue,
                'avg_rental_duration': avg_rental_duration,
            },
            'category_analytics': category_analytics,
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
        }
    
    @api.model
    def generate_maintenance_analytics(self, start_date=None, end_date=None):
        """Generate maintenance analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Maintenance analytics require the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        maintenance_records = self.env['fleet.maintenance'].search([
            ('scheduled_date', '>=', start_date),
            ('scheduled_date', '<=', end_date),
        ])
        
        # Calculate maintenance metrics
        total_maintenance = len(maintenance_records)
        completed_maintenance = len(maintenance_records.filtered(lambda m: m.status == 'completed'))
        total_cost = sum(maintenance_records.mapped('total_cost'))
        
        # Calculate by maintenance type
        type_analytics = {}
        for maintenance in maintenance_records:
            maintenance_type = maintenance.maintenance_type
            if maintenance_type not in type_analytics:
                type_analytics[maintenance_type] = {
                    'count': 0,
                    'total_cost': 0,
                    'avg_duration': 0,
                }
            
            type_analytics[maintenance_type]['count'] += 1
            type_analytics[maintenance_type]['total_cost'] += maintenance.total_cost
        
        # Calculate average duration by type
        for maintenance_type in type_analytics:
            type_records = maintenance_records.filtered(lambda m: m.maintenance_type == maintenance_type)
            if type_records:
                durations = type_records.mapped('actual_duration')
                if durations:
                    type_analytics[maintenance_type]['avg_duration'] = sum(durations) / len(durations)
        
        return {
            'maintenance_metrics': {
                'total_maintenance': total_maintenance,
                'completed_maintenance': completed_maintenance,
                'completion_rate': (completed_maintenance / total_maintenance * 100) if total_maintenance > 0 else 0,
                'total_cost': total_cost,
                'avg_cost_per_maintenance': total_cost / total_maintenance if total_maintenance > 0 else 0,
            },
            'type_analytics': type_analytics,
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
        }
    
    @api.model
    def generate_fuel_analytics(self, start_date=None, end_date=None):
        """Generate fuel analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Fuel analytics require the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        fuel_records = self.env['fleet.fuel.management'].search([
            ('refuel_date', '>=', start_date),
            ('refuel_date', '<=', end_date),
        ])
        
        # Calculate fuel metrics
        total_fuel = sum(fuel_records.mapped('fuel_quantity'))
        total_cost = sum(fuel_records.mapped('total_cost'))
        total_distance = sum(fuel_records.mapped('distance_traveled'))
        
        # Calculate average efficiency
        efficiencies = fuel_records.mapped('fuel_efficiency')
        avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0
        
        # Calculate by fuel type
        fuel_type_analytics = {}
        for record in fuel_records:
            fuel_type = record.fuel_type
            if fuel_type not in fuel_type_analytics:
                fuel_type_analytics[fuel_type] = {
                    'quantity': 0,
                    'cost': 0,
                    'records_count': 0,
                }
            
            fuel_type_analytics[fuel_type]['quantity'] += record.fuel_quantity
            fuel_type_analytics[fuel_type]['cost'] += record.total_cost
            fuel_type_analytics[fuel_type]['records_count'] += 1
        
        return {
            'fuel_metrics': {
                'total_fuel': total_fuel,
                'total_cost': total_cost,
                'total_distance': total_distance,
                'avg_efficiency': avg_efficiency,
                'cost_per_km': total_cost / total_distance if total_distance > 0 else 0,
            },
            'fuel_type_analytics': fuel_type_analytics,
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
        }
    
    @api.model
    def generate_driver_analytics(self, start_date=None, end_date=None):
        """Generate driver analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Driver analytics require the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        drivers = self.env['fleet.driver'].search([('is_active', '=', True)])
        
        driver_analytics = []
        for driver in drivers:
            # Get driver's rentals
            rentals = self.env['fleet.rental'].search([
                ('driver_id', '=', driver.id),
                ('start_date', '>=', start_date),
                ('start_date', '<=', end_date),
            ])
            
            if rentals:
                total_rentals = len(rentals)
                total_revenue = sum(rentals.mapped('total_amount'))
                avg_rating = sum(rentals.mapped('customer_rating')) / total_rentals if total_rentals > 0 else 0
                
                driver_analytics.append({
                    'driver_id': driver.id,
                    'driver_name': driver.name,
                    'total_rentals': total_rentals,
                    'total_revenue': total_revenue,
                    'avg_rating': avg_rating,
                })
        
        # Sort by revenue
        driver_analytics.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        return {
            'driver_analytics': driver_analytics,
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
        }
    
    @api.model
    def generate_financial_analytics(self, start_date=None, end_date=None):
        """Generate financial analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Financial analytics require the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        # Get financial data
        rentals = self.env['fleet.rental'].search([
            ('start_date', '>=', start_date),
            ('start_date', '<=', end_date),
        ])
        maintenance_records = self.env['fleet.maintenance'].search([
            ('scheduled_date', '>=', start_date),
            ('scheduled_date', '<=', end_date),
        ])
        fuel_records = self.env['fleet.fuel.management'].search([
            ('refuel_date', '>=', start_date),
            ('refuel_date', '<=', end_date),
        ])
        
        # Calculate financial metrics
        total_revenue = sum(rentals.mapped('total_amount'))
        total_maintenance_cost = sum(maintenance_records.mapped('total_cost'))
        total_fuel_cost = sum(fuel_records.mapped('total_cost'))
        total_operating_cost = total_maintenance_cost + total_fuel_cost
        
        net_profit = total_revenue - total_operating_cost
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        # Calculate daily revenue trend
        daily_revenue = {}
        for rental in rentals:
            date = rental.start_date.date()
            if date not in daily_revenue:
                daily_revenue[date] = 0
            daily_revenue[date] += rental.total_amount
        
        # Calculate monthly revenue trend
        monthly_revenue = {}
        for rental in rentals:
            month = rental.start_date.strftime('%Y-%m')
            if month not in monthly_revenue:
                monthly_revenue[month] = 0
            monthly_revenue[month] += rental.total_amount
        
        return {
            'financial_metrics': {
                'total_revenue': total_revenue,
                'total_operating_cost': total_operating_cost,
                'maintenance_cost': total_maintenance_cost,
                'fuel_cost': total_fuel_cost,
                'net_profit': net_profit,
                'profit_margin': profit_margin,
            },
            'revenue_trends': {
                'daily': daily_revenue,
                'monthly': monthly_revenue,
            },
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
        }
    
    @api.model
    def get_dashboard_data(self):
        """Get dashboard data for fleet management"""
        if not self._is_enterprise_available():
            raise UserError(_("Dashboard data requires the Enterprise edition."))
        
        # Get current date range
        end_date = fields.Date.today()
        start_date = end_date - timedelta(days=30)
        
        # Generate all analytics
        fleet_overview = self.generate_fleet_overview(start_date, end_date)
        rental_analytics = self.generate_rental_analytics(start_date, end_date)
        maintenance_analytics = self.generate_maintenance_analytics(start_date, end_date)
        fuel_analytics = self.generate_fuel_analytics(start_date, end_date)
        financial_analytics = self.generate_financial_analytics(start_date, end_date)
        
        return {
            'fleet_overview': fleet_overview,
            'rental_analytics': rental_analytics,
            'maintenance_analytics': maintenance_analytics,
            'fuel_analytics': fuel_analytics,
            'financial_analytics': financial_analytics,
            'last_updated': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    
    @api.model
    def schedule_analytics_report(self, report_type, start_date, end_date, email_recipients=None):
        """Schedule analytics report"""
        if not self._is_enterprise_available():
            raise UserError(_("Scheduled reports require the Enterprise edition."))
        
        # Create scheduled report record
        scheduled_report = self.env['fleet.scheduled.report'].create({
            'name': f'{report_type.title()} Report - {start_date} to {end_date}',
            'report_type': report_type,
            'start_date': start_date,
            'end_date': end_date,
            'email_recipients': email_recipients or [],
            'state': 'scheduled',
        })
        
        return scheduled_report
    
    @api.model
    def generate_custom_report(self, report_config):
        """Generate custom report based on configuration"""
        if not self._is_enterprise_available():
            raise UserError(_("Custom reports require the Enterprise edition."))
        
        # This would implement custom report generation based on configuration
        # For now, return a basic structure
        return {
            'report_type': 'custom',
            'config': report_config,
            'data': {},
            'generated_at': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }




