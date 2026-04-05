# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TdcPromoCode(models.Model):
    _name = 'tdc.promo.code'
    _description = 'TDC Promo Code'
    _order = 'create_date desc'

    code = fields.Char(
        string='Code',
        required=True,
        index=True,
    )
    description = fields.Text(string='Description')
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], string='Discount Type', required=True, default='percentage')
    discount_value = fields.Float(string='Discount Value', required=True)
    min_booking_amount = fields.Float(string='Minimum Booking Amount')
    max_discount = fields.Float(string='Maximum Discount')
    valid_from = fields.Datetime(string='Valid From', required=True)
    valid_to = fields.Datetime(string='Valid To', required=True)
    usage_limit = fields.Integer(string='Usage Limit', default=0, help='0 = unlimited')
    used_count = fields.Integer(string='Used Count', default=0, readonly=True)
    is_active = fields.Boolean(string='Active', default=True, index=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Promo code must be unique!'),
    ]

    @api.constrains('discount_value')
    def _check_discount_value(self):
        for record in self:
            if record.discount_value <= 0:
                raise ValidationError('Discount value must be positive.')
            if record.discount_type == 'percentage' and record.discount_value > 100:
                raise ValidationError('Percentage discount cannot exceed 100%.')

    @api.model
    def create(self, vals):
        if 'code' in vals:
            vals['code'] = vals['code'].upper().strip()
        return super().create(vals)

    def write(self, vals):
        if 'code' in vals:
            vals['code'] = vals['code'].upper().strip()
        return super().write(vals)
