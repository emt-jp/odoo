# -*- coding: utf-8 -*-
# Part of the emt-tech job-hunting platform.

from odoo import models, fields, api


class JobhuntProfile(models.Model):
    # Mirror of emt-tech/profile/master-profile.yaml. The scoring engine and the
    # external generator worker read the active profile. YAML stays the source of
    # truth; loaded into a record on install/update or via the External API.
    _name = 'jobhunt.profile'
    _description = 'Master Resume Profile'
    _order = 'version desc, id desc'

    name = fields.Char('Name', required=True, default='Master Profile')
    active = fields.Boolean('Active', default=True)
    version = fields.Integer('Schema Version', default=1)
    headline = fields.Char('Headline')
    full_name = fields.Char('Full Name')
    # Structured blocks kept as JSON text to mirror the YAML 1:1.
    skills_json = fields.Text('Skills (JSON)')
    role_archetypes_json = fields.Text('Role Archetypes (JSON)')
    github_json = fields.Text('GitHub Projects (JSON)',
                              help="Owned projects + learning signals — for portfolio matching")
    resume_rules_json = fields.Text(
        'Resume Rules (JSON)',
        help="Includes one_client_per_window + lead_client_decided_by=user_at_generation_time")

    @api.model
    def get_active(self):
        return self.search([('active', '=', True)], order='version desc', limit=1)
