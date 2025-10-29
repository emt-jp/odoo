# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class FleetFinancialManagement(models.Model):
    _name = 'fleet.financial.management'
    _description = 'Fleet Financial Management'
    
    # Financial Period
    name = fields.Char('Financial Period', required=True)
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    
    # Revenue
    total_revenue = fields.Monetary('Total Revenue', currency_field='currency_id', compute='_compute_financial_metrics', store=True)
    rental_revenue = fields.Monetary('Rental Revenue', currency_field='currency_id', compute='_compute_financial_metrics', store=True)
    additional_charges_revenue = fields.Monetary('Additional Charges Revenue', currency_field='currency_id', compute='_compute_financial_metrics', store=True)
    
    # Operating Costs
    total_operating_costs = fields.Monetary('Total Operating Costs', currency_field='currency_id', compute='_compute_financial_metrics', store=True)
    maintenance_costs = fields.Monetary('Maintenance Costs', currency_field='currency_id', compute='_compute_financial_metrics', store=True)
    fuel_costs = fields.Monetary('Fuel Costs', currency_field='currency_id', compute='_compute_financial_metrics', store=True)
    insurance_costs = fields.Monetary('Insurance Costs', currency_field='currency_id', compute='_compute_financial_metrics', store=True)
    depreciation_costs = fields.Monetary('Depreciation Costs', currency_field='currency_id', compute='_compute_financial_metrics', store=True)
    
    # Profitability
    gross_profit = fields.Monetary('Gross Profit', currency_field='currency_id', compute='_compute_financial_metrics', store=True)
    net_profit = fields.Monetary('Net Profit', currency_field='currency_id', compute='_compute_financial_metrics', store=True)
    profit_margin = fields.Float('Profit Margin (%)', digits=(5, 2), compute='_compute_financial_metrics', store=True)
    
    # Currency
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Enterprise Features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.depends('start_date', 'end_date')
    def _compute_financial_metrics(self):
        """Compute financial metrics"""
        for record in self:
            if record._is_enterprise_available() and record.start_date and record.end_date:
                record._calculate_financial_metrics()
            else:
                record._reset_financial_metrics()
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return self.env.context.get('is_enterprise', True)
    
    def _calculate_financial_metrics(self):
        """Calculate financial metrics"""
        # Get rental revenue
        rentals = self.env['fleet.rental'].search([
            ('start_date', '>=', self.start_date),
            ('start_date', '<=', self.end_date),
            ('state', 'in', ['completed', 'in_progress']),
        ])
        
        self.rental_revenue = sum(rentals.mapped('total_amount'))
        self.additional_charges_revenue = sum(rentals.mapped('total_charges'))
        self.total_revenue = self.rental_revenue + self.additional_charges_revenue
        
        # Get maintenance costs
        maintenance_records = self.env['fleet.maintenance'].search([
            ('scheduled_date', '>=', self.start_date),
            ('scheduled_date', '<=', self.end_date),
            ('status', '=', 'completed'),
        ])
        self.maintenance_costs = sum(maintenance_records.mapped('total_cost'))
        
        # Get fuel costs
        fuel_records = self.env['fleet.fuel.management'].search([
            ('refuel_date', '>=', self.start_date),
            ('refuel_date', '<=', self.end_date),
        ])
        self.fuel_costs = sum(fuel_records.mapped('total_cost'))
        
        # Get insurance costs
        insurance_policies = self.env['fleet.insurance'].search([
            ('start_date', '<=', self.end_date),
            ('expiry_date', '>=', self.start_date),
        ])
        self.insurance_costs = sum(insurance_policies.mapped('premium_amount'))
        
        # Calculate depreciation costs
        self.depreciation_costs = self._calculate_depreciation_costs()
        
        # Calculate total operating costs
        self.total_operating_costs = (self.maintenance_costs + self.fuel_costs + 
                                    self.insurance_costs + self.depreciation_costs)
        
        # Calculate profitability
        self.gross_profit = self.total_revenue - self.total_operating_costs
        self.net_profit = self.gross_profit  # Simplified - no other expenses
        
        # Calculate profit margin
        self.profit_margin = (self.net_profit / self.total_revenue * 100) if self.total_revenue > 0 else 0
    
    def _calculate_depreciation_costs(self):
        """Calculate depreciation costs for vehicles"""
        vehicles = self.env['fleet.vehicle'].search([
            ('is_rental_vehicle', '=', True),
        ])
        
        total_depreciation = 0.0
        for vehicle in vehicles:
            if vehicle.purchase_price and vehicle.depreciation_rate:
                # Calculate annual depreciation
                annual_depreciation = vehicle.purchase_price * (vehicle.depreciation_rate / 100)
                
                # Calculate period depreciation based on days in period
                period_days = (self.end_date - self.start_date).days
                period_depreciation = annual_depreciation * (period_days / 365)
                
                total_depreciation += period_depreciation
        
        return total_depreciation
    
    def _reset_financial_metrics(self):
        """Reset financial metrics"""
        self.total_revenue = 0.0
        self.rental_revenue = 0.0
        self.additional_charges_revenue = 0.0
        self.total_operating_costs = 0.0
        self.maintenance_costs = 0.0
        self.fuel_costs = 0.0
        self.insurance_costs = 0.0
        self.depreciation_costs = 0.0
        self.gross_profit = 0.0
        self.net_profit = 0.0
        self.profit_margin = 0.0
    
    @api.model
    def generate_financial_report(self, start_date, end_date):
        """Generate financial report for period"""
        if not self._is_enterprise_available():
            raise UserError(_("Financial reporting requires the Enterprise edition."))
        
        # Create or update financial record
        financial_record = self.search([
            ('start_date', '=', start_date),
            ('end_date', '=', end_date),
        ], limit=1)
        
        if not financial_record:
            financial_record = self.create({
                'name': f'Financial Report - {start_date} to {end_date}',
                'start_date': start_date,
                'end_date': end_date,
            })
        
        return {
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
            'revenue': {
                'total_revenue': financial_record.total_revenue,
                'rental_revenue': financial_record.rental_revenue,
                'additional_charges_revenue': financial_record.additional_charges_revenue,
            },
            'costs': {
                'total_operating_costs': financial_record.total_operating_costs,
                'maintenance_costs': financial_record.maintenance_costs,
                'fuel_costs': financial_record.fuel_costs,
                'insurance_costs': financial_record.insurance_costs,
                'depreciation_costs': financial_record.depreciation_costs,
            },
            'profitability': {
                'gross_profit': financial_record.gross_profit,
                'net_profit': financial_record.net_profit,
                'profit_margin': financial_record.profit_margin,
            },
        }
    
    @api.model
    def get_financial_dashboard(self):
        """Get financial dashboard data"""
        if not self._is_enterprise_available():
            raise UserError(_("Financial dashboard requires the Enterprise edition."))
        
        # Get current month data
        today = fields.Date.today()
        start_of_month = today.replace(day=1)
        end_of_month = today + relativedelta(months=1, day=1) - timedelta(days=1)
        
        current_month = self.generate_financial_report(start_of_month, end_of_month)
        
        # Get previous month data
        prev_start = start_of_month - relativedelta(months=1)
        prev_end = start_of_month - timedelta(days=1)
        previous_month = self.generate_financial_report(prev_start, prev_end)
        
        # Calculate growth rates
        revenue_growth = self._calculate_growth_rate(
            current_month['revenue']['total_revenue'],
            previous_month['revenue']['total_revenue']
        )
        
        profit_growth = self._calculate_growth_rate(
            current_month['profitability']['net_profit'],
            previous_month['profitability']['net_profit']
        )
        
        return {
            'current_month': current_month,
            'previous_month': previous_month,
            'growth_rates': {
                'revenue_growth': revenue_growth,
                'profit_growth': profit_growth,
            },
            'kpis': {
                'total_revenue': current_month['revenue']['total_revenue'],
                'total_costs': current_month['costs']['total_operating_costs'],
                'net_profit': current_month['profitability']['net_profit'],
                'profit_margin': current_month['profitability']['profit_margin'],
            },
        }
    
    def _calculate_growth_rate(self, current_value, previous_value):
        """Calculate growth rate percentage"""
        if previous_value == 0:
            return 0.0
        return ((current_value - previous_value) / previous_value) * 100
    
    @api.model
    def get_vehicle_profitability(self, vehicle_id, start_date=None, end_date=None):
        """Get vehicle profitability analysis"""
        if not self._is_enterprise_available():
            raise UserError(_("Vehicle profitability analysis requires the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        vehicle = self.env['fleet.vehicle'].browse(vehicle_id)
        if not vehicle.exists():
            raise UserError(_("Vehicle not found."))
        
        # Get vehicle revenue
        rentals = self.env['fleet.rental'].search([
            ('vehicle_id', '=', vehicle_id),
            ('start_date', '>=', start_date),
            ('start_date', '<=', end_date),
            ('state', 'in', ['completed', 'in_progress']),
        ])
        
        total_revenue = sum(rentals.mapped('total_amount'))
        
        # Get vehicle costs
        maintenance_costs = sum(self.env['fleet.maintenance'].search([
            ('vehicle_id', '=', vehicle_id),
            ('scheduled_date', '>=', start_date),
            ('scheduled_date', '<=', end_date),
            ('status', '=', 'completed'),
        ]).mapped('total_cost'))
        
        fuel_costs = sum(self.env['fleet.fuel.management'].search([
            ('vehicle_id', '=', vehicle_id),
            ('refuel_date', '>=', start_date),
            ('refuel_date', '<=', end_date),
        ]).mapped('total_cost'))
        
        # Calculate depreciation
        depreciation_cost = 0.0
        if vehicle.purchase_price and vehicle.depreciation_rate:
            period_days = (end_date - start_date).days
            annual_depreciation = vehicle.purchase_price * (vehicle.depreciation_rate / 100)
            depreciation_cost = annual_depreciation * (period_days / 365)
        
        total_costs = maintenance_costs + fuel_costs + depreciation_cost
        net_profit = total_revenue - total_costs
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            'vehicle_id': vehicle_id,
            'vehicle_name': vehicle.name,
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
            'revenue': {
                'total_revenue': total_revenue,
                'rental_count': len(rentals),
                'avg_rental_value': total_revenue / len(rentals) if rentals else 0,
            },
            'costs': {
                'maintenance_costs': maintenance_costs,
                'fuel_costs': fuel_costs,
                'depreciation_cost': depreciation_cost,
                'total_costs': total_costs,
            },
            'profitability': {
                'net_profit': net_profit,
                'profit_margin': profit_margin,
                'roi': (net_profit / vehicle.purchase_price * 100) if vehicle.purchase_price > 0 else 0,
            },
        }
    
    @api.model
    def get_cost_center_analysis(self, start_date=None, end_date=None):
        """Get cost center analysis"""
        if not self._is_enterprise_available():
            raise UserError(_("Cost center analysis requires the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        # Get all vehicles
        vehicles = self.env['fleet.vehicle'].search([
            ('is_rental_vehicle', '=', True),
        ])
        
        cost_centers = {}
        for vehicle in vehicles:
            # Get vehicle costs
            maintenance_costs = sum(self.env['fleet.maintenance'].search([
                ('vehicle_id', '=', vehicle.id),
                ('scheduled_date', '>=', start_date),
                ('scheduled_date', '<=', end_date),
                ('status', '=', 'completed'),
            ]).mapped('total_cost'))
            
            fuel_costs = sum(self.env['fleet.fuel.management'].search([
                ('vehicle_id', '=', vehicle.id),
                ('refuel_date', '>=', start_date),
                ('refuel_date', '<=', end_date),
            ]).mapped('total_cost'))
            
            # Get vehicle revenue
            rentals = self.env['fleet.rental'].search([
                ('vehicle_id', '=', vehicle.id),
                ('start_date', '>=', start_date),
                ('start_date', '<=', end_date),
                ('state', 'in', ['completed', 'in_progress']),
            ])
            
            revenue = sum(rentals.mapped('total_amount'))
            total_costs = maintenance_costs + fuel_costs
            
            cost_centers[vehicle.id] = {
                'vehicle_name': vehicle.name,
                'vehicle_type': vehicle.vehicle_type,
                'rental_category': vehicle.rental_category,
                'revenue': revenue,
                'maintenance_costs': maintenance_costs,
                'fuel_costs': fuel_costs,
                'total_costs': total_costs,
                'net_profit': revenue - total_costs,
                'profit_margin': ((revenue - total_costs) / revenue * 100) if revenue > 0 else 0,
            }
        
        return cost_centers
    
    @api.model
    def get_budget_vs_actual(self, start_date=None, end_date=None):
        """Get budget vs actual analysis"""
        if not self._is_enterprise_available():
            raise UserError(_("Budget analysis requires the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=30)
        if not end_date:
            end_date = fields.Date.today()
        
        # Get actual data
        actual_data = self.generate_financial_report(start_date, end_date)
        
        # Get budget data (this would come from budget planning module)
        budget_data = self._get_budget_data(start_date, end_date)
        
        # Calculate variances
        revenue_variance = actual_data['revenue']['total_revenue'] - budget_data.get('revenue', 0)
        cost_variance = actual_data['costs']['total_operating_costs'] - budget_data.get('costs', 0)
        profit_variance = actual_data['profitability']['net_profit'] - budget_data.get('profit', 0)
        
        return {
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
            'actual': actual_data,
            'budget': budget_data,
            'variances': {
                'revenue_variance': revenue_variance,
                'cost_variance': cost_variance,
                'profit_variance': profit_variance,
            },
        }
    
    def _get_budget_data(self, start_date, end_date):
        """Get budget data for period"""
        # This would integrate with a budget planning module
        # For now, return mock data
        return {
            'revenue': 50000.0,
            'costs': 30000.0,
            'profit': 20000.0,
        }
    
    @api.model
    def get_financial_forecast(self, months=12):
        """Get financial forecast"""
        if not self._is_enterprise_available():
            raise UserError(_("Financial forecasting requires the Enterprise edition."))
        
        # Get historical data for trend analysis
        end_date = fields.Date.today()
        start_date = end_date - relativedelta(months=6)
        
        historical_data = []
        current_date = start_date
        
        while current_date <= end_date:
            month_end = current_date + relativedelta(months=1, day=1) - timedelta(days=1)
            month_data = self.generate_financial_report(current_date, month_end)
            
            historical_data.append({
                'month': current_date.strftime('%Y-%m'),
                'revenue': month_data['revenue']['total_revenue'],
                'costs': month_data['costs']['total_operating_costs'],
                'profit': month_data['profitability']['net_profit'],
            })
            
            current_date += relativedelta(months=1)
        
        # Generate forecast based on historical trends
        forecast_data = []
        for i in range(months):
            forecast_month = end_date + relativedelta(months=i+1)
            
            # Simple linear trend (in real implementation, use more sophisticated forecasting)
            if len(historical_data) >= 2:
                revenue_trend = (historical_data[-1]['revenue'] - historical_data[-2]['revenue']) / historical_data[-2]['revenue'] if historical_data[-2]['revenue'] > 0 else 0
                cost_trend = (historical_data[-1]['costs'] - historical_data[-2]['costs']) / historical_data[-2]['costs'] if historical_data[-2]['costs'] > 0 else 0
                
                forecast_revenue = historical_data[-1]['revenue'] * (1 + revenue_trend) ** (i + 1)
                forecast_costs = historical_data[-1]['costs'] * (1 + cost_trend) ** (i + 1)
                forecast_profit = forecast_revenue - forecast_costs
            else:
                forecast_revenue = historical_data[-1]['revenue'] if historical_data else 0
                forecast_costs = historical_data[-1]['costs'] if historical_data else 0
                forecast_profit = forecast_revenue - forecast_costs
            
            forecast_data.append({
                'month': forecast_month.strftime('%Y-%m'),
                'revenue': forecast_revenue,
                'costs': forecast_costs,
                'profit': forecast_profit,
            })
        
        return {
            'historical_data': historical_data,
            'forecast_data': forecast_data,
            'forecast_period': months,
        }




