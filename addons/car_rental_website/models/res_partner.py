# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class ResPartnerRental(models.Model):
    _inherit = 'res.partner'

    # Driving License
    driving_license_number = fields.Char('Driving License Number')
    driving_license_country_id = fields.Many2one('res.country', string='License Country')
    driving_license_expiry = fields.Date('License Expiry Date')
    driving_license_front = fields.Binary('License Front Image')
    driving_license_back = fields.Binary('License Back Image')
    driving_license_verified = fields.Boolean('License Verified', default=False)
    driving_license_verified_date = fields.Date('Verification Date')
    driving_license_verified_by = fields.Many2one('res.users', string='Verified By')

    # Customer Status
    is_rental_customer = fields.Boolean('Rental Customer', default=False)
    rental_verified = fields.Boolean('Verified Customer', compute='_compute_rental_verified', store=True)
    email_verified = fields.Boolean('Email Verified', default=False)
    email_verification_token = fields.Char('Email Verification Token')

    # Statistics
    total_rentals = fields.Integer('Total Rentals', compute='_compute_rental_stats')
    total_spent = fields.Float('Total Spent', compute='_compute_rental_stats')
    current_rentals = fields.Integer('Current Rentals', compute='_compute_rental_stats')

    # Preferences
    preferred_vehicle_type = fields.Many2one('fleet.vehicle.model.category',
        string='Preferred Vehicle Type')
    preferred_insurance_id = fields.Many2one('rental.insurance',
        string='Preferred Insurance')
    preferred_location_id = fields.Many2one('rental.location',
        string='Preferred Pickup Location')

    # Age verification (must be 21+ to rent)
    birthdate = fields.Date('Date of Birth')
    age = fields.Integer('Age', compute='_compute_age')

    @api.depends('birthdate')
    def _compute_age(self):
        today = date.today()
        for partner in self:
            if partner.birthdate:
                partner.age = today.year - partner.birthdate.year - (
                    (today.month, today.day) < (partner.birthdate.month, partner.birthdate.day)
                )
            else:
                partner.age = 0

    @api.depends('driving_license_verified', 'email_verified', 'driving_license_expiry')
    def _compute_rental_verified(self):
        today = date.today()
        for partner in self:
            partner.rental_verified = (
                partner.driving_license_verified and
                partner.email_verified and
                partner.driving_license_expiry and
                partner.driving_license_expiry > today
            )

    def _compute_rental_stats(self):
        for partner in self:
            bookings = self.env['rental.booking'].search([
                ('partner_id', '=', partner.id),
                ('state', '!=', 'cancelled'),
            ])
            partner.total_rentals = len(bookings.filtered(lambda b: b.state == 'completed'))
            partner.total_spent = sum(bookings.filtered(
                lambda b: b.state == 'completed').mapped('total_amount'))
            partner.current_rentals = len(bookings.filtered(
                lambda b: b.state in ['confirmed', 'in_progress']))

    def action_verify_license(self):
        """Verify customer's driving license"""
        self.ensure_one()
        if not self.driving_license_number:
            raise ValidationError(_('No driving license number provided'))
        if not self.driving_license_front:
            raise ValidationError(_('Please upload license front image'))

        self.write({
            'driving_license_verified': True,
            'driving_license_verified_date': fields.Date.today(),
            'driving_license_verified_by': self.env.uid,
        })

    def action_unverify_license(self):
        """Remove license verification"""
        self.ensure_one()
        self.write({
            'driving_license_verified': False,
            'driving_license_verified_date': False,
            'driving_license_verified_by': False,
        })

    def send_verification_email(self):
        """Send email verification link"""
        self.ensure_one()
        import uuid
        token = str(uuid.uuid4())
        self.email_verification_token = token

        template = self.env.ref('car_rental_website.email_template_verify_email',
                               raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def verify_email(self, token):
        """Verify email with token"""
        self.ensure_one()
        if self.email_verification_token == token:
            self.write({
                'email_verified': True,
                'email_verification_token': False,
            })
            return True
        return False

    def can_rent(self):
        """Check if customer can rent a car"""
        self.ensure_one()
        issues = []

        if not self.email_verified:
            issues.append(_('Email not verified'))

        if not self.driving_license_verified:
            issues.append(_('Driving license not verified'))

        if self.driving_license_expiry and self.driving_license_expiry < date.today():
            issues.append(_('Driving license expired'))

        if self.age and self.age < 21:
            issues.append(_('Must be at least 21 years old'))

        return len(issues) == 0, issues
