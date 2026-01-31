# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class RentalInsurance(models.Model):
    _name = 'rental.insurance'
    _description = 'Rental Insurance Plan'
    _order = 'sequence, id'

    name = fields.Char('Insurance Name', required=True, translate=True)
    code = fields.Selection([
        ('none', 'No Insurance'),
        ('basic', 'Basic Insurance'),
        ('full', 'Full Coverage'),
    ], string='Insurance Type', required=True, default='basic')
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)

    # Pricing
    daily_rate = fields.Float('Daily Rate', required=True, default=0.0)
    currency_id = fields.Many2one('res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)

    # Coverage Details
    description = fields.Html('Description', translate=True)
    terms = fields.Html('Terms & Conditions', translate=True)
    coverage_amount = fields.Float('Maximum Coverage Amount', default=0.0)
    max_coverage = fields.Float('Maximum Coverage', related='coverage_amount', store=True)
    deductible = fields.Float('Deductible Amount', default=0.0,
        help='Amount customer pays before insurance kicks in')

    # Coverage includes
    collision_damage = fields.Boolean('Collision Damage Waiver (CDW)', default=False)
    theft_protection = fields.Boolean('Theft Protection', default=False)
    personal_accident = fields.Boolean('Personal Accident Insurance', default=False)
    liability_coverage = fields.Boolean('Third Party Liability', default=False)
    roadside_assistance = fields.Boolean('24/7 Roadside Assistance', default=False)
    glass_tire_coverage = fields.Boolean('Glass & Tire Coverage', default=False)

    # Display
    is_recommended = fields.Boolean('Recommended', default=False,
        help='Highlight this as recommended option')
    icon = fields.Char('Icon Class', default='fa-shield',
        help='FontAwesome icon class')
    color = fields.Char('Color', default='#007bff')

    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company)

    def get_coverage_features(self):
        """Return list of coverage features for display"""
        self.ensure_one()
        features = []
        if self.collision_damage:
            features.append({'name': _('Collision Damage Waiver'), 'icon': 'fa-car'})
        if self.theft_protection:
            features.append({'name': _('Theft Protection'), 'icon': 'fa-lock'})
        if self.personal_accident:
            features.append({'name': _('Personal Accident Insurance'), 'icon': 'fa-user-shield'})
        if self.liability_coverage:
            features.append({'name': _('Third Party Liability'), 'icon': 'fa-users'})
        if self.roadside_assistance:
            features.append({'name': _('24/7 Roadside Assistance'), 'icon': 'fa-phone'})
        if self.glass_tire_coverage:
            features.append({'name': _('Glass & Tire Coverage'), 'icon': 'fa-circle'})
        return features
