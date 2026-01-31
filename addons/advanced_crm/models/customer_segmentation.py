# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class CustomerSegmentation(models.Model):
    _name = 'customer.segmentation'
    _description = 'Customer Segmentation'
    _order = 'sequence, name'
    
    name = fields.Char('Segment Name', required=True, translate=True)
    description = fields.Text('Description', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    
    # Segmentation criteria
    segment_type = fields.Selection([
        ('demographic', 'Demographic'),
        ('behavioral', 'Behavioral'),
        ('geographic', 'Geographic'),
        ('psychographic', 'Psychographic'),
        ('value_based', 'Value Based'),
        ('custom', 'Custom'),
    ], string='Segment Type', required=True)
    
    # Criteria configuration
    criteria_rules = fields.One2many('customer.segmentation.rule', 'segment_id', string='Criteria Rules')
    domain = fields.Text('Domain', help='Domain filter for segment customers')
    auto_refresh = fields.Boolean('Auto Refresh', default=False, help='Automatically refresh segment customers')

    # Segment characteristics
    color = fields.Char('Color', default='#007bff', help='Color code for the segment')
    icon = fields.Char('Icon', default='fa fa-users', help='Icon for the segment')

    # Customers in segment
    partner_ids = fields.Many2many('res.partner', 'customer_segmentation_partner_rel', 'segment_id', 'partner_id', string='Customers')

    # Customer count
    customer_count = fields.Integer('Customer Count', compute='_compute_customer_count', store=True)
    
    # Enterprise features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.depends('criteria_rules', 'partner_ids')
    def _compute_customer_count(self):
        """Compute the number of customers in this segment"""
        for segment in self:
            if segment.partner_ids:
                segment.customer_count = len(segment.partner_ids)
            elif segment._is_enterprise_available():
                segment.customer_count = segment._get_customer_count()
            else:
                segment.customer_count = 0

    def action_refresh_segment(self):
        """Refresh the segment customers based on criteria"""
        self.ensure_one()
        customers = self._get_segment_customers()
        self.partner_ids = [(6, 0, customers.ids)]
        return True

    def action_view_customers(self):
        """View customers in this segment"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Customers - {self.name}',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.partner_ids.ids)],
            'context': {'default_customer_rank': 1},
        }
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    def _get_customer_count(self):
        """Get the number of customers in this segment"""
        customers = self._get_segment_customers()
        return len(customers)
    
    def _get_segment_customers(self):
        """Get customers that belong to this segment"""
        if not self.criteria_rules:
            return self.env['res.partner']
        
        # Start with all customers
        customers = self.env['res.partner'].search([
            ('is_company', '=', True),
            ('active', '=', True),
        ])
        
        # Apply each rule
        for rule in self.criteria_rules:
            if rule.active:
                customers = customers.filtered(lambda c: rule._evaluate_customer(c))
        
        return customers
    
    @api.model
    def assign_customers_to_segments(self):
        """Assign customers to segments based on criteria"""
        if not self._is_enterprise_available():
            return
        
        segments = self.search([('active', '=', True)])
        
        for segment in segments:
            customers = segment._get_segment_customers()
            # Update customer segment
            customers.write({'customer_segment_id': segment.id})
    
    @api.model
    def get_segment_analytics(self):
        """Get analytics for all segments"""
        if not self._is_enterprise_available():
            return {}
        
        segments = self.search([('active', '=', True)])
        analytics = {}
        
        for segment in segments:
            customers = segment._get_segment_customers()
            
            # Calculate segment metrics
            total_revenue = self._calculate_segment_revenue(customers)
            avg_order_value = self._calculate_avg_order_value(customers)
            customer_lifetime_value = self._calculate_customer_lifetime_value(customers)
            
            analytics[segment.id] = {
                'name': segment.name,
                'customer_count': len(customers),
                'total_revenue': total_revenue,
                'avg_order_value': avg_order_value,
                'customer_lifetime_value': customer_lifetime_value,
                'color': segment.color,
                'icon': segment.icon,
            }
        
        return analytics
    
    def _calculate_segment_revenue(self, customers):
        """Calculate total revenue for segment customers"""
        orders = self.env['sale.order'].search([
            ('partner_id', 'in', customers.ids),
            ('state', 'in', ['sale', 'done']),
        ])
        return sum(orders.mapped('amount_total'))
    
    def _calculate_avg_order_value(self, customers):
        """Calculate average order value for segment customers"""
        orders = self.env['sale.order'].search([
            ('partner_id', 'in', customers.ids),
            ('state', 'in', ['sale', 'done']),
        ])
        
        if not orders:
            return 0.0
        
        total_revenue = sum(orders.mapped('amount_total'))
        return total_revenue / len(orders)
    
    def _calculate_customer_lifetime_value(self, customers):
        """Calculate customer lifetime value for segment customers"""
        # Simplified CLV calculation
        total_revenue = self._calculate_segment_revenue(customers)
        customer_count = len(customers)
        
        if customer_count == 0:
            return 0.0
        
        return total_revenue / customer_count
    
    @api.model
    def create_default_segments(self):
        """Create default customer segments"""
        segments = [
            {
                'name': 'High Value Customers',
                'description': 'Customers with high revenue and frequent purchases',
                'segment_type': 'value_based',
                'color': '#28a745',
                'icon': 'fa fa-star',
                'sequence': 10,
            },
            {
                'name': 'New Customers',
                'description': 'Recently acquired customers',
                'segment_type': 'behavioral',
                'color': '#007bff',
                'icon': 'fa fa-user-plus',
                'sequence': 20,
            },
            {
                'name': 'At Risk Customers',
                'description': 'Customers with declining activity',
                'segment_type': 'behavioral',
                'color': '#dc3545',
                'icon': 'fa fa-exclamation-triangle',
                'sequence': 30,
            },
            {
                'name': 'Enterprise Customers',
                'description': 'Large enterprise customers',
                'segment_type': 'demographic',
                'color': '#6f42c1',
                'icon': 'fa fa-building',
                'sequence': 40,
            },
            {
                'name': 'SMB Customers',
                'description': 'Small and medium business customers',
                'segment_type': 'demographic',
                'color': '#fd7e14',
                'icon': 'fa fa-store',
                'sequence': 50,
            },
        ]
        
        for segment_data in segments:
            if not self.search([('name', '=', segment_data['name'])]):
                self.create(segment_data)
    
    @api.model
    def get_segment_recommendations(self, customer_id):
        """Get segment recommendations for a customer"""
        if not self._is_enterprise_available():
            return []
        
        customer = self.env['res.partner'].browse(customer_id)
        if not customer.exists():
            return []
        
        recommendations = []
        segments = self.search([('active', '=', True)])
        
        for segment in segments:
            score = segment._calculate_customer_score(customer)
            if score > 0.7:  # High match score
                recommendations.append({
                    'segment_id': segment.id,
                    'segment_name': segment.name,
                    'score': score,
                    'reason': segment._get_recommendation_reason(customer),
                })
        
        return sorted(recommendations, key=lambda x: x['score'], reverse=True)
    
    def _calculate_customer_score(self, customer):
        """Calculate how well a customer matches this segment"""
        if not self.criteria_rules:
            return 0.0
        
        total_score = 0.0
        rule_count = 0
        
        for rule in self.criteria_rules:
            if rule.active:
                if rule._evaluate_customer(customer):
                    total_score += 1.0
                rule_count += 1
        
        if rule_count == 0:
            return 0.0
        
        return total_score / rule_count
    
    def _get_recommendation_reason(self, customer):
        """Get reason why customer matches this segment"""
        reasons = []
        
        for rule in self.criteria_rules:
            if rule.active and rule._evaluate_customer(customer):
                reasons.append(rule.name)
        
        return ', '.join(reasons) if reasons else 'No specific criteria met'


class CustomerSegmentationRule(models.Model):
    _name = 'customer.segmentation.rule'
    _description = 'Customer Segmentation Rule'
    _order = 'sequence, name'
    
    name = fields.Char('Rule Name', required=True, translate=True)
    description = fields.Text('Description', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    
    # Rule configuration
    segment_id = fields.Many2one('customer.segmentation', string='Segment', required=True, ondelete='cascade')
    
    rule_type = fields.Selection([
        ('field_value', 'Field Value'),
        ('field_presence', 'Field Presence'),
        ('revenue_range', 'Revenue Range'),
        ('order_count', 'Order Count'),
        ('last_order_date', 'Last Order Date'),
        ('customer_age', 'Customer Age'),
        ('custom', 'Custom Logic'),
    ], string='Rule Type', required=True)
    
    # Field configuration
    field_name = fields.Char('Field Name', help='Field to evaluate')
    field_value = fields.Char('Field Value', help='Expected field value')
    operator = fields.Selection([
        ('equals', 'Equals'),
        ('not_equals', 'Not Equals'),
        ('contains', 'Contains'),
        ('not_contains', 'Not Contains'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
        ('is_empty', 'Is Empty'),
        ('is_not_empty', 'Is Not Empty'),
    ], string='Operator', default='equals')
    
    # Range configuration
    min_value = fields.Float('Minimum Value')
    max_value = fields.Float('Maximum Value')
    
    # Date configuration
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    
    # Custom logic
    custom_domain = fields.Text('Custom Domain', help='Custom domain for evaluation')
    
    def _evaluate_customer(self, customer):
        """Evaluate if customer matches this rule"""
        try:
            if self.rule_type == 'field_value':
                return self._evaluate_field_value(customer)
            elif self.rule_type == 'field_presence':
                return self._evaluate_field_presence(customer)
            elif self.rule_type == 'revenue_range':
                return self._evaluate_revenue_range(customer)
            elif self.rule_type == 'order_count':
                return self._evaluate_order_count(customer)
            elif self.rule_type == 'last_order_date':
                return self._evaluate_last_order_date(customer)
            elif self.rule_type == 'customer_age':
                return self._evaluate_customer_age(customer)
            elif self.rule_type == 'custom':
                return self._evaluate_custom_logic(customer)
        except Exception as e:
            _logger.error(f"Error evaluating segmentation rule {self.name}: {str(e)}")
            return False
        
        return False
    
    def _evaluate_field_value(self, customer):
        """Evaluate field value rule"""
        if not self.field_name or not hasattr(customer, self.field_name):
            return False
        
        field_value = getattr(customer, self.field_name)
        expected_value = self.field_value
        
        if self.operator == 'equals':
            return str(field_value) == str(expected_value)
        elif self.operator == 'not_equals':
            return str(field_value) != str(expected_value)
        elif self.operator == 'contains':
            return str(expected_value).lower() in str(field_value).lower()
        elif self.operator == 'not_contains':
            return str(expected_value).lower() not in str(field_value).lower()
        elif self.operator == 'greater_than':
            return float(field_value) > float(expected_value)
        elif self.operator == 'less_than':
            return float(field_value) < float(expected_value)
        elif self.operator == 'is_empty':
            return not field_value
        elif self.operator == 'is_not_empty':
            return bool(field_value)
        
        return False
    
    def _evaluate_field_presence(self, customer):
        """Evaluate field presence rule"""
        if not self.field_name or not hasattr(customer, self.field_name):
            return False
        
        field_value = getattr(customer, self.field_name)
        
        if self.operator == 'is_empty':
            return not field_value
        elif self.operator == 'is_not_empty':
            return bool(field_value)
        
        return False
    
    def _evaluate_revenue_range(self, customer):
        """Evaluate revenue range rule"""
        orders = self.env['sale.order'].search([
            ('partner_id', '=', customer.id),
            ('state', 'in', ['sale', 'done']),
        ])
        
        total_revenue = sum(orders.mapped('amount_total'))
        
        if self.min_value and total_revenue < self.min_value:
            return False
        
        if self.max_value and total_revenue > self.max_value:
            return False
        
        return True
    
    def _evaluate_order_count(self, customer):
        """Evaluate order count rule"""
        order_count = self.env['sale.order'].search_count([
            ('partner_id', '=', customer.id),
            ('state', 'in', ['sale', 'done']),
        ])
        
        if self.min_value and order_count < self.min_value:
            return False
        
        if self.max_value and order_count > self.max_value:
            return False
        
        return True
    
    def _evaluate_last_order_date(self, customer):
        """Evaluate last order date rule"""
        last_order = self.env['sale.order'].search([
            ('partner_id', '=', customer.id),
            ('state', 'in', ['sale', 'done']),
        ], order='date_order desc', limit=1)
        
        if not last_order:
            return False
        
        if self.date_from and last_order.date_order < self.date_from:
            return False
        
        if self.date_to and last_order.date_order > self.date_to:
            return False
        
        return True
    
    def _evaluate_customer_age(self, customer):
        """Evaluate customer age rule"""
        if not customer.create_date:
            return False
        
        days_old = (fields.Date.today() - customer.create_date.date()).days
        
        if self.min_value and days_old < self.min_value:
            return False
        
        if self.max_value and days_old > self.max_value:
            return False
        
        return True
    
    def _evaluate_custom_logic(self, customer):
        """Evaluate custom logic rule"""
        if not self.custom_domain:
            return False
        
        try:
            domain = eval(self.custom_domain)
            customers = self.env['res.partner'].search(domain)
            return customer in customers
        except:
            return False




