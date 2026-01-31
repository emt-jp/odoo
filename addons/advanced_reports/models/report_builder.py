# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json

_logger = logging.getLogger(__name__)


class ReportBuilder(models.Model):
    _name = 'report.builder'
    _description = 'Report Builder'
    _order = 'sequence, name'
    
    name = fields.Char('Report Name', required=True, translate=True)
    description = fields.Text('Description', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    
    # Report configuration
    report_type = fields.Selection([
        ('financial', 'Financial Report'),
        ('sales', 'Sales Report'),
        ('inventory', 'Inventory Report'),
        ('crm', 'CRM Report'),
        ('custom', 'Custom Report'),
    ], string='Report Type', required=True)
    
    # Data source
    model_name = fields.Char('Model Name', required=True)
    domain = fields.Text('Domain', help='Domain filter for report data')
    
    # Fields configuration
    field_config = fields.Text('Field Configuration', help='JSON configuration for fields')
    
    # Grouping and aggregation
    group_by_fields = fields.Text('Group By Fields', help='Comma-separated list of fields to group by')
    aggregate_fields = fields.Text('Aggregate Fields', help='JSON configuration for aggregate fields')
    
    # Filtering
    filter_config = fields.Text('Filter Configuration', help='JSON configuration for filters')
    
    # Display options
    chart_type = fields.Selection([
        ('table', 'Table'),
        ('line', 'Line Chart'),
        ('bar', 'Bar Chart'),
        ('pie', 'Pie Chart'),
        ('area', 'Area Chart'),
        ('scatter', 'Scatter Plot'),
        ('funnel', 'Funnel Chart'),
        ('gauge', 'Gauge Chart'),
    ], string='Chart Type', default='table')
    
    chart_config = fields.Text('Chart Configuration', help='JSON configuration for charts')
    
    # Time period
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    period_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    ], string='Period Type', default='monthly')
    
    # Enterprise features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    # Access control
    user_ids = fields.Many2many('res.users', string='Allowed Users')
    group_ids = fields.Many2many('res.groups', string='Allowed Groups')
    
    # Report generation
    last_generated = fields.Datetime('Last Generated')
    generation_count = fields.Integer('Generation Count', default=0)

    def action_generate_report(self):
        """Action to generate the report"""
        self.ensure_one()
        return self.generate_report(report_id=self.id)

    def action_preview_report(self):
        """Action to preview the report"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Preview - {self.name}',
            'res_model': 'report.builder',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_export_pdf(self):
        """Action to export report to PDF"""
        self.ensure_one()
        # Placeholder for PDF export
        return True

    def action_export_excel(self):
        """Action to export report to Excel"""
        self.ensure_one()
        # Placeholder for Excel export
        return True

    def action_view_history(self):
        """Action to view report generation history"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'History - {self.name}',
            'res_model': 'report.builder',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def generate_report(self, report_id=None, context=None):
        """Generate report data"""
        if not self._is_enterprise_available():
            raise UserError(_("Advanced reporting requires the Enterprise edition."))
        
        report = self.browse(report_id) if report_id else self.search([('active', '=', True)], limit=1)
        if not report:
            raise UserError(_("No active report found."))
        
        # Update context
        if context:
            self = self.with_context(**context)
        
        # Generate report data
        data = report._get_report_data()
        
        # Update generation info
        report.write({
            'last_generated': fields.Datetime.now(),
            'generation_count': report.generation_count + 1,
        })
        
        return {
            'report': report.read()[0],
            'data': data,
            'chart_config': report._get_chart_config(),
            'filters': report._get_available_filters(),
        }
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    def _get_report_data(self):
        """Get report data based on configuration"""
        model = self.env[self.model_name]
        domain = self._get_domain()
        
        # Get field configuration
        field_config = self._get_field_config()
        
        # Get group by fields
        group_by_fields = self._get_group_by_fields()
        
        # Get aggregate fields
        aggregate_fields = self._get_aggregate_fields()
        
        if group_by_fields:
            # Group by specified fields
            return self._get_grouped_data(model, domain, field_config, group_by_fields, aggregate_fields)
        else:
            # Simple data retrieval
            return self._get_simple_data(model, domain, field_config)
    
    def _get_domain(self):
        """Get domain for report data"""
        domain = []
        
        # Add custom domain if specified
        if self.domain:
            try:
                domain = eval(self.domain)
            except:
                _logger.warning(f"Invalid domain for report {self.name}: {self.domain}")
        
        # Add date filter if dates are specified
        if self.date_from and self.date_to:
            date_field = self._get_date_field()
            if date_field:
                domain.extend([
                    (date_field, '>=', self.date_from),
                    (date_field, '<=', self.date_to),
                ])
        
        return domain
    
    def _get_date_field(self):
        """Get the appropriate date field for the model"""
        date_fields = {
            'sale.order': 'date_order',
            'crm.lead': 'create_date',
            'account.move': 'date',
            'stock.move': 'date',
            'purchase.order': 'date_order',
        }
        return date_fields.get(self.model_name, 'create_date')
    
    def _get_field_config(self):
        """Get field configuration"""
        if not self.field_config:
            return []
        
        try:
            return json.loads(self.field_config)
        except:
            _logger.warning(f"Invalid field configuration for report {self.name}")
            return []
    
    def _get_group_by_fields(self):
        """Get group by fields"""
        if not self.group_by_fields:
            return []
        
        return [f.strip() for f in self.group_by_fields.split(',')]
    
    def _get_aggregate_fields(self):
        """Get aggregate fields configuration"""
        if not self.aggregate_fields:
            return []
        
        try:
            return json.loads(self.aggregate_fields)
        except:
            _logger.warning(f"Invalid aggregate configuration for report {self.name}")
            return []
    
    def _get_simple_data(self, model, domain, field_config):
        """Get simple report data without grouping"""
        records = model.search(domain)
        
        if not field_config:
            # Return basic record data
            return [record.read() for record in records]
        
        # Return configured fields
        data = []
        for record in records:
            record_data = {'id': record.id}
            for field_config_item in field_config:
                field_name = field_config_item.get('field_name')
                field_label = field_config_item.get('label', field_name)
                field_type = field_config_item.get('type', 'string')
                
                if field_name and hasattr(record, field_name):
                    value = getattr(record, field_name)
                    record_data[field_label] = self._format_field_value(value, field_type)
            
            data.append(record_data)
        
        return data
    
    def _get_grouped_data(self, model, domain, field_config, group_by_fields, aggregate_fields):
        """Get grouped report data"""
        records = model.search(domain)
        
        # Group records by specified fields
        grouped_data = {}
        for record in records:
            group_key = self._get_group_key(record, group_by_fields)
            if group_key not in grouped_data:
                grouped_data[group_key] = []
            grouped_data[group_key].append(record)
        
        # Process grouped data
        result = []
        for group_key, group_records in grouped_data.items():
            group_data = {'group_key': group_key, 'count': len(group_records)}
            
            # Add field values
            for field_config_item in field_config:
                field_name = field_config_item.get('field_name')
                field_label = field_config_item.get('label', field_name)
                field_type = field_config_item.get('type', 'string')
                
                if field_name:
                    values = [getattr(record, field_name) for record in group_records if hasattr(record, field_name)]
                    if values:
                        if field_type in ['integer', 'float', 'monetary']:
                            group_data[field_label] = sum(values)
                        else:
                            group_data[field_label] = values[0]  # Take first value for non-numeric fields
            
            # Add aggregate fields
            for aggregate_field in aggregate_fields:
                field_name = aggregate_field.get('field_name')
                aggregate_type = aggregate_field.get('type', 'sum')
                field_label = aggregate_field.get('label', f"{aggregate_type}_{field_name}")
                
                if field_name:
                    values = [getattr(record, field_name) for record in group_records if hasattr(record, field_name)]
                    if values:
                        if aggregate_type == 'sum':
                            group_data[field_label] = sum(values)
                        elif aggregate_type == 'avg':
                            group_data[field_label] = sum(values) / len(values)
                        elif aggregate_type == 'count':
                            group_data[field_label] = len(values)
                        elif aggregate_type == 'min':
                            group_data[field_label] = min(values)
                        elif aggregate_type == 'max':
                            group_data[field_label] = max(values)
            
            result.append(group_data)
        
        return result
    
    def _get_group_key(self, record, group_by_fields):
        """Get group key for record"""
        key_parts = []
        for field_name in group_by_fields:
            if hasattr(record, field_name):
                value = getattr(record, field_name)
                if hasattr(value, 'name'):
                    key_parts.append(str(value.name))
                else:
                    key_parts.append(str(value))
        return ' - '.join(key_parts)
    
    def _format_field_value(self, value, field_type):
        """Format field value according to type"""
        if field_type == 'integer':
            return int(value) if value else 0
        elif field_type == 'float':
            return float(value) if value else 0.0
        elif field_type == 'monetary':
            return float(value) if value else 0.0
        elif field_type == 'date':
            return value.strftime('%Y-%m-%d') if value else ''
        elif field_type == 'datetime':
            return value.strftime('%Y-%m-%d %H:%M:%S') if value else ''
        else:
            return str(value) if value else ''
    
    def _get_chart_config(self):
        """Get chart configuration"""
        if not self.chart_config:
            return {
                'type': self.chart_type,
                'title': self.name,
                'x_axis': 'group_key',
                'y_axis': 'count',
            }
        
        try:
            config = json.loads(self.chart_config)
            config['type'] = self.chart_type
            return config
        except:
            return {
                'type': self.chart_type,
                'title': self.name,
                'x_axis': 'group_key',
                'y_axis': 'count',
            }
    
    def _get_available_filters(self):
        """Get available filters for the report"""
        if not self.filter_config:
            return []
        
        try:
            return json.loads(self.filter_config)
        except:
            return []
    
    @api.model
    def create_default_reports(self):
        """Create default reports"""
        reports = [
            {
                'name': 'Sales Performance Report',
                'description': 'Comprehensive sales performance analysis',
                'report_type': 'sales',
                'model_name': 'sale.order',
                'field_config': json.dumps([
                    {'field_name': 'name', 'label': 'Order Number', 'type': 'string'},
                    {'field_name': 'date_order', 'label': 'Order Date', 'type': 'date'},
                    {'field_name': 'partner_id', 'label': 'Customer', 'type': 'string'},
                    {'field_name': 'amount_total', 'label': 'Total Amount', 'type': 'monetary'},
                    {'field_name': 'state', 'label': 'Status', 'type': 'string'},
                ]),
                'group_by_fields': 'partner_id',
                'aggregate_fields': json.dumps([
                    {'field_name': 'amount_total', 'type': 'sum', 'label': 'Total Sales'},
                    {'field_name': 'amount_total', 'type': 'avg', 'label': 'Average Order Value'},
                ]),
                'chart_type': 'bar',
                'domain': "[('state', 'in', ['sale', 'done'])]",
            },
            {
                'name': 'Financial Summary Report',
                'description': 'Financial performance summary',
                'report_type': 'financial',
                'model_name': 'account.move',
                'field_config': json.dumps([
                    {'field_name': 'name', 'label': 'Invoice Number', 'type': 'string'},
                    {'field_name': 'date', 'label': 'Date', 'type': 'date'},
                    {'field_name': 'partner_id', 'label': 'Customer', 'type': 'string'},
                    {'field_name': 'amount_total', 'label': 'Amount', 'type': 'monetary'},
                    {'field_name': 'state', 'label': 'Status', 'type': 'string'},
                ]),
                'group_by_fields': 'partner_id',
                'chart_type': 'pie',
                'domain': "[('state', '=', 'posted')]",
            },
            {
                'name': 'Lead Conversion Report',
                'description': 'Lead conversion analysis',
                'report_type': 'crm',
                'model_name': 'crm.lead',
                'field_config': json.dumps([
                    {'field_name': 'name', 'label': 'Lead Name', 'type': 'string'},
                    {'field_name': 'stage_id', 'label': 'Stage', 'type': 'string'},
                    {'field_name': 'expected_revenue', 'label': 'Expected Revenue', 'type': 'monetary'},
                    {'field_name': 'probability', 'label': 'Probability', 'type': 'integer'},
                ]),
                'group_by_fields': 'stage_id',
                'chart_type': 'funnel',
                'domain': "[]",
            },
            {
                'name': 'Inventory Valuation Report',
                'description': 'Inventory valuation analysis',
                'report_type': 'inventory',
                'model_name': 'product.product',
                'field_config': json.dumps([
                    {'field_name': 'name', 'label': 'Product Name', 'type': 'string'},
                    {'field_name': 'qty_available', 'label': 'Quantity Available', 'type': 'integer'},
                    {'field_name': 'standard_price', 'label': 'Standard Price', 'type': 'monetary'},
                    {'field_name': 'categ_id', 'label': 'Category', 'type': 'string'},
                ]),
                'group_by_fields': 'categ_id',
                'aggregate_fields': json.dumps([
                    {'field_name': 'qty_available', 'type': 'sum', 'label': 'Total Quantity'},
                    {'field_name': 'standard_price', 'type': 'avg', 'label': 'Average Price'},
                ]),
                'chart_type': 'bar',
                'domain': "[('type', '=', 'product')]",
            },
        ]
        
        for report_data in reports:
            if not self.search([('name', '=', report_data['name'])]):
                self.create(report_data)
    
    @api.model
    def get_report_categories(self):
        """Get available report categories"""
        return [
            {'id': 'financial', 'name': 'Financial Reports', 'icon': 'fa fa-chart-line'},
            {'id': 'sales', 'name': 'Sales Reports', 'icon': 'fa fa-shopping-cart'},
            {'id': 'inventory', 'name': 'Inventory Reports', 'icon': 'fa fa-boxes'},
            {'id': 'crm', 'name': 'CRM Reports', 'icon': 'fa fa-users'},
            {'id': 'custom', 'name': 'Custom Reports', 'icon': 'fa fa-cog'},
        ]
    
    @api.model
    def get_available_models(self):
        """Get available models for report building"""
        return [
            {'id': 'sale.order', 'name': 'Sales Orders'},
            {'id': 'account.move', 'name': 'Invoices'},
            {'id': 'crm.lead', 'name': 'Leads'},
            {'id': 'res.partner', 'name': 'Partners'},
            {'id': 'product.product', 'name': 'Products'},
            {'id': 'stock.move', 'name': 'Stock Moves'},
            {'id': 'purchase.order', 'name': 'Purchase Orders'},
        ]
    
    @api.model
    def get_field_types(self):
        """Get available field types for report building"""
        return [
            {'id': 'string', 'name': 'Text'},
            {'id': 'integer', 'name': 'Integer'},
            {'id': 'float', 'name': 'Float'},
            {'id': 'monetary', 'name': 'Monetary'},
            {'id': 'date', 'name': 'Date'},
            {'id': 'datetime', 'name': 'DateTime'},
            {'id': 'boolean', 'name': 'Boolean'},
        ]
    
    @api.model
    def get_aggregate_types(self):
        """Get available aggregate types"""
        return [
            {'id': 'sum', 'name': 'Sum'},
            {'id': 'avg', 'name': 'Average'},
            {'id': 'count', 'name': 'Count'},
            {'id': 'min', 'name': 'Minimum'},
            {'id': 'max', 'name': 'Maximum'},
        ]
    
    @api.model
    def get_chart_types(self):
        """Get available chart types"""
        return [
            {'id': 'table', 'name': 'Table', 'icon': 'fa fa-table'},
            {'id': 'line', 'name': 'Line Chart', 'icon': 'fa fa-chart-line'},
            {'id': 'bar', 'name': 'Bar Chart', 'icon': 'fa fa-chart-bar'},
            {'id': 'pie', 'name': 'Pie Chart', 'icon': 'fa fa-chart-pie'},
            {'id': 'area', 'name': 'Area Chart', 'icon': 'fa fa-chart-area'},
            {'id': 'scatter', 'name': 'Scatter Plot', 'icon': 'fa fa-chart-scatter'},
            {'id': 'funnel', 'name': 'Funnel Chart', 'icon': 'fa fa-funnel'},
            {'id': 'gauge', 'name': 'Gauge Chart', 'icon': 'fa fa-tachometer-alt'},
        ]




