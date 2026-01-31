# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMoveExtended(models.Model):
    _inherit = 'account.move'

    # Additional tracking fields
    approval_state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', tracking=True, copy=False)

    approved_by = fields.Many2one('res.users', string='Approved By', copy=False)
    approved_date = fields.Datetime('Approval Date', copy=False)
    rejection_reason = fields.Text('Rejection Reason', copy=False)

    # Custom reference fields
    internal_reference = fields.Char('Internal Reference', copy=False)
    department_name = fields.Char('Department', help='Department name for categorization')

    # Financial notes
    financial_notes = fields.Html('Financial Notes')

    # Recurring invoice fields
    is_recurring = fields.Boolean('Recurring Invoice', default=False)
    recurring_interval = fields.Integer('Recurring Interval', default=1)
    recurring_period = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], string='Recurring Period', default='months')
    next_recurring_date = fields.Date('Next Recurring Date')

    # Payment tracking
    payment_reminder_sent = fields.Boolean('Payment Reminder Sent', default=False)
    payment_reminder_date = fields.Date('Last Reminder Date')

    def action_approve(self):
        """Approve the journal entry"""
        for move in self:
            if move.approval_state == 'pending':
                move.write({
                    'approval_state': 'approved',
                    'approved_by': self.env.user.id,
                    'approved_date': fields.Datetime.now(),
                })
        return True

    def action_reject(self):
        """Open rejection wizard"""
        return {
            'name': _('Reject Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_id': self.id},
        }

    def action_request_approval(self):
        """Request approval for this entry"""
        for move in self:
            move.approval_state = 'pending'
        return True

    def action_send_payment_reminder(self):
        """Send payment reminder email"""
        self.ensure_one()
        # This can be extended to send actual emails
        self.write({
            'payment_reminder_sent': True,
            'payment_reminder_date': fields.Date.today(),
        })
        return True

    def action_create_recurring(self):
        """Create next recurring invoice"""
        self.ensure_one()
        if not self.is_recurring or not self.next_recurring_date:
            return False

        # Copy the invoice
        new_move = self.copy({
            'date': self.next_recurring_date,
            'invoice_date': self.next_recurring_date,
        })

        # Calculate next recurring date
        from dateutil.relativedelta import relativedelta
        if self.recurring_period == 'days':
            delta = relativedelta(days=self.recurring_interval)
        elif self.recurring_period == 'weeks':
            delta = relativedelta(weeks=self.recurring_interval)
        elif self.recurring_period == 'months':
            delta = relativedelta(months=self.recurring_interval)
        else:
            delta = relativedelta(years=self.recurring_interval)

        self.next_recurring_date = self.next_recurring_date + delta

        return {
            'name': _('Recurring Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': new_move.id,
            'view_mode': 'form',
        }


class AccountMoveLineExtended(models.Model):
    _inherit = 'account.move.line'

    # Additional analysis fields
    cost_center_id = fields.Many2one('account.analytic.account', string='Cost Center')
    project_name = fields.Char('Project', help='Project name for categorization')

    # Budget tracking
    budget_line_id = fields.Many2one('account.budget.line', string='Budget Line')

    # Notes
    line_notes = fields.Char('Line Notes')


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
