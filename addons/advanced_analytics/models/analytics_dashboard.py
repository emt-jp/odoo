# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class AnalyticsDashboard(models.Model):
    _name = 'analytics.dashboard'
    _description = 'Analytics Dashboard'
    _order = 'sequence, name'
    
    name = fields.Char('Dashboard Name', required=True, translate=True)
    description = fields.Text('Description', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    
    # Enterprise features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    # Dashboard configuration
    dashboard_type = fields.Selection([
        ('sales', 'Sales Analytics'),
        ('financial', 'Financial Analytics'),
        ('inventory', 'Inventory Analytics'),
        ('crm', 'CRM Analytics'),
        ('custom', 'Custom Dashboard'),
    ], string='Dashboard Type', required=True, default='sales')
    
    # KPI configuration
    kpi_ids = fields.One2many('analytics.kpi', 'dashboard_id', string='KPIs')
    chart_config = fields.Text('Chart Configuration', help='JSON configuration for charts')
    
    # Access control
    user_ids = fields.Many2many('res.users', string='Allowed Users')
    group_ids = fields.Many2many('res.groups', string='Allowed Groups')
    
    # Time period
    date_from = fields.Date('Date From', default=lambda self: fields.Date.today() - relativedelta(months=1))
    date_to = fields.Date('Date To', default=fields.Date.today)
    
    @api.model
    def get_dashboard_data(self, dashboard_id=None):
        """Get dashboard data with enterprise feature check"""
        if not self._is_enterprise_available():
            raise UserError(_("Advanced analytics requires the Enterprise edition. Please upgrade to access this feature."))
        
        dashboard = self.browse(dashboard_id) if dashboard_id else self.search([('active', '=', True)], limit=1)
        if not dashboard:
            raise UserError(_("No active dashboard found."))
        
        return {
            'dashboard': dashboard.read()[0],
            'kpis': self._get_kpi_data(dashboard),
            'charts': self._get_chart_data(dashboard),
            'summary': self._get_summary_data(dashboard),
        }
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        # You can implement your own licensing logic here
        # For now, we'll use a simple context check
        return True  # Enterprise checks disabled
    
    def _get_kpi_data(self, dashboard):
        """Get KPI data for dashboard"""
        kpi_data = []
        for kpi in dashboard.kpi_ids:
            if kpi.active:
                kpi_data.append({
                    'id': kpi.id,
                    'name': kpi.name,
                    'value': kpi.get_current_value(),
                    'previous_value': kpi.get_previous_value(),
                    'change_percent': kpi.get_change_percent(),
                    'trend': kpi.get_trend(),
                    'color': kpi.color,
                    'icon': kpi.icon,
                })
        return kpi_data
    
    def _get_chart_data(self, dashboard):
        """Get chart data for dashboard"""
        chart_data = []
        
        if dashboard.dashboard_type == 'sales':
            chart_data = self._get_sales_chart_data(dashboard)
        elif dashboard.dashboard_type == 'financial':
            chart_data = self._get_financial_chart_data(dashboard)
        elif dashboard.dashboard_type == 'inventory':
            chart_data = self._get_inventory_chart_data(dashboard)
        elif dashboard.dashboard_type == 'crm':
            chart_data = self._get_crm_chart_data(dashboard)
        
        return chart_data
    
    def _get_sales_chart_data(self, dashboard):
        """Get sales chart data"""
        # Sales over time
        sales_data = self._get_sales_over_time(dashboard.date_from, dashboard.date_to)
        
        # Top products
        top_products = self._get_top_products(dashboard.date_from, dashboard.date_to)
        
        # Sales by region
        sales_by_region = self._get_sales_by_region(dashboard.date_from, dashboard.date_to)
        
        return [
            {
                'type': 'line',
                'title': 'Sales Over Time',
                'data': sales_data,
                'x_axis': 'date',
                'y_axis': 'amount',
            },
            {
                'type': 'bar',
                'title': 'Top Products',
                'data': top_products,
                'x_axis': 'product',
                'y_axis': 'quantity',
            },
            {
                'type': 'pie',
                'title': 'Sales by Region',
                'data': sales_by_region,
                'x_axis': 'region',
                'y_axis': 'amount',
            },
        ]
    
    def _get_financial_chart_data(self, dashboard):
        """Get financial chart data"""
        # Revenue vs Expenses
        revenue_expenses = self._get_revenue_expenses(dashboard.date_from, dashboard.date_to)
        
        # Cash flow
        cash_flow = self._get_cash_flow(dashboard.date_from, dashboard.date_to)
        
        # Profit margin
        profit_margin = self._get_profit_margin(dashboard.date_from, dashboard.date_to)
        
        return [
            {
                'type': 'line',
                'title': 'Revenue vs Expenses',
                'data': revenue_expenses,
                'x_axis': 'date',
                'y_axis': 'amount',
            },
            {
                'type': 'bar',
                'title': 'Cash Flow',
                'data': cash_flow,
                'x_axis': 'month',
                'y_axis': 'amount',
            },
            {
                'type': 'line',
                'title': 'Profit Margin',
                'data': profit_margin,
                'x_axis': 'date',
                'y_axis': 'percentage',
            },
        ]
    
    def _get_inventory_chart_data(self, dashboard):
        """Get inventory chart data"""
        # Stock levels
        stock_levels = self._get_stock_levels()
        
        # Top selling products
        top_selling = self._get_top_selling_products(dashboard.date_from, dashboard.date_to)
        
        # Low stock alerts
        low_stock = self._get_low_stock_products()
        
        return [
            {
                'type': 'bar',
                'title': 'Stock Levels',
                'data': stock_levels,
                'x_axis': 'product',
                'y_axis': 'quantity',
            },
            {
                'type': 'pie',
                'title': 'Top Selling Products',
                'data': top_selling,
                'x_axis': 'product',
                'y_axis': 'quantity',
            },
            {
                'type': 'bar',
                'title': 'Low Stock Alerts',
                'data': low_stock,
                'x_axis': 'product',
                'y_axis': 'quantity',
            },
        ]
    
    def _get_crm_chart_data(self, dashboard):
        """Get CRM chart data"""
        # Lead conversion
        lead_conversion = self._get_lead_conversion(dashboard.date_from, dashboard.date_to)
        
        # Sales pipeline
        sales_pipeline = self._get_sales_pipeline()
        
        # Customer acquisition
        customer_acquisition = self._get_customer_acquisition(dashboard.date_from, dashboard.date_to)
        
        return [
            {
                'type': 'funnel',
                'title': 'Lead Conversion',
                'data': lead_conversion,
                'x_axis': 'stage',
                'y_axis': 'count',
            },
            {
                'type': 'bar',
                'title': 'Sales Pipeline',
                'data': sales_pipeline,
                'x_axis': 'stage',
                'y_axis': 'amount',
            },
            {
                'type': 'line',
                'title': 'Customer Acquisition',
                'data': customer_acquisition,
                'x_axis': 'date',
                'y_axis': 'count',
            },
        ]
    
    def _get_summary_data(self, dashboard):
        """Get summary data for dashboard"""
        if dashboard.dashboard_type == 'sales':
            return self._get_sales_summary(dashboard.date_from, dashboard.date_to)
        elif dashboard.dashboard_type == 'financial':
            return self._get_financial_summary(dashboard.date_from, dashboard.date_to)
        elif dashboard.dashboard_type == 'inventory':
            return self._get_inventory_summary()
        elif dashboard.dashboard_type == 'crm':
            return self._get_crm_summary(dashboard.date_from, dashboard.date_to)
        return {}
    
    # Sales Analytics Methods
    def _get_sales_over_time(self, date_from, date_to):
        """Get sales data over time"""
        sales_orders = self.env['sale.order'].search([
            ('date_order', '>=', date_from),
            ('date_order', '<=', date_to),
            ('state', 'in', ['sale', 'done']),
        ])
        
        data = {}
        for order in sales_orders:
            date_key = order.date_order.strftime('%Y-%m-%d')
            if date_key not in data:
                data[date_key] = 0
            data[date_key] += order.amount_total
        
        return [{'date': k, 'amount': v} for k, v in sorted(data.items())]
    
    def _get_top_products(self, date_from, date_to, limit=10):
        """Get top selling products"""
        lines = self.env['sale.order.line'].search([
            ('order_id.date_order', '>=', date_from),
            ('order_id.date_order', '<=', date_to),
            ('order_id.state', 'in', ['sale', 'done']),
        ])
        
        product_data = {}
        for line in lines:
            if line.product_id.id not in product_data:
                product_data[line.product_id.id] = {
                    'product': line.product_id.name,
                    'quantity': 0,
                    'amount': 0,
                }
            product_data[line.product_id.id]['quantity'] += line.product_uom_qty
            product_data[line.product_id.id]['amount'] += line.price_subtotal
        
        return sorted(product_data.values(), key=lambda x: x['quantity'], reverse=True)[:limit]
    
    def _get_sales_by_region(self, date_from, date_to):
        """Get sales by region"""
        orders = self.env['sale.order'].search([
            ('date_order', '>=', date_from),
            ('date_order', '<=', date_to),
            ('state', 'in', ['sale', 'done']),
        ])
        
        region_data = {}
        for order in orders:
            region = order.partner_id.country_id.name or 'Unknown'
            if region not in region_data:
                region_data[region] = 0
            region_data[region] += order.amount_total
        
        return [{'region': k, 'amount': v} for k, v in region_data.items()]
    
    def _get_sales_summary(self, date_from, date_to):
        """Get sales summary data"""
        orders = self.env['sale.order'].search([
            ('date_order', '>=', date_from),
            ('date_order', '<=', date_to),
            ('state', 'in', ['sale', 'done']),
        ])
        
        total_sales = sum(orders.mapped('amount_total'))
        total_orders = len(orders)
        avg_order_value = total_sales / total_orders if total_orders > 0 else 0
        
        # Previous period comparison
        prev_date_from = date_from - relativedelta(months=1)
        prev_date_to = date_to - relativedelta(months=1)
        prev_orders = self.env['sale.order'].search([
            ('date_order', '>=', prev_date_from),
            ('date_order', '<=', prev_date_to),
            ('state', 'in', ['sale', 'done']),
        ])
        prev_total_sales = sum(prev_orders.mapped('amount_total'))
        growth_rate = ((total_sales - prev_total_sales) / prev_total_sales * 100) if prev_total_sales > 0 else 0
        
        return {
            'total_sales': total_sales,
            'total_orders': total_orders,
            'avg_order_value': avg_order_value,
            'growth_rate': growth_rate,
        }
    
    # Financial Analytics Methods
    def _get_revenue_expenses(self, date_from, date_to):
        """Get revenue vs expenses data"""
        # This is a simplified version - you would need to implement proper accounting logic
        revenue = self._get_sales_summary(date_from, date_to)['total_sales']
        expenses = revenue * 0.7  # Simplified - 70% of revenue as expenses
        
        return [
            {'date': date_from.strftime('%Y-%m-%d'), 'revenue': revenue, 'expenses': expenses},
            {'date': date_to.strftime('%Y-%m-%d'), 'revenue': revenue, 'expenses': expenses},
        ]
    
    def _get_cash_flow(self, date_from, date_to):
        """Get cash flow data"""
        # Simplified cash flow calculation
        months = []
        current_date = date_from
        while current_date <= date_to:
            months.append({
                'month': current_date.strftime('%Y-%m'),
                'amount': 10000 + (current_date.month * 1000),  # Simplified
            })
            current_date += relativedelta(months=1)
        
        return months
    
    def _get_profit_margin(self, date_from, date_to):
        """Get profit margin data"""
        # Simplified profit margin calculation
        return [
            {'date': date_from.strftime('%Y-%m-%d'), 'percentage': 25.5},
            {'date': date_to.strftime('%Y-%m-%d'), 'percentage': 28.3},
        ]
    
    def _get_financial_summary(self, date_from, date_to):
        """Get financial summary data"""
        sales_summary = self._get_sales_summary(date_from, date_to)
        return {
            'revenue': sales_summary['total_sales'],
            'expenses': sales_summary['total_sales'] * 0.7,
            'profit': sales_summary['total_sales'] * 0.3,
            'profit_margin': 30.0,
        }
    
    # Inventory Analytics Methods
    def _get_stock_levels(self):
        """Get current stock levels"""
        products = self.env['product.product'].search([('type', '=', 'product')], limit=10)
        return [{'product': p.name, 'quantity': p.qty_available} for p in products]
    
    def _get_top_selling_products(self, date_from, date_to, limit=5):
        """Get top selling products for inventory analysis"""
        return self._get_top_products(date_from, date_to, limit)
    
    def _get_low_stock_products(self):
        """Get products with low stock"""
        products = self.env['product.product'].search([
            ('type', '=', 'product'),
            ('qty_available', '<', 10),
        ])
        return [{'product': p.name, 'quantity': p.qty_available} for p in products]
    
    def _get_inventory_summary(self):
        """Get inventory summary data"""
        products = self.env['product.product'].search([('type', '=', 'product')])
        total_products = len(products)
        low_stock_count = len(self.env['product.product'].search([
            ('type', '=', 'product'),
            ('qty_available', '<', 10),
        ]))
        
        return {
            'total_products': total_products,
            'low_stock_count': low_stock_count,
            'stock_value': sum(products.mapped(lambda p: p.qty_available * p.standard_price)),
        }
    
    # CRM Analytics Methods
    def _get_lead_conversion(self, date_from, date_to):
        """Get lead conversion funnel data"""
        leads = self.env['crm.lead'].search([
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to),
        ])
        
        stages = ['New', 'Qualified', 'Proposal', 'Negotiation', 'Won']
        data = []
        for stage in stages:
            count = len(leads.filtered(lambda l: l.stage_id.name == stage))
            data.append({'stage': stage, 'count': count})
        
        return data
    
    def _get_sales_pipeline(self):
        """Get sales pipeline data"""
        opportunities = self.env['crm.lead'].search([
            ('type', '=', 'opportunity'),
            ('probability', '>', 0),
        ])
        
        stages = ['New', 'Qualified', 'Proposal', 'Negotiation', 'Won']
        data = []
        for stage in stages:
            stage_opps = opportunities.filtered(lambda o: o.stage_id.name == stage)
            amount = sum(stage_opps.mapped('expected_revenue'))
            data.append({'stage': stage, 'amount': amount})
        
        return data
    
    def _get_customer_acquisition(self, date_from, date_to):
        """Get customer acquisition data"""
        customers = self.env['res.partner'].search([
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to),
            ('is_company', '=', True),
        ])
        
        data = {}
        for customer in customers:
            date_key = customer.create_date.strftime('%Y-%m-%d')
            if date_key not in data:
                data[date_key] = 0
            data[date_key] += 1
        
        return [{'date': k, 'count': v} for k, v in sorted(data.items())]
    
    def _get_crm_summary(self, date_from, date_to):
        """Get CRM summary data"""
        leads = self.env['crm.lead'].search([
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to),
        ])
        
        opportunities = leads.filtered(lambda l: l.type == 'opportunity')
        won_opportunities = opportunities.filtered(lambda o: o.stage_id.name == 'Won')
        
        return {
            'total_leads': len(leads),
            'total_opportunities': len(opportunities),
            'won_opportunities': len(won_opportunities),
            'conversion_rate': (len(won_opportunities) / len(opportunities) * 100) if opportunities else 0,
        }
    
    def action_view_dashboard(self):
        """Open dashboard view"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'analytics.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def create_default_dashboards(self):
        """Create default dashboards"""
        dashboards = [
            {
                'name': 'Sales Analytics',
                'description': 'Advanced sales analytics and reporting',
                'dashboard_type': 'sales',
                'sequence': 10,
            },
            {
                'name': 'Financial Analytics',
                'description': 'Financial performance and analysis',
                'dashboard_type': 'financial',
                'sequence': 20,
            },
            {
                'name': 'Inventory Analytics',
                'description': 'Inventory management and analysis',
                'dashboard_type': 'inventory',
                'sequence': 30,
            },
            {
                'name': 'CRM Analytics',
                'description': 'Customer relationship management analytics',
                'dashboard_type': 'crm',
                'sequence': 40,
            },
        ]
        
        for dashboard_data in dashboards:
            if not self.search([('name', '=', dashboard_data['name'])]):
                self.create(dashboard_data)




