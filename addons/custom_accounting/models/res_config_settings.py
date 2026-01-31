# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_japanese_invoice_system = fields.Boolean(
        related='company_id.use_japanese_invoice_system',
        readonly=False,
        string='Use Japanese Invoice System'
    )
    company_t_number = fields.Char(
        related='company_id.t_number',
        readonly=False,
        string='Company T-Number'
    )
