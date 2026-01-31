# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class AnalyticsKPI(models.Model):
    _name = 'analytics.kpi'
    _description = 'Analytics KPI'
    _order = 'sequence, name'
    
    name = fields.Char('KPI Name', required=True, translate=True)
    description = fields.Text('Description', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    
    # KPI configuration
    dashboard_id = fields.Many2one('analytics.dashboard', string='Dashboard', required=True, ondelete='cascade')
    kpi_type = fields.Selection([
        ('sales', 'Sales'),
        ('financial', 'Financial'),
        ('inventory', 'Inventory'),
        ('crm', 'CRM'),
        ('custom', 'Custom'),
    ], string='KPI Type', required=True)
    
    # Display configuration
    color = fields.Selection([
        ('primary', 'Primary'),
        ('success', 'Success'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('danger', 'Danger'),
        ('secondary', 'Secondary'),
    ], string='Color', default='primary')
    
    icon = fields.Char('Icon', default='fa fa-chart-line', help='Font Awesome icon class')
    
    # Calculation configuration
    calculation_method = fields.Selection([
        ('sum', 'Sum'),
        ('average', 'Average'),
        ('count', 'Count'),
        ('percentage', 'Percentage'),
        ('custom', 'Custom'),
    ], string='Calculation Method', required=True, default='sum')
    
    model_name = fields.Char('Model Name', required=True, default='sale.order')
    field_name = fields.Char('Field Name', required=True, default='amount_total')
    domain = fields.Text('Domain', help='Domain filter for data calculation')
    
    # Time period
    period_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    ], string='Period Type', default='monthly')
    
    period_days = fields.Integer('Period Days', default=30, help='Number of days for custom period')
    
    # Comparison
    compare_previous = fields.Boolean('Compare with Previous Period', default=True)
    compare_target = fields.Boolean('Compare with Target', default=False)
    target_value = fields.Float('Target Value', default=0.0)

    # Thresholds for alerts
    threshold_warning = fields.Float('Warning Threshold', help='Value at which to show warning status')
    threshold_critical = fields.Float('Critical Threshold', help='Value at which to show critical status')

    # Aggregation function (alternative to calculation_method for view compatibility)
    aggregation_function = fields.Selection([
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
        ('count', 'Count'),
    ], string='Aggregation Function', default='sum')
    
    # Formatting
    number_format = fields.Selection([
        ('integer', 'Integer'),
        ('decimal', 'Decimal'),
        ('currency', 'Currency'),
        ('percentage', 'Percentage'),
    ], string='Number Format', default='currency')
    
    decimal_places = fields.Integer('Decimal Places', default=2)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Enterprise features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.model
    def get_current_value(self):
        """Get current KPI value"""
        if not self._is_enterprise_available():
            raise UserError(_("Advanced KPI features require the Enterprise edition."))
        
        try:
            if self.calculation_method == 'custom':
                return self._calculate_custom_value()
            else:
                return self._calculate_standard_value()
        except Exception as e:
            _logger.error(f"Error calculating KPI {self.name}: {str(e)}")
            return 0.0
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    def _calculate_standard_value(self):
        """Calculate standard KPI value"""
        model = self.env[self.model_name]
        domain = self._get_domain()
        
        if self.calculation_method == 'sum':
            return sum(model.search(domain).mapped(self.field_name))
        elif self.calculation_method == 'average':
            records = model.search(domain)
            values = records.mapped(self.field_name)
            return sum(values) / len(values) if values else 0.0
        elif self.calculation_method == 'count':
            return model.search_count(domain)
        elif self.calculation_method == 'percentage':
            total = model.search_count(self._get_base_domain())
            filtered = model.search_count(domain)
            return (filtered / total * 100) if total > 0 else 0.0
        
        return 0.0
    
    def _calculate_custom_value(self):
        """Calculate custom KPI value"""
        # Implement custom calculation logic based on KPI type
        if self.kpi_type == 'sales':
            return self._calculate_sales_kpi()
        elif self.kpi_type == 'financial':
            return self._calculate_financial_kpi()
        elif self.kpi_type == 'inventory':
            return self._calculate_inventory_kpi()
        elif self.kpi_type == 'crm':
            return self._calculate_crm_kpi()
        
        return 0.0
    
    def _calculate_sales_kpi(self):
        """Calculate sales-specific KPI"""
        if self.name == 'Total Sales':
            return self._get_total_sales()
        elif self.name == 'Average Order Value':
            return self._get_average_order_value()
        elif self.name == 'Number of Orders':
            return self._get_number_of_orders()
        elif self.name == 'Sales Growth Rate':
            return self._get_sales_growth_rate()
        elif self.name == 'Top Customer':
            return self._get_top_customer_value()
        
        return 0.0
    
    def _calculate_financial_kpi(self):
        """Calculate financial-specific KPI"""
        if self.name == 'Revenue':
            return self._get_total_sales()
        elif self.name == 'Profit Margin':
            return self._get_profit_margin()
        elif self.name == 'Cash Flow':
            return self._get_cash_flow()
        elif self.name == 'ROI':
            return self._get_roi()
        
        return 0.0
    
    def _calculate_inventory_kpi(self):
        """Calculate inventory-specific KPI"""
        if self.name == 'Total Products':
            return self._get_total_products()
        elif self.name == 'Low Stock Items':
            return self._get_low_stock_items()
        elif self.name == 'Stock Value':
            return self._get_stock_value()
        elif self.name == 'Turnover Rate':
            return self._get_turnover_rate()
        
        return 0.0
    
    def _calculate_crm_kpi(self):
        """Calculate CRM-specific KPI"""
        if self.name == 'Total Leads':
            return self._get_total_leads()
        elif self.name == 'Conversion Rate':
            return self._get_conversion_rate()
        elif self.name == 'Pipeline Value':
            return self._get_pipeline_value()
        elif self.name == 'Customer Acquisition':
            return self._get_customer_acquisition()
        
        return 0.0
    
    def _get_domain(self):
        """Get domain for KPI calculation"""
        domain = []
        
        # Add custom domain if specified
        if self.domain:
            try:
                domain = eval(self.domain)
            except:
                _logger.warning(f"Invalid domain for KPI {self.name}: {self.domain}")
        
        # Add date filter based on period type
        date_from, date_to = self._get_date_range()
        if self.model_name == 'sale.order':
            domain.extend([
                ('date_order', '>=', date_from),
                ('date_order', '<=', date_to),
                ('state', 'in', ['sale', 'done']),
            ])
        elif self.model_name == 'crm.lead':
            domain.extend([
                ('create_date', '>=', date_from),
                ('create_date', '<=', date_to),
            ])
        elif self.model_name == 'account.move':
            domain.extend([
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('state', '=', 'posted'),
            ])
        
        return domain
    
    def _get_base_domain(self):
        """Get base domain for percentage calculations"""
        domain = []
        date_from, date_to = self._get_date_range()
        
        if self.model_name == 'sale.order':
            domain.extend([
                ('date_order', '>=', date_from),
                ('date_order', '<=', date_to),
            ])
        elif self.model_name == 'crm.lead':
            domain.extend([
                ('create_date', '>=', date_from),
                ('create_date', '<=', date_to),
            ])
        
        return domain
    
    def _get_date_range(self):
        """Get date range based on period type"""
        today = fields.Date.today()
        
        if self.period_type == 'daily':
            return today, today
        elif self.period_type == 'weekly':
            start = today - timedelta(days=today.weekday())
            return start, today
        elif self.period_type == 'monthly':
            start = today.replace(day=1)
            return start, today
        elif self.period_type == 'quarterly':
            quarter = (today.month - 1) // 3 + 1
            start = today.replace(month=(quarter - 1) * 3 + 1, day=1)
            return start, today
        elif self.period_type == 'yearly':
            start = today.replace(month=1, day=1)
            return start, today
        elif self.period_type == 'custom':
            start = today - timedelta(days=self.period_days)
            return start, today
        
        return today, today
    
    # Sales KPI Methods
    def _get_total_sales(self):
        """Get total sales amount"""
        orders = self.env['sale.order'].search(self._get_domain())
        return sum(orders.mapped('amount_total'))
    
    def _get_average_order_value(self):
        """Get average order value"""
        orders = self.env['sale.order'].search(self._get_domain())
        if not orders:
            return 0.0
        return sum(orders.mapped('amount_total')) / len(orders)
    
    def _get_number_of_orders(self):
        """Get number of orders"""
        return self.env['sale.order'].search_count(self._get_domain())
    
    def _get_sales_growth_rate(self):
        """Get sales growth rate"""
        current_sales = self._get_total_sales()
        
        # Get previous period sales
        date_from, date_to = self._get_date_range()
        period_days = (date_to - date_from).days
        prev_date_from = date_from - timedelta(days=period_days)
        prev_date_to = date_from
        
        prev_orders = self.env['sale.order'].search([
            ('date_order', '>=', prev_date_from),
            ('date_order', '<=', prev_date_to),
            ('state', 'in', ['sale', 'done']),
        ])
        prev_sales = sum(prev_orders.mapped('amount_total'))
        
        if prev_sales == 0:
            return 0.0
        
        return ((current_sales - prev_sales) / prev_sales) * 100
    
    def _get_top_customer_value(self):
        """Get top customer sales value"""
        orders = self.env['sale.order'].search(self._get_domain())
        customer_sales = {}
        
        for order in orders:
            customer = order.partner_id
            if customer.id not in customer_sales:
                customer_sales[customer.id] = 0
            customer_sales[customer.id] += order.amount_total
        
        if not customer_sales:
            return 0.0
        
        return max(customer_sales.values())
    
    # Financial KPI Methods
    def _get_profit_margin(self):
        """Get profit margin percentage"""
        revenue = self._get_total_sales()
        # Simplified calculation - in real implementation, you'd calculate actual costs
        costs = revenue * 0.7  # Assume 70% costs
        profit = revenue - costs
        
        if revenue == 0:
            return 0.0
        
        return (profit / revenue) * 100
    
    def _get_cash_flow(self):
        """Get cash flow amount"""
        # Simplified cash flow calculation
        return self._get_total_sales() * 0.8  # Assume 80% of sales as cash flow
    
    def _get_roi(self):
        """Get return on investment"""
        # Simplified ROI calculation
        investment = 100000  # Assume fixed investment
        profit = self._get_total_sales() * 0.3  # Assume 30% profit margin
        
        if investment == 0:
            return 0.0
        
        return (profit / investment) * 100
    
    # Inventory KPI Methods
    def _get_total_products(self):
        """Get total number of products"""
        return self.env['product.product'].search_count([('type', '=', 'product')])
    
    def _get_low_stock_items(self):
        """Get number of low stock items"""
        return self.env['product.product'].search_count([
            ('type', '=', 'product'),
            ('qty_available', '<', 10),
        ])
    
    def _get_stock_value(self):
        """Get total stock value"""
        products = self.env['product.product'].search([('type', '=', 'product')])
        return sum(products.mapped(lambda p: p.qty_available * p.standard_price))
    
    def _get_turnover_rate(self):
        """Get inventory turnover rate"""
        # Simplified turnover rate calculation
        stock_value = self._get_stock_value()
        sales = self._get_total_sales()
        
        if stock_value == 0:
            return 0.0
        
        return sales / stock_value
    
    # CRM KPI Methods
    def _get_total_leads(self):
        """Get total number of leads"""
        return self.env['crm.lead'].search_count(self._get_domain())
    
    def _get_conversion_rate(self):
        """Get lead conversion rate"""
        total_leads = self.env['crm.lead'].search_count(self._get_base_domain())
        won_leads = self.env['crm.lead'].search_count([
            ('stage_id.name', '=', 'Won'),
        ] + self._get_base_domain())
        
        if total_leads == 0:
            return 0.0
        
        return (won_leads / total_leads) * 100
    
    def _get_pipeline_value(self):
        """Get total pipeline value"""
        opportunities = self.env['crm.lead'].search([
            ('type', '=', 'opportunity'),
            ('probability', '>', 0),
        ] + self._get_domain())
        
        return sum(opportunities.mapped('expected_revenue'))
    
    def _get_customer_acquisition(self):
        """Get number of new customers"""
        return self.env['res.partner'].search_count([
            ('create_date', '>=', self._get_date_range()[0]),
            ('create_date', '<=', self._get_date_range()[1]),
            ('is_company', '=', True),
        ])
    
    def get_previous_value(self):
        """Get previous period value for comparison"""
        if not self.compare_previous:
            return 0.0
        
        # Get previous period date range
        date_from, date_to = self._get_date_range()
        period_days = (date_to - date_from).days
        prev_date_from = date_from - timedelta(days=period_days)
        prev_date_to = date_from
        
        # Temporarily update the period for calculation
        original_period_type = self.period_type
        self.period_type = 'custom'
        self.period_days = period_days
        
        # Calculate previous value
        prev_value = self._calculate_standard_value()
        
        # Restore original period type
        self.period_type = original_period_type
        
        return prev_value
    
    def get_change_percent(self):
        """Get percentage change from previous period"""
        current_value = self.get_current_value()
        previous_value = self.get_previous_value()
        
        if previous_value == 0:
            return 0.0
        
        return ((current_value - previous_value) / previous_value) * 100
    
    def get_trend(self):
        """Get trend direction"""
        change_percent = self.get_change_percent()
        
        if change_percent > 5:
            return 'up'
        elif change_percent < -5:
            return 'down'
        else:
            return 'stable'
    
    def format_value(self, value):
        """Format value according to number format"""
        if self.number_format == 'integer':
            return f"{int(value):,}"
        elif self.number_format == 'decimal':
            return f"{value:,.{self.decimal_places}f}"
        elif self.number_format == 'currency':
            return f"{self.currency_id.symbol}{value:,.{self.decimal_places}f}"
        elif self.number_format == 'percentage':
            return f"{value:.{self.decimal_places}f}%"
        
        return str(value)
    
    @api.model
    def create_default_kpis(self):
        """Create default KPIs for each dashboard type"""
        # Sales KPIs
        sales_dashboard = self.env['analytics.dashboard'].search([('dashboard_type', '=', 'sales')], limit=1)
        if sales_dashboard:
            sales_kpis = [
                {
                    'name': 'Total Sales',
                    'description': 'Total sales amount for the period',
                    'dashboard_id': sales_dashboard.id,
                    'kpi_type': 'sales',
                    'calculation_method': 'custom',
                    'color': 'primary',
                    'icon': 'fa fa-dollar-sign',
                    'number_format': 'currency',
                },
                {
                    'name': 'Average Order Value',
                    'description': 'Average value per order',
                    'dashboard_id': sales_dashboard.id,
                    'kpi_type': 'sales',
                    'calculation_method': 'custom',
                    'color': 'success',
                    'icon': 'fa fa-chart-line',
                    'number_format': 'currency',
                },
                {
                    'name': 'Number of Orders',
                    'description': 'Total number of orders',
                    'dashboard_id': sales_dashboard.id,
                    'kpi_type': 'sales',
                    'calculation_method': 'custom',
                    'color': 'info',
                    'icon': 'fa fa-shopping-cart',
                    'number_format': 'integer',
                },
                {
                    'name': 'Sales Growth Rate',
                    'description': 'Sales growth compared to previous period',
                    'dashboard_id': sales_dashboard.id,
                    'kpi_type': 'sales',
                    'calculation_method': 'custom',
                    'color': 'warning',
                    'icon': 'fa fa-trending-up',
                    'number_format': 'percentage',
                },
            ]
            
            for kpi_data in sales_kpis:
                if not self.search([('name', '=', kpi_data['name'])]):
                    self.create(kpi_data)
        
        # Financial KPIs
        financial_dashboard = self.env['analytics.dashboard'].search([('dashboard_type', '=', 'financial')], limit=1)
        if financial_dashboard:
            financial_kpis = [
                {
                    'name': 'Revenue',
                    'description': 'Total revenue for the period',
                    'dashboard_id': financial_dashboard.id,
                    'kpi_type': 'financial',
                    'calculation_method': 'custom',
                    'color': 'primary',
                    'icon': 'fa fa-chart-bar',
                    'number_format': 'currency',
                },
                {
                    'name': 'Profit Margin',
                    'description': 'Profit margin percentage',
                    'dashboard_id': financial_dashboard.id,
                    'kpi_type': 'financial',
                    'calculation_method': 'custom',
                    'color': 'success',
                    'icon': 'fa fa-percentage',
                    'number_format': 'percentage',
                },
                {
                    'name': 'Cash Flow',
                    'description': 'Cash flow amount',
                    'dashboard_id': financial_dashboard.id,
                    'kpi_type': 'financial',
                    'calculation_method': 'custom',
                    'color': 'info',
                    'icon': 'fa fa-money-bill-wave',
                    'number_format': 'currency',
                },
            ]
            
            for kpi_data in financial_kpis:
                if not self.search([('name', '=', kpi_data['name'])]):
                    self.create(kpi_data)
        
        # Inventory KPIs
        inventory_dashboard = self.env['analytics.dashboard'].search([('dashboard_type', '=', 'inventory')], limit=1)
        if inventory_dashboard:
            inventory_kpis = [
                {
                    'name': 'Total Products',
                    'description': 'Total number of products in inventory',
                    'dashboard_id': inventory_dashboard.id,
                    'kpi_type': 'inventory',
                    'calculation_method': 'custom',
                    'color': 'primary',
                    'icon': 'fa fa-boxes',
                    'number_format': 'integer',
                },
                {
                    'name': 'Low Stock Items',
                    'description': 'Number of items with low stock',
                    'dashboard_id': inventory_dashboard.id,
                    'kpi_type': 'inventory',
                    'calculation_method': 'custom',
                    'color': 'danger',
                    'icon': 'fa fa-exclamation-triangle',
                    'number_format': 'integer',
                },
                {
                    'name': 'Stock Value',
                    'description': 'Total value of inventory',
                    'dashboard_id': inventory_dashboard.id,
                    'kpi_type': 'inventory',
                    'calculation_method': 'custom',
                    'color': 'success',
                    'icon': 'fa fa-dollar-sign',
                    'number_format': 'currency',
                },
            ]
            
            for kpi_data in inventory_kpis:
                if not self.search([('name', '=', kpi_data['name'])]):
                    self.create(kpi_data)
        
        # CRM KPIs
        crm_dashboard = self.env['analytics.dashboard'].search([('dashboard_type', '=', 'crm')], limit=1)
        if crm_dashboard:
            crm_kpis = [
                {
                    'name': 'Total Leads',
                    'description': 'Total number of leads',
                    'dashboard_id': crm_dashboard.id,
                    'kpi_type': 'crm',
                    'calculation_method': 'custom',
                    'color': 'primary',
                    'icon': 'fa fa-users',
                    'number_format': 'integer',
                },
                {
                    'name': 'Conversion Rate',
                    'description': 'Lead conversion rate percentage',
                    'dashboard_id': crm_dashboard.id,
                    'kpi_type': 'crm',
                    'calculation_method': 'custom',
                    'color': 'success',
                    'icon': 'fa fa-percentage',
                    'number_format': 'percentage',
                },
                {
                    'name': 'Pipeline Value',
                    'description': 'Total value of sales pipeline',
                    'dashboard_id': crm_dashboard.id,
                    'kpi_type': 'crm',
                    'calculation_method': 'custom',
                    'color': 'info',
                    'icon': 'fa fa-chart-line',
                    'number_format': 'currency',
                },
            ]
            
            for kpi_data in crm_kpis:
                if not self.search([('name', '=', kpi_data['name'])]):
                    self.create(kpi_data)




