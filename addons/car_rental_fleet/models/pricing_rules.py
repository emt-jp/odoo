# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta, date

_logger = logging.getLogger(__name__)


class FleetPricingRule(models.Model):
    _name = 'fleet.pricing.rule'
    _description = 'Fleet Pricing Rules'
    _order = 'sequence, id'

    name = fields.Char('Rule Name', required=True)
    sequence = fields.Integer('Sequence', default=10, help='Lower sequence = higher priority')
    active = fields.Boolean('Active', default=True)

    # Rule Type
    rule_type = fields.Selection([
        ('seasonal', 'Seasonal Rate'),
        ('duration', 'Duration Discount'),
        ('early_bird', 'Early Bird Discount'),
        ('last_minute', 'Last Minute Deal'),
        ('loyalty', 'Loyalty Discount'),
        ('promo_code', 'Promo Code'),
        ('weekend', 'Weekend Rate'),
        ('holiday', 'Holiday Rate'),
        ('vehicle_category', 'Vehicle Category Rate'),
    ], string='Rule Type', required=True)

    # Applicability
    apply_to = fields.Selection([
        ('all', 'All Vehicles'),
        ('category', 'Specific Category'),
        ('vehicle', 'Specific Vehicle'),
    ], string='Apply To', default='all')

    vehicle_ids = fields.Many2many('fleet.vehicle', string='Vehicles')
    rental_category = fields.Selection([
        ('economy', 'Economy'),
        ('compact', 'Compact'),
        ('intermediate', 'Intermediate'),
        ('standard', 'Standard'),
        ('full_size', 'Full Size'),
        ('premium', 'Premium'),
        ('luxury', 'Luxury'),
        ('suv', 'SUV'),
        ('minivan', 'Minivan'),
        ('convertible', 'Convertible'),
    ], string='Rental Category')

    # Date Range (for seasonal/holiday rates)
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')

    # Day of Week (for weekend rates)
    monday = fields.Boolean('Monday', default=False)
    tuesday = fields.Boolean('Tuesday', default=False)
    wednesday = fields.Boolean('Wednesday', default=False)
    thursday = fields.Boolean('Thursday', default=False)
    friday = fields.Boolean('Friday', default=True)
    saturday = fields.Boolean('Saturday', default=True)
    sunday = fields.Boolean('Sunday', default=True)

    # Duration Conditions (for duration discounts)
    min_duration_days = fields.Integer('Minimum Duration (Days)', default=1)
    max_duration_days = fields.Integer('Maximum Duration (Days)', default=365)

    # Early Bird / Last Minute Conditions
    booking_days_before = fields.Integer('Days Before Pickup', help='For early bird: minimum days, for last minute: maximum days')

    # Promo Code
    promo_code = fields.Char('Promo Code')
    promo_usage_limit = fields.Integer('Usage Limit', default=0, help='0 = unlimited')
    promo_used_count = fields.Integer('Times Used', default=0, readonly=True)

    # Loyalty Conditions
    min_previous_rentals = fields.Integer('Minimum Previous Rentals', default=0)

    # Pricing Adjustment
    adjustment_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('new_rate', 'New Daily Rate'),
    ], string='Adjustment Type', required=True, default='percentage')

    adjustment_value = fields.Float('Adjustment Value', required=True, help='Negative = discount, Positive = surcharge')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Stacking
    can_stack = fields.Boolean('Can Stack with Other Rules', default=False, help='If checked, this rule can be combined with other discounts')

    # Description
    description = fields.Text('Description')
    customer_description = fields.Text('Customer Visible Description', help='Shown to customers on website/portal')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rule in self:
            if rule.date_from and rule.date_to and rule.date_from > rule.date_to:
                raise ValidationError(_("End date must be after start date."))

    @api.constrains('promo_code')
    def _check_promo_code(self):
        for rule in self:
            if rule.rule_type == 'promo_code' and not rule.promo_code:
                raise ValidationError(_("Promo code is required for promo code rules."))
            if rule.promo_code:
                existing = self.search([
                    ('id', '!=', rule.id),
                    ('promo_code', '=', rule.promo_code),
                    ('active', '=', True),
                ])
                if existing:
                    raise ValidationError(_("Promo code '%s' already exists.") % rule.promo_code)

    def is_applicable(self, vehicle, pickup_date, return_date, customer=None, promo_code=None):
        """Check if this rule is applicable for the given rental"""
        self.ensure_one()

        if not self.active:
            return False

        # Check vehicle applicability
        if self.apply_to == 'vehicle' and vehicle not in self.vehicle_ids:
            return False
        if self.apply_to == 'category' and self.rental_category and vehicle.rental_category != self.rental_category:
            return False

        # Check date range
        if self.date_from and pickup_date.date() < self.date_from:
            return False
        if self.date_to and pickup_date.date() > self.date_to:
            return False

        # Check duration
        duration_days = (return_date - pickup_date).days
        if duration_days < self.min_duration_days:
            return False
        if self.max_duration_days and duration_days > self.max_duration_days:
            return False

        # Check rule-specific conditions
        if self.rule_type == 'promo_code':
            if promo_code != self.promo_code:
                return False
            if self.promo_usage_limit > 0 and self.promo_used_count >= self.promo_usage_limit:
                return False

        if self.rule_type == 'early_bird':
            days_until_pickup = (pickup_date.date() - date.today()).days
            if days_until_pickup < self.booking_days_before:
                return False

        if self.rule_type == 'last_minute':
            days_until_pickup = (pickup_date.date() - date.today()).days
            if days_until_pickup > self.booking_days_before:
                return False

        if self.rule_type == 'weekend':
            # Check if any rental day falls on selected weekdays
            has_applicable_day = False
            current = pickup_date
            while current <= return_date:
                weekday = current.weekday()
                if (weekday == 0 and self.monday) or \
                   (weekday == 1 and self.tuesday) or \
                   (weekday == 2 and self.wednesday) or \
                   (weekday == 3 and self.thursday) or \
                   (weekday == 4 and self.friday) or \
                   (weekday == 5 and self.saturday) or \
                   (weekday == 6 and self.sunday):
                    has_applicable_day = True
                    break
                current += timedelta(days=1)
            if not has_applicable_day:
                return False

        if self.rule_type == 'loyalty' and customer:
            previous_rentals = self.env['fleet.rental'].search_count([
                ('customer_id', '=', customer.id),
                ('state', '=', 'completed'),
            ])
            if previous_rentals < self.min_previous_rentals:
                return False

        return True

    def calculate_adjustment(self, base_rate, duration_days=1):
        """Calculate the price adjustment"""
        self.ensure_one()

        if self.adjustment_type == 'percentage':
            return base_rate * (self.adjustment_value / 100)
        elif self.adjustment_type == 'fixed':
            return self.adjustment_value
        elif self.adjustment_type == 'new_rate':
            return self.adjustment_value - base_rate

        return 0

    def mark_promo_used(self):
        """Increment promo code usage count"""
        self.ensure_one()
        if self.rule_type == 'promo_code':
            self.promo_used_count += 1


class FleetPricingCalculator(models.TransientModel):
    _name = 'fleet.pricing.calculator'
    _description = 'Fleet Pricing Calculator'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    pickup_date = fields.Datetime('Pickup Date', required=True)
    return_date = fields.Datetime('Return Date', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer')
    promo_code = fields.Char('Promo Code')

    # Results
    base_daily_rate = fields.Monetary('Base Daily Rate', currency_field='currency_id', readonly=True)
    duration_days = fields.Integer('Duration (Days)', readonly=True)
    base_total = fields.Monetary('Base Total', currency_field='currency_id', readonly=True)
    discount_amount = fields.Monetary('Total Discount', currency_field='currency_id', readonly=True)
    surcharge_amount = fields.Monetary('Total Surcharge', currency_field='currency_id', readonly=True)
    final_total = fields.Monetary('Final Total', currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    applied_rules = fields.Text('Applied Rules', readonly=True)

    def action_calculate(self):
        """Calculate pricing with all applicable rules"""
        self.ensure_one()

        vehicle = self.vehicle_id
        pickup = self.pickup_date
        return_dt = self.return_date

        duration = (return_dt - pickup).days
        if duration < 1:
            duration = 1

        base_rate = vehicle.daily_rate
        base_total = base_rate * duration

        # Find applicable rules
        rules = self.env['fleet.pricing.rule'].search([
            ('active', '=', True),
        ], order='sequence')

        total_discount = 0
        total_surcharge = 0
        applied_rules_list = []
        applied_non_stackable = False

        for rule in rules:
            if rule.is_applicable(vehicle, pickup, return_dt, self.customer_id, self.promo_code):
                # Check stacking
                if not rule.can_stack and applied_non_stackable:
                    continue

                adjustment = rule.calculate_adjustment(base_rate, duration) * duration

                if adjustment < 0:
                    total_discount += abs(adjustment)
                    applied_rules_list.append(f"✓ {rule.name}: -{abs(adjustment):.2f}")
                else:
                    total_surcharge += adjustment
                    applied_rules_list.append(f"✓ {rule.name}: +{adjustment:.2f}")

                if not rule.can_stack:
                    applied_non_stackable = True

        final_total = base_total - total_discount + total_surcharge

        self.write({
            'base_daily_rate': base_rate,
            'duration_days': duration,
            'base_total': base_total,
            'discount_amount': total_discount,
            'surcharge_amount': total_surcharge,
            'final_total': final_total,
            'applied_rules': '\n'.join(applied_rules_list) if applied_rules_list else 'No special rates applied',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.pricing.calculator',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class FleetSeasonalRate(models.Model):
    _name = 'fleet.seasonal.rate'
    _description = 'Seasonal Rate Configuration'
    _order = 'date_from'

    name = fields.Char('Season Name', required=True)
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)

    rate_multiplier = fields.Float('Rate Multiplier', default=1.0, help='1.0 = normal rate, 1.5 = 50% increase, 0.8 = 20% discount')

    # Apply to specific categories
    apply_to_all = fields.Boolean('Apply to All Categories', default=True)
    rental_category_ids = fields.Many2many(
        'fleet.vehicle',
        'fleet_seasonal_rate_category_rel',
        'rate_id', 'vehicle_id',
        string='Specific Vehicles',
        help='Leave empty to apply to all'
    )

    notes = fields.Text('Notes')
    active = fields.Boolean('Active', default=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rate in self:
            if rate.date_from > rate.date_to:
                raise ValidationError(_("End date must be after start date."))

    @api.constrains('rate_multiplier')
    def _check_multiplier(self):
        for rate in self:
            if rate.rate_multiplier <= 0:
                raise ValidationError(_("Rate multiplier must be greater than 0."))
