# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class FleetInsurance(models.Model):
    _name = 'fleet.insurance'
    _description = 'Fleet Insurance Management'
    _order = 'expiry_date desc'
    
    _sql_constraints = [
        ('policy_number_unique', 'UNIQUE(policy_number)', 'Policy number must be unique!'),
    ]
    
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    
    # Insurance Details
    policy_number = fields.Char('Policy Number', required=True)
    insurance_company = fields.Char('Insurance Company', required=True)
    insurance_type = fields.Selection([
        ('comprehensive', 'Comprehensive'),
        ('third_party', 'Third Party'),
        ('collision', 'Collision'),
        ('liability', 'Liability'),
        ('theft', 'Theft'),
        ('fire', 'Fire'),
        ('natural_disaster', 'Natural Disaster'),
    ], string='Insurance Type', required=True)
    
    # Coverage Details
    coverage_amount = fields.Monetary('Coverage Amount', currency_field='currency_id', required=True)
    premium_amount = fields.Monetary('Premium Amount', currency_field='currency_id', required=True)
    deductible_amount = fields.Monetary('Deductible Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    # Validity Period
    start_date = fields.Date('Start Date', required=True)
    expiry_date = fields.Date('Expiry Date', required=True)
    
    # Status
    status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ], string='Status', default='active', compute='_compute_status', store=True, readonly=False)
    
    # Contact Information
    agent_name = fields.Char('Agent Name')
    agent_phone = fields.Char('Agent Phone')
    agent_email = fields.Char('Agent Email')
    
    # Documents
    policy_document = fields.Binary('Policy Document')
    policy_filename = fields.Char('Policy Filename')
    certificate_document = fields.Binary('Certificate Document')
    certificate_filename = fields.Char('Certificate Filename')
    
    # Claims
    claim_ids = fields.One2many('fleet.insurance.claim', 'insurance_id', string='Claims')
    claims_count = fields.Integer('Claims Count', compute='_compute_claims_count', store=True)
    total_claims_amount = fields.Monetary('Total Claims Amount', currency_field='currency_id', compute='_compute_claims_count', store=True)
    
    # Enterprise Features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.depends('claim_ids')
    def _compute_claims_count(self):
        """Compute claims count and total amount"""
        for insurance in self:
            if insurance._is_enterprise_available():
                insurance.claims_count = len(insurance.claim_ids)
                insurance.total_claims_amount = sum(insurance.claim_ids.mapped('claim_amount'))
            else:
                insurance.claims_count = 0
                insurance.total_claims_amount = 0.0
    
    @api.depends('expiry_date')
    def _compute_status(self):
        """Auto-update status based on expiry date"""
        today = fields.Date.today()
        for insurance in self:
            if insurance.status == 'cancelled':
                continue  # Don't auto-update cancelled policies
            if insurance.expiry_date and insurance.expiry_date < today:
                insurance.status = 'expired'
            elif insurance.status == 'expired' and insurance.expiry_date and insurance.expiry_date >= today:
                insurance.status = 'active'
    
    @api.constrains('start_date', 'expiry_date')
    def _check_dates(self):
        """Validate that expiry date is after start date"""
        for insurance in self:
            if insurance.start_date and insurance.expiry_date:
                if insurance.expiry_date <= insurance.start_date:
                    raise ValidationError(_('Expiry date must be after start date.'))
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    def action_view_claims(self):
        """Open claims for this insurance policy"""
        self.ensure_one()
        action = {
            'name': _('Insurance Claims'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.insurance.claim',
            'view_mode': 'tree,form',
            'domain': [('insurance_id', '=', self.id)],
            'context': {'default_insurance_id': self.id},
        }
        return action
    
    @api.model
    def check_expiring_insurance(self, days=30):
        """Check for expiring insurance policies"""
        if not self._is_enterprise_available():
            return []
        
        expiry_date = fields.Date.today() + timedelta(days=days)
        
        expiring_policies = self.search([
            ('status', '=', 'active'),
            ('expiry_date', '<=', expiry_date),
            ('expiry_date', '>', fields.Date.today()),
        ])
        
        alerts = []
        for policy in expiring_policies:
            days_until_expiry = (policy.expiry_date - fields.Date.today()).days
            alerts.append({
                'policy_id': policy.id,
                'vehicle_id': policy.vehicle_id.id,
                'vehicle_name': policy.vehicle_id.name,
                'policy_number': policy.policy_number,
                'insurance_company': policy.insurance_company,
                'expiry_date': policy.expiry_date,
                'days_until_expiry': days_until_expiry,
                'severity': 'high' if days_until_expiry <= 7 else 'medium',
            })
        
        return alerts
    
    @api.model
    def get_insurance_analytics(self, start_date=None, end_date=None):
        """Get insurance analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Insurance analytics require the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=365)
        if not end_date:
            end_date = fields.Date.today()
        
        policies = self.search([
            ('start_date', '>=', start_date),
            ('start_date', '<=', end_date),
        ])
        
        total_policies = len(policies)
        active_policies = len(policies.filtered(lambda p: p.status == 'active'))
        expired_policies = len(policies.filtered(lambda p: p.status == 'expired'))
        
        total_premium = sum(policies.mapped('premium_amount'))
        total_coverage = sum(policies.mapped('coverage_amount'))
        
        # Calculate by insurance type
        type_analytics = {}
        for policy in policies:
            insurance_type = policy.insurance_type
            if insurance_type not in type_analytics:
                type_analytics[insurance_type] = {
                    'count': 0,
                    'total_premium': 0,
                    'total_coverage': 0,
                }
            
            type_analytics[insurance_type]['count'] += 1
            type_analytics[insurance_type]['total_premium'] += policy.premium_amount
            type_analytics[insurance_type]['total_coverage'] += policy.coverage_amount
        
        return {
            'policy_metrics': {
                'total_policies': total_policies,
                'active_policies': active_policies,
                'expired_policies': expired_policies,
                'total_premium': total_premium,
                'total_coverage': total_coverage,
            },
            'type_analytics': type_analytics,
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
        }
    
    @api.model
    def create_insurance_policy(self, vehicle_id, policy_data):
        """Create insurance policy"""
        if not self._is_enterprise_available():
            raise UserError(_("Insurance management requires the Enterprise edition."))
        
        # Validate required fields
        required_fields = ['policy_number', 'insurance_company', 'insurance_type', 'coverage_amount', 'premium_amount', 'start_date', 'expiry_date']
        for field in required_fields:
            if field not in policy_data or not policy_data[field]:
                raise UserError(_(f"Field {field} is required."))
        
        policy_data['vehicle_id'] = vehicle_id
        return self.create(policy_data)
    
    @api.model
    def renew_insurance_policy(self, policy_id, new_expiry_date):
        """Renew insurance policy"""
        if not self._is_enterprise_available():
            raise UserError(_("Insurance renewal requires the Enterprise edition."))
        
        policy = self.browse(policy_id)
        if not policy.exists():
            raise UserError(_("Insurance policy not found."))
        
        if policy.status != 'active':
            raise UserError(_("Only active policies can be renewed."))
        
        # Create new policy with same details
        new_policy_data = {
            'vehicle_id': policy.vehicle_id.id,
            'policy_number': f"{policy.policy_number}-RENEWED",
            'insurance_company': policy.insurance_company,
            'insurance_type': policy.insurance_type,
            'coverage_amount': policy.coverage_amount,
            'premium_amount': policy.premium_amount,
            'deductible_amount': policy.deductible_amount,
            'start_date': policy.expiry_date + timedelta(days=1),
            'expiry_date': new_expiry_date,
            'agent_name': policy.agent_name,
            'agent_phone': policy.agent_phone,
            'agent_email': policy.agent_email,
        }
        
        # Mark old policy as expired
        policy.write({'status': 'expired'})
        
        # Create new policy
        return self.create(new_policy_data)


class FleetInsuranceClaim(models.Model):
    _name = 'fleet.insurance.claim'
    _description = 'Fleet Insurance Claims'
    _order = 'claim_date desc'
    
    insurance_id = fields.Many2one('fleet.insurance', string='Insurance Policy', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', related='insurance_id.vehicle_id', store=True)
    
    # Claim Details
    claim_number = fields.Char('Claim Number', required=True)
    claim_date = fields.Date('Claim Date', required=True, default=fields.Date.today)
    incident_date = fields.Date('Incident Date', required=True)
    incident_location = fields.Char('Incident Location', required=True)
    
    # Claim Type
    claim_type = fields.Selection([
        ('accident', 'Accident'),
        ('theft', 'Theft'),
        ('vandalism', 'Vandalism'),
        ('fire', 'Fire'),
        ('natural_disaster', 'Natural Disaster'),
        ('other', 'Other'),
    ], string='Claim Type', required=True)
    
    # Claim Amount
    claim_amount = fields.Monetary('Claim Amount', currency_field='currency_id', required=True)
    approved_amount = fields.Monetary('Approved Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', related='insurance_id.currency_id')
    
    # Status
    status = fields.Selection([
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('settled', 'Settled'),
    ], string='Status', default='submitted')
    
    # Description
    description = fields.Text('Description', required=True)
    damage_description = fields.Text('Damage Description')
    
    # Documents
    police_report = fields.Binary('Police Report')
    police_report_filename = fields.Char('Police Report Filename')
    photos = fields.Binary('Photos')
    photos_filename = fields.Char('Photos Filename')
    estimate_document = fields.Binary('Estimate Document')
    estimate_filename = fields.Char('Estimate Filename')
    
    # Settlement
    settlement_date = fields.Date('Settlement Date')
    settlement_amount = fields.Monetary('Settlement Amount', currency_field='currency_id')
    settlement_notes = fields.Text('Settlement Notes')
    
    # Enterprise Features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    @api.constrains('claim_date', 'incident_date')
    def _check_claim_dates(self):
        """Validate that claim date is not before incident date"""
        for claim in self:
            if claim.claim_date and claim.incident_date:
                if claim.claim_date < claim.incident_date:
                    raise ValidationError(_('Claim date cannot be before incident date.'))
    
    @api.constrains('claim_amount', 'approved_amount')
    def _check_approved_amount(self):
        """Validate that approved amount does not exceed claim amount"""
        for claim in self:
            if claim.approved_amount and claim.claim_amount:
                if claim.approved_amount > claim.claim_amount:
                    raise ValidationError(_('Approved amount cannot exceed claim amount.'))
    
    @api.constrains('approved_amount', 'settlement_amount', 'status')
    def _check_settlement_amount(self):
        """Validate that settlement amount does not exceed approved amount"""
        for claim in self:
            if claim.settlement_amount and claim.approved_amount:
                if claim.settlement_amount > claim.approved_amount:
                    raise ValidationError(_('Settlement amount cannot exceed approved amount.'))
            if claim.settlement_amount and claim.status not in ('approved', 'settled'):
                raise ValidationError(_('Settlement amount can only be set for approved or settled claims.'))
    
    @api.model
    def create_claim(self, insurance_id, claim_data):
        """Create insurance claim"""
        if not self._is_enterprise_available():
            raise UserError(_("Claim management requires the Enterprise edition."))
        
        # Validate required fields
        required_fields = ['claim_number', 'incident_date', 'incident_location', 'claim_type', 'claim_amount', 'description']
        for field in required_fields:
            if field not in claim_data or not claim_data[field]:
                raise UserError(_(f"Field {field} is required."))
        
        claim_data['insurance_id'] = insurance_id
        return self.create(claim_data)
    
    @api.model
    def get_claims_analytics(self, start_date=None, end_date=None):
        """Get claims analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Claims analytics require the Enterprise edition."))
        
        if not start_date:
            start_date = fields.Date.today() - timedelta(days=365)
        if not end_date:
            end_date = fields.Date.today()
        
        claims = self.search([
            ('claim_date', '>=', start_date),
            ('claim_date', '<=', end_date),
        ])
        
        total_claims = len(claims)
        approved_claims = len(claims.filtered(lambda c: c.status == 'approved'))
        settled_claims = len(claims.filtered(lambda c: c.status == 'settled'))
        
        total_claim_amount = sum(claims.mapped('claim_amount'))
        total_approved_amount = sum(claims.mapped('approved_amount'))
        total_settled_amount = sum(claims.mapped('settlement_amount'))
        
        # Calculate by claim type
        type_analytics = {}
        for claim in claims:
            claim_type = claim.claim_type
            if claim_type not in type_analytics:
                type_analytics[claim_type] = {
                    'count': 0,
                    'total_amount': 0,
                    'avg_amount': 0,
                }
            
            type_analytics[claim_type]['count'] += 1
            type_analytics[claim_type]['total_amount'] += claim.claim_amount
        
        # Calculate average amounts
        for claim_type in type_analytics:
            data = type_analytics[claim_type]
            if data['count'] > 0:
                data['avg_amount'] = data['total_amount'] / data['count']
        
        return {
            'claim_metrics': {
                'total_claims': total_claims,
                'approved_claims': approved_claims,
                'settled_claims': settled_claims,
                'approval_rate': (approved_claims / total_claims * 100) if total_claims > 0 else 0,
                'settlement_rate': (settled_claims / total_claims * 100) if total_claims > 0 else 0,
                'total_claim_amount': total_claim_amount,
                'total_approved_amount': total_approved_amount,
                'total_settled_amount': total_settled_amount,
            },
            'type_analytics': type_analytics,
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            },
        }


class FleetDocument(models.Model):
    _name = 'fleet.document'
    _description = 'Fleet Document Management'
    _order = 'expiry_date desc'
    
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    
    # Document Details
    document_type = fields.Selection([
        ('registration', 'Vehicle Registration'),
        ('license', 'Driver License'),
        ('insurance', 'Insurance Certificate'),
        ('inspection', 'Inspection Certificate'),
        ('emission', 'Emission Certificate'),
        ('permit', 'Permit'),
        ('contract', 'Contract'),
        ('warranty', 'Warranty'),
        ('other', 'Other'),
    ], string='Document Type', required=True)
    
    document_name = fields.Char('Document Name', required=True)
    document_number = fields.Char('Document Number')
    
    # Validity Period
    issue_date = fields.Date('Issue Date')
    expiry_date = fields.Date('Expiry Date')
    
    # Status
    status = fields.Selection([
        ('valid', 'Valid'),
        ('expired', 'Expired'),
        ('expiring_soon', 'Expiring Soon'),
        ('invalid', 'Invalid'),
    ], string='Status', compute='_compute_status', store=True)
    
    # Document File
    document_file = fields.Binary('Document File', required=True)
    document_filename = fields.Char('Document Filename')
    
    # Description
    description = fields.Text('Description')
    
    # Enterprise Features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    @api.depends('expiry_date')
    def _compute_status(self):
        """Compute document status"""
        for document in self:
            if not document.expiry_date:
                document.status = 'valid'
            elif document.expiry_date < fields.Date.today():
                document.status = 'expired'
            elif document.expiry_date <= fields.Date.today() + timedelta(days=30):
                document.status = 'expiring_soon'
            else:
                document.status = 'valid'
    
    @api.constrains('issue_date', 'expiry_date')
    def _check_document_dates(self):
        """Validate that expiry date is after issue date if both are provided"""
        for document in self:
            if document.issue_date and document.expiry_date:
                if document.expiry_date < document.issue_date:
                    raise ValidationError(_('Expiry date must be after issue date.'))
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return True  # Enterprise checks disabled
    
    @api.model
    def get_expiring_documents(self, days=30):
        """Get expiring documents"""
        if not self._is_enterprise_available():
            return self.env['fleet.document']
        
        expiry_date = fields.Date.today() + timedelta(days=days)
        
        return self.search([
            ('expiry_date', '<=', expiry_date),
            ('expiry_date', '>', fields.Date.today()),
        ])
    
    @api.model
    def get_expired_documents(self):
        """Get expired documents"""
        if not self._is_enterprise_available():
            return self.env['fleet.document']
        
        return self.search([
            ('expiry_date', '<', fields.Date.today()),
        ])
    
    @api.model
    def create_document(self, vehicle_id, document_data):
        """Create document"""
        if not self._is_enterprise_available():
            raise UserError(_("Document management requires the Enterprise edition."))
        
        # Validate required fields
        required_fields = ['document_type', 'document_name', 'document_file']
        for field in required_fields:
            if field not in document_data or not document_data[field]:
                raise UserError(_(f"Field {field} is required."))
        
        document_data['vehicle_id'] = vehicle_id
        return self.create(document_data)
    
    @api.model
    def get_document_analytics(self):
        """Get document analytics"""
        if not self._is_enterprise_available():
            raise UserError(_("Document analytics require the Enterprise edition."))
        
        documents = self.search([])
        
        total_documents = len(documents)
        valid_documents = len(documents.filtered(lambda d: d.status == 'valid'))
        expired_documents = len(documents.filtered(lambda d: d.status == 'expired'))
        expiring_documents = len(documents.filtered(lambda d: d.status == 'expiring_soon'))
        
        # Calculate by document type
        type_analytics = {}
        for document in documents:
            doc_type = document.document_type
            if doc_type not in type_analytics:
                type_analytics[doc_type] = {
                    'total': 0,
                    'valid': 0,
                    'expired': 0,
                    'expiring_soon': 0,
                }
            
            type_analytics[doc_type]['total'] += 1
            type_analytics[doc_type][document.status] += 1
        
        return {
            'document_metrics': {
                'total_documents': total_documents,
                'valid_documents': valid_documents,
                'expired_documents': expired_documents,
                'expiring_documents': expiring_documents,
                'validity_rate': (valid_documents / total_documents * 100) if total_documents > 0 else 0,
            },
            'type_analytics': type_analytics,
        }




