# -*- coding: utf-8 -*-
# Part of the emt-tech job-hunting platform.

from odoo import models, fields


class JobhuntStage(models.Model):
    _name = 'jobhunt.stage'
    _description = 'Job Application Stage'
    _order = 'sequence, id'

    name = fields.Char('Stage', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    fold = fields.Boolean('Folded in Kanban',
                          help="Collapse this column in the kanban by default")
    is_won = fields.Boolean('Won Stage', help="e.g. Offer")
    is_lost = fields.Boolean('Lost Stage', help="e.g. Rejected / Closed")
