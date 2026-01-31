# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class FleetFuelManagement(models.Model):
    _name = 'fleet.fuel.management'
    _description = 'Fleet Fuel Management'
    _order = 'refuel_date desc'

    name = fields.Char('Reference', required=True, copy=False, default='New')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    fuel_date = fields.Datetime('Fuel Date', related='refuel_date', store=True)
    refuel_date = fields.Datetime('Refuel Date', required=True, default=fields.Datetime.now)
    
    # Fuel Details
    fuel_type = fields.Selection([
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('hybrid', 'Hybrid'),
        ('electric', 'Electric'),
        ('lpg', 'LPG'),
        ('cng', 'CNG'),
    ], string='Fuel Type', required=True)
    
    fuel_quantity = fields.Float('Fuel Quantity', digits=(10, 3), required=True)
    quantity = fields.Float('Quantity', related='fuel_quantity', store=True)
    fuel_unit = fields.Selection([
        ('liters', 'Liters'),
        ('gallons', 'Gallons'),
        ('kwh', 'kWh (Electric)'),
    ], string='Fuel Unit', required=True, default='liters')

    # Cost Information
    unit_price = fields.Monetary('Unit Price', currency_field='currency_id', required=True)
    total_cost = fields.Monetary('Total Cost', currency_field='currency_id', compute='_compute_total_cost', store=True)
    cost = fields.Monetary('Cost', related='total_cost', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Location
    refuel_location = fields.Char('Refuel Location')
    location = fields.Char('Location', related='refuel_location', store=True)
    station_name = fields.Char('Station Name')
    fuel_station = fields.Char('Fuel Station', related='station_name', store=True)
    station_address = fields.Text('Station Address')
    
    # Odometer
    odometer_reading = fields.Integer('Odometer Reading', required=True)
    previous_odometer = fields.Integer('Previous Odometer Reading', compute='_compute_previous_odometer', store=True)
    distance_traveled = fields.Integer('Distance Traveled', compute='_compute_distance_traveled', store=True)
    
    # Fuel Efficiency
    fuel_efficiency = fields.Float('Fuel Efficiency (L/100km)', digits=(10, 2), compute='_compute_fuel_efficiency', store=True)
    
    # Driver Information
    driver_id = fields.Many2one('fleet.driver', string='Driver')
    driver_name = fields.Char('Driver Name')
    fuel_card_id = fields.Many2one('fleet.fuel.card', string='Fuel Card', ondelete='set null')
    
    # Receipt
    receipt_number = fields.Char('Receipt Number')
    receipt_image = fields.Binary('Receipt Image')
    receipt_filename = fields.Char('Receipt Filename')
    
    # Notes
    notes = fields.Text('Notes')
    
    # Enterprise Features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.depends('fuel_quantity', 'unit_price')
    def _compute_total_cost(self):
        """Compute total cost"""
        for record in self:
            record.total_cost = record.fuel_quantity * record.unit_price
    
    @api.depends('vehicle_id', 'refuel_date')
    def _compute_previous_odometer(self):
        """Compute previous odometer reading"""
        for record in self:
            if record.vehicle_id and record.refuel_date:
                previous_record = self.search([
                    ('vehicle_id', '=', record.vehicle_id.id),
                    ('refuel_date', '<', record.refuel_date),
                ], order='refuel_date desc', limit=1)
                
                record.previous_odometer = previous_record.odometer_reading if previous_record else 0
            else:
                record.previous_odometer = 0
    
    @api.depends('odometer_reading', 'previous_odometer')
    def _compute_distance_traveled(self):
        """Compute distance traveled"""
        for record in self:
            record.distance_traveled = max(0, record.odometer_reading - record.previous_odometer)
    
    @api.depends('fuel_quantity', 'distance_traveled')
    def _compute_fuel_efficiency(self):
        """Compute fuel efficiency"""
        for record in self:
            if record.distance_traveled > 0 and record.fuel_quantity > 0:
                # Convert to liters if needed
                fuel_liters = record.fuel_quantity
                if record.fuel_unit == 'gallons':
                    fuel_liters = fuel_liters * 3.78541  # Convert gallons to liters
                
                # Calculate efficiency in L/100km
                record.fuel_efficiency = (fuel_liters / record.distance_traveled) * 100
            else:
                record.fuel_efficiency = 0.0
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    @api.model
    def create_fuel_record(self, vehicle_id, fuel_data):
        """Create fuel record"""
        if not self._is_enterprise_available():
            raise UserError(_("Fuel management requires the Enterprise edition."))
        
        # Validate required fields
        required_fields = ['fuel_type', 'fuel_quantity', 'unit_price', 'odometer_reading']
        for field in required_fields:
            if field not in fuel_data or not fuel_data[field]:
                raise UserError(_(f"Field {field} is required."))
        
        # Set vehicle fuel type if not set
        vehicle = self.env['fleet.vehicle'].browse(vehicle_id)
        if not vehicle.engine_type:
            vehicle.write({'engine_type': fuel_data['fuel_type']})
        
        fuel_data['vehicle_id'] = vehicle_id
        return self.create(fuel_data)
    
    @api.model
    def get_fuel_analytics(self, vehicle_id=None, start_date=None, end_date=None):
        """Get fuel analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Fuel analytics require the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        domain = [
            ('refuel_date', '>=', start_date),
            ('refuel_date', '<=', end_date),
        ]
        
        if vehicle_id:
            domain.append(('vehicle_id', '=', vehicle_id))
        
        fuel_records = self.search(domain)
        
        if not fuel_records:
            return {}
        
        total_fuel = sum(fuel_records.mapped('fuel_quantity'))
        total_cost = sum(fuel_records.mapped('total_cost'))
        total_distance = sum(fuel_records.mapped('distance_traveled'))
        
        # Calculate average efficiency
        efficiencies = fuel_records.mapped('fuel_efficiency')
        avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0
        
        # Calculate cost per kilometer
        cost_per_km = total_cost / total_distance if total_distance > 0 else 0
        
        return {
            'total_fuel': total_fuel,
            'total_cost': total_cost,
            'total_distance': total_distance,
            'avg_efficiency': avg_efficiency,
            'cost_per_km': cost_per_km,
            'fuel_records_count': len(fuel_records),
        }
    
    @api.model
    def get_vehicle_fuel_efficiency(self, vehicle_id):
        """Get vehicle fuel efficiency over time"""
        if not self._is_enterprise_available():
            raise UserError(_("Fuel efficiency tracking requires the Enterprise edition."))
        
        fuel_records = self.search([
            ('vehicle_id', '=', vehicle_id),
            ('fuel_efficiency', '>', 0),
        ], order='refuel_date asc')
        
        efficiency_data = []
        for record in fuel_records:
            efficiency_data.append({
                'date': record.refuel_date.strftime('%Y-%m-%d'),
                'efficiency': record.fuel_efficiency,
                'distance': record.distance_traveled,
                'fuel_quantity': record.fuel_quantity,
            })
        
        return efficiency_data
    
    @api.model
    def get_fuel_cost_analysis(self, vehicle_id=None, start_date=None, end_date=None):
        """Get fuel cost analysis"""
        if not self._is_enterprise_available():
            raise UserError(_("Fuel cost analysis requires the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        domain = [
            ('refuel_date', '>=', start_date),
            ('refuel_date', '<=', end_date),
        ]
        
        if vehicle_id:
            domain.append(('vehicle_id', '=', vehicle_id))
        
        fuel_records = self.search(domain)
        
        # Group by fuel type
        cost_by_type = {}
        for record in fuel_records:
            fuel_type = record.fuel_type
            if fuel_type not in cost_by_type:
                cost_by_type[fuel_type] = {
                    'total_cost': 0,
                    'total_quantity': 0,
                    'avg_price': 0,
                    'records_count': 0,
                }
            
            cost_by_type[fuel_type]['total_cost'] += record.total_cost
            cost_by_type[fuel_type]['total_quantity'] += record.fuel_quantity
            cost_by_type[fuel_type]['records_count'] += 1
        
        # Calculate average prices
        for fuel_type in cost_by_type:
            data = cost_by_type[fuel_type]
            if data['total_quantity'] > 0:
                data['avg_price'] = data['total_cost'] / data['total_quantity']
        
        return cost_by_type
    
    @api.model
    def get_fuel_consumption_trend(self, vehicle_id, days=30):
        """Get fuel consumption trend"""
        if not self._is_enterprise_available():
            raise UserError(_("Fuel consumption trends require the Enterprise edition."))
        
        end_date = fields.Date.today()
        start_date = end_date - timedelta(days=days)
        
        fuel_records = self.search([
            ('vehicle_id', '=', vehicle_id),
            ('refuel_date', '>=', start_date),
            ('refuel_date', '<=', end_date),
        ], order='refuel_date asc')
        
        trend_data = []
        current_date = start_date
        
        while current_date <= end_date:
            day_records = fuel_records.filtered(lambda r: r.refuel_date.date() == current_date)
            
            total_fuel = sum(day_records.mapped('fuel_quantity'))
            total_cost = sum(day_records.mapped('total_cost'))
            
            trend_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'fuel_quantity': total_fuel,
                'total_cost': total_cost,
                'records_count': len(day_records),
            })
            
            current_date += timedelta(days=1)
        
        return trend_data
    
    @api.model
    def get_fuel_efficiency_ranking(self, limit=10):
        """Get fuel efficiency ranking of vehicles"""
        if not self._is_enterprise_available():
            raise UserError(_("Fuel efficiency ranking requires the Enterprise edition."))
        
        vehicles = self.env['fleet.vehicle'].search([
            ('is_rental_vehicle', '=', True),
        ])
        
        efficiency_data = []
        for vehicle in vehicles:
            # Get recent fuel records
            recent_records = self.search([
                ('vehicle_id', '=', vehicle.id),
                ('refuel_date', '>=', fields.Date.today() - timedelta(days=90)),
                ('fuel_efficiency', '>', 0),
            ])
            
            if recent_records:
                avg_efficiency = sum(recent_records.mapped('fuel_efficiency')) / len(recent_records)
                efficiency_data.append({
                    'vehicle_id': vehicle.id,
                    'vehicle_name': vehicle.name,
                    'avg_efficiency': avg_efficiency,
                    'records_count': len(recent_records),
                })
        
        # Sort by efficiency (lower is better)
        efficiency_data.sort(key=lambda x: x['avg_efficiency'])
        
        return efficiency_data[:limit]
    
    @api.model
    def get_fuel_alerts(self):
        """Get fuel-related alerts"""
        if not self._is_enterprise_available():
            return []
        
        alerts = []
        
        # Check for vehicles with low fuel efficiency
        vehicles = self.env['fleet.vehicle'].search([
            ('is_rental_vehicle', '=', True),
        ])
        
        for vehicle in vehicles:
            recent_records = self.search([
                ('vehicle_id', '=', vehicle.id),
                ('refuel_date', '>=', fields.Date.today() - timedelta(days=30)),
                ('fuel_efficiency', '>', 0),
            ])
            
            if recent_records:
                avg_efficiency = sum(recent_records.mapped('fuel_efficiency')) / len(recent_records)
                
                # Alert if efficiency is below 8 L/100km (good efficiency threshold)
                if avg_efficiency > 8.0:
                    alerts.append({
                        'type': 'low_efficiency',
                        'vehicle_id': vehicle.id,
                        'vehicle_name': vehicle.name,
                        'efficiency': avg_efficiency,
                        'message': f'Low fuel efficiency: {avg_efficiency:.2f} L/100km',
                        'severity': 'medium',
                    })
        
        return alerts
    
    @api.model
    def get_fuel_forecast(self, vehicle_id, days=30):
        """Get fuel consumption forecast"""
        if not self._is_enterprise_available():
            raise UserError(_("Fuel forecasting requires the Enterprise edition."))
        
        # Get historical data
        historical_records = self.search([
            ('vehicle_id', '=', vehicle_id),
            ('refuel_date', '>=', fields.Date.today() - timedelta(days=90)),
        ], order='refuel_date asc')
        
        if not historical_records:
            return []
        
        # Calculate average daily consumption
        total_fuel = sum(historical_records.mapped('fuel_quantity'))
        total_days = (historical_records[-1].refuel_date - historical_records[0].refuel_date).days
        
        if total_days > 0:
            avg_daily_consumption = total_fuel / total_days
        else:
            avg_daily_consumption = 0
        
        # Generate forecast
        forecast_data = []
        current_date = fields.Date.today()
        
        for i in range(days):
            forecast_date = current_date + timedelta(days=i)
            forecast_consumption = avg_daily_consumption * (i + 1)
            
            forecast_data.append({
                'date': forecast_date.strftime('%Y-%m-%d'),
                'predicted_consumption': forecast_consumption,
                'confidence': max(0, 100 - (i * 2)),  # Decreasing confidence over time
            })
        
        return forecast_data


class FleetFuelCard(models.Model):
    _name = 'fleet.fuel.card'
    _description = 'Fleet Fuel Card Management'
    
    name = fields.Char('Card Name', required=True)
    card_number = fields.Char('Card Number', required=True)
    card_type = fields.Selection([
        ('company', 'Company Card'),
        ('driver', 'Driver Card'),
        ('vehicle', 'Vehicle Card'),
    ], string='Card Type', required=True)
    
    # Assignment
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    driver_id = fields.Many2one('fleet.driver', string='Driver')
    
    # Card Details
    issuer = fields.Char('Card Issuer')
    expiry_date = fields.Date('Expiry Date')
    credit_limit = fields.Monetary('Credit Limit', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Status
    active = fields.Boolean('Active', default=True)
    blocked = fields.Boolean('Blocked', default=False)
    
    # Usage Tracking
    fuel_records = fields.One2many('fleet.fuel.management', 'fuel_card_id', string='Fuel Records')
    total_usage = fields.Monetary('Total Usage', currency_field='currency_id', compute='_compute_usage_stats', store=True)
    usage_count = fields.Integer('Usage Count', compute='_compute_usage_stats', store=True)
    
    # Enterprise Features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.depends('fuel_records.total_cost')
    def _compute_usage_stats(self):
        """Compute usage statistics"""
        for card in self:
            if card._is_enterprise_available():
                card.total_usage = sum(card.fuel_records.mapped('total_cost'))
                card.usage_count = len(card.fuel_records)
            else:
                card.total_usage = 0
                card.usage_count = 0
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    @api.model
    def get_card_usage_analytics(self, card_id, start_date=None, end_date=None):
        """Get fuel card usage analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Fuel card analytics require the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        card = self.browse(card_id)
        if not card.exists():
            raise UserError(_("Fuel card not found."))
        
        fuel_records = self.env['fleet.fuel.management'].search([
            ('fuel_card_id', '=', card_id),
            ('refuel_date', '>=', start_date),
            ('refuel_date', '<=', end_date),
        ])
        
        total_usage = sum(fuel_records.mapped('total_cost'))
        total_fuel = sum(fuel_records.mapped('fuel_quantity'))
        usage_count = len(fuel_records)
        
        return {
            'card_id': card_id,
            'card_name': card.name,
            'total_usage': total_usage,
            'total_fuel': total_fuel,
            'usage_count': usage_count,
            'avg_transaction': total_usage / usage_count if usage_count > 0 else 0,
        }




