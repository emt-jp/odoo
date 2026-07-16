# -*- coding: utf-8 -*-
# Part of the emt-tech job-hunting platform.

from odoo import models, fields


class JobhuntContact(models.Model):
    # Recruiter / hiring contact. Dedicated model, isolated from res.partner.
    _name = 'jobhunt.contact'
    _description = 'Job Hunt Contact (recruiter / hiring)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char('Name', required=True, tracking=True)
    company_id = fields.Many2one('jobhunt.company', string='Company')
    email = fields.Char('Email')
    linkedin = fields.Char('LinkedIn')
    phone = fields.Char('Phone')
    role = fields.Char('Role', help="e.g. recruiter, hiring manager, founder")
    source = fields.Char('Source', help="how this contact was found")
    notes = fields.Html('Notes')
