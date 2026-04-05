# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tdc_password_hash = fields.Char(
        string='TDC Password Hash',
        help='Bcrypt password hash for TDC web authentication',
        groups='base.group_system',
    )
    email_verified = fields.Boolean(
        string='Email Verified',
        default=False,
        help='Whether the partner has verified their email address via TDC',
    )
    is_rental_customer = fields.Boolean(
        string='Is Rental Customer',
        default=False,
        help='Whether this partner is a TDC rental customer',
    )
