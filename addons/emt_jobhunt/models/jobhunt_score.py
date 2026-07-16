# -*- coding: utf-8 -*-
# Part of the emt-tech job-hunting platform.

from odoo import models, fields


class JobhuntScore(models.Model):
    _name = 'jobhunt.score'
    _description = 'Opportunity Score'
    _order = 'scored_at desc'

    name = fields.Char('Reference', compute='_compute_name', store=True)
    posting_id = fields.Many2one('jobhunt.posting', string='Posting',
                                 required=True, ondelete='cascade')
    profile_version = fields.Integer('Profile Version')

    # 12 scoring dimensions (0–100). See emt-tech/docs/SCORING.md.
    dim_cpp = fields.Float('C++ Relevance')
    dim_fintech = fields.Float('FinTech/Trading')
    dim_blockchain = fields.Float('Blockchain/Web3')
    dim_rust = fields.Float('Rust Relevance')
    dim_remote = fields.Float('Remote Compatibility')
    dim_salary = fields.Float('Salary Potential')
    dim_experience = fields.Float('Experience Match')
    dim_location = fields.Float('Location/Visa')
    dim_company = fields.Float('Company Quality')
    dim_freelance = fields.Float('Freelance Compatibility')
    dim_difficulty = fields.Float('Application Difficulty')
    dim_urgency = fields.Float('Urgency')

    total = fields.Float('Total Score')
    classification = fields.Selection([
        ('must_apply', 'Must Apply'),
        ('good_match', 'Good Match'),
        ('maybe', 'Maybe'),
        ('low_priority', 'Low Priority'),
        ('not_suitable', 'Not Suitable'),
    ], string='Classification')
    is_stretch = fields.Boolean('Stretch (Rust/blockchain hard req)')
    rationale = fields.Text('Rationale', help="Explainable per-dimension breakdown")
    scored_at = fields.Datetime('Scored At', default=fields.Datetime.now)

    def _compute_name(self):
        for rec in self:
            rec.name = "%s (%.0f)" % (rec.classification or 'unscored', rec.total or 0.0)
