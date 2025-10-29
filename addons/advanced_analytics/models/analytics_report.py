# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class AnalyticsReport(models.Model):
    _name = 'analytics.report'
    _description = 'Analytics Report'
    _order = 'sequence, name'
    
    name = fields.Char('Report Name', required=True, translate=True)
    description = fields.Text('Description', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    
    # Report configuration
    report_type = fields.Selection([
        ('sales', 'Sales Report'),
        ('financial', 'Financial Report'),
        ('inventory', 'Inventory Report'),
        ('crm', 'CRM Report'),
        ('custom', 'Custom Report'),
    ], string='Report Type', required=True)
    
    # Data configuration
    model_name = fields.Char('Model Name', required=True)
    field_names = fields.Text('Field Names', help='Comma-separated list of fields to include')
    group_by_fields = fields.Text('Group By Fields', help='Comma-separated list of fields to group by')
    domain = fields.Text('Domain', help='Domain filter for report data')
    
    # Display configuration
    chart_type = fields.Selection([
        ('table', 'Table'),
        ('line', 'Line Chart'),
        ('bar', 'Bar Chart'),
        ('pie', 'Pie Chart'),
        ('area', 'Area Chart'),
        ('scatter', 'Scatter Plot'),
    ], string='Chart Type', default='table')
    
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
    
    @api.model
    def generate_report(self, report_id=None, date_from=None, date_to=None):
        """Generate report data"""
        if not self._is_enterprise_available():
            raise UserError(_("Advanced reporting requires the Enterprise edition."))
        
        report = self.browse(report_id) if report_id else self.search([('active', '=', True)], limit=1)
        if not report:
            raise UserError(_("No active report found."))
        
        # Use provided dates or report's default dates
        if date_from:
            report.date_from = date_from
        if date_to:
            report.date_to = date_to
        
        return {
            'report': report.read()[0],
            'data': report._get_report_data(),
            'chart_config': report._get_chart_config(),
        }
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return self.env.context.get('is_enterprise', True)
    
    def _get_report_data(self):
        """Get report data based on configuration"""
        model = self.env[self.model_name]
        domain = self._get_domain()
        
        # Get field names
        field_names = [f.strip() for f in self.field_names.split(',')] if self.field_names else []
        
        # Get group by fields
        group_by_fields = [f.strip() for f in self.group_by_fields.split(',')] if self.group_by_fields else []
        
        if group_by_fields:
            # Group by specified fields
            return self._get_grouped_data(model, domain, field_names, group_by_fields)
        else:
            # Simple data retrieval
            return self._get_simple_data(model, domain, field_names)
    
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
            if self.model_name == 'sale.order':
                domain.extend([
                    ('date_order', '>=', self.date_from),
                    ('date_order', '<=', self.date_to),
                ])
            elif self.model_name == 'crm.lead':
                domain.extend([
                    ('create_date', '>=', self.date_from),
                    ('create_date', '<=', self.date_to),
                ])
            elif self.model_name == 'account.move':
                domain.extend([
                    ('date', '>=', self.date_from),
                    ('date', '<=', self.date_to),
                ])
        
        return domain
    
    def _get_simple_data(self, model, domain, field_names):
        """Get simple report data without grouping"""
        records = model.search(domain)
        
        if not field_names:
            # Return basic record data
            return [record.read() for record in records]
        
        # Return specific fields
        data = []
        for record in records:
            record_data = {'id': record.id}
            for field_name in field_names:
                if hasattr(record, field_name):
                    record_data[field_name] = getattr(record, field_name)
            data.append(record_data)
        
        return data
    
    def _get_grouped_data(self, model, domain, field_names, group_by_fields):
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
            for field_name in field_names:
                if field_name:
                    values = [getattr(record, field_name) for record in group_records if hasattr(record, field_name)]
                    if values:
                        if isinstance(values[0], (int, float)):
                            group_data[field_name] = sum(values)
                        else:
                            group_data[field_name] = values[0]  # Take first value for non-numeric fields
            
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
    
    def _get_chart_config(self):
        """Get chart configuration"""
        return {
            'type': self.chart_type,
            'title': self.name,
            'x_axis': self.group_by_fields.split(',')[0].strip() if self.group_by_fields else 'id',
            'y_axis': self.field_names.split(',')[0].strip() if self.field_names else 'id',
        }
    
    @api.model
    def create_default_reports(self):
        """Create default reports"""
        reports = [
            {
                'name': 'Sales Performance Report',
                'description': 'Detailed sales performance analysis',
                'report_type': 'sales',
                'model_name': 'sale.order',
                'field_names': 'name,date_order,partner_id,amount_total,state',
                'group_by_fields': 'partner_id',
                'chart_type': 'bar',
                'domain': "[('state', 'in', ['sale', 'done'])]",
            },
            {
                'name': 'Lead Conversion Report',
                'description': 'Lead conversion analysis',
                'report_type': 'crm',
                'model_name': 'crm.lead',
                'field_names': 'name,stage_id,expected_revenue,probability',
                'group_by_fields': 'stage_id',
                'chart_type': 'pie',
                'domain': "[]",
            },
            {
                'name': 'Product Performance Report',
                'description': 'Product sales performance',
                'report_type': 'sales',
                'model_name': 'sale.order.line',
                'field_names': 'product_id,product_uom_qty,price_subtotal',
                'group_by_fields': 'product_id',
                'chart_type': 'bar',
                'domain': "[('order_id.state', 'in', ['sale', 'done'])]",
            },
            {
                'name': 'Customer Analysis Report',
                'description': 'Customer behavior analysis',
                'report_type': 'sales',
                'model_name': 'res.partner',
                'field_names': 'name,is_company,create_date',
                'group_by_fields': 'is_company',
                'chart_type': 'pie',
                'domain': "[]",
            },
        ]
        
        for report_data in reports:
            if not self.search([('name', '=', report_data['name'])]):
                self.create(report_data)




