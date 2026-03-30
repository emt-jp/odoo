# -*- coding: utf-8 -*-
from odoo import fields, models


class HrDocumentType(models.Model):
    _name = 'hr.document.type'
    _description = 'Employee Document Type'
    _order = 'sequence, name'

    name = fields.Char(string='Document Type', required=True)
    sequence = fields.Integer(default=10)
    has_expiry = fields.Boolean(string='Has Expiry Date', default=False)
    expiry_warning_days = fields.Integer(
        string='Warning Days Before Expiry',
        default=30,
        help='Number of days before expiry to send a warning notification',
    )
    required_for_onboarding = fields.Boolean(
        string='Required for Onboarding',
        default=False,
    )
    active = fields.Boolean(default=True)
    note = fields.Text(string='Description')
