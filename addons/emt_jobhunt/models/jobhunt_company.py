# -*- coding: utf-8 -*-
# Part of the emt-tech job-hunting platform.

from odoo import models, fields


class JobhuntCompany(models.Model):
    # Dedicated model (NOT res.partner) to keep job-hunt companies isolated from
    # the company ERP contacts.
    _name = 'jobhunt.company'
    _description = 'Job Hunt Company'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char('Company', required=True, tracking=True)
    website = fields.Char('Website')
    domain = fields.Char('Domain')
    sector = fields.Char('Sector')
    size = fields.Selection([
        ('startup', 'Startup'),
        ('scaleup', 'Scaleup'),
        ('mid', 'Mid-size'),
        ('enterprise', 'Enterprise'),
        ('unknown', 'Unknown'),
    ], string='Size', default='unknown')
    quality_score = fields.Float('Quality Score', help="0–100, feeds opportunity scoring")
    notes = fields.Html('Notes')
    contact_ids = fields.One2many('jobhunt.contact', 'company_id', string='Contacts')
    posting_ids = fields.One2many('jobhunt.posting', 'company_id', string='Postings')
    posting_count = fields.Integer('Postings', compute='_compute_posting_count')

    def _compute_posting_count(self):
        for rec in self:
            rec.posting_count = len(rec.posting_ids)
