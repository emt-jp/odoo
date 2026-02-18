# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountMoveRejectWizard(models.TransientModel):
    _name = 'account.move.reject.wizard'
    _description = 'Reject Journal Entry Wizard'

    move_id = fields.Many2one('account.move', string='Journal Entry', required=True)
    rejection_reason = fields.Text('Rejection Reason', required=True)

    def action_reject(self):
        """Reject the journal entry with reason"""
        self.move_id.write({
            'approval_state': 'rejected',
            'rejection_reason': self.rejection_reason,
        })
        return {'type': 'ir.actions.act_window_close'}
