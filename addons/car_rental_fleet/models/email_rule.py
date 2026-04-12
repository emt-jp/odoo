# -*- coding: utf-8 -*-
"""
Email Classification Rule

Deterministic rules that short-circuit the Claude API call. When an incoming
email matches a rule, the classification is applied directly — no AI round-trip,
no cost, instant routing. Users create rules by clicking "Create Rule" on an
email they've manually corrected.
"""

import re
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class TdcEmailRule(models.Model):
    _name = 'tdc.email.rule'
    _description = 'AI Email Classification Rule'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    sender_pattern = fields.Char(
        string='Sender Match',
        help='Match against the email From header. Empty = no check on sender.',
    )
    subject_pattern = fields.Char(
        string='Subject Match',
        help='Match against the email subject. Empty = no check on subject.',
    )
    body_pattern = fields.Char(
        string='Body Match',
        help='Match against the email body. Empty = no check on body.',
    )
    match_type = fields.Selection([
        ('substring', 'Substring (case-insensitive)'),
        ('regex', 'Regular expression'),
    ], default='substring', required=True)

    classification = fields.Selection([
        ('rental_booking', 'Rental Booking'),
        ('rental_cancel', 'Rental Cancellation'),
        ('invoice', 'Invoice / Receipt'),
        ('expense', 'Expense / Receipt'),
        ('task', 'Task / Action Item'),
        ('customer_inquiry', 'Customer Inquiry'),
        ('spam', 'Spam / Newsletter'),
        ('informational', 'Informational'),
    ], required=True)

    confidence = fields.Float(
        string='Confidence',
        default=1.0,
        digits=(3, 2),
        help='Confidence applied to emails matching this rule. 1.0 triggers auto-processing.',
    )

    hit_count = fields.Integer(string='Times Matched', readonly=True, default=0)
    last_matched = fields.Datetime(readonly=True)
    created_from_email_id = fields.Many2one(
        'tdc.email.processor',
        string='Created From Email',
        readonly=True,
        ondelete='set null',
    )
    notes = fields.Text()

    @api.constrains('sender_pattern', 'subject_pattern', 'body_pattern')
    def _check_has_pattern(self):
        for r in self:
            if not (r.sender_pattern or r.subject_pattern or r.body_pattern):
                from odoo.exceptions import ValidationError
                raise ValidationError(
                    "At least one match pattern (sender, subject, or body) is required."
                )

    def matches(self, email_from, subject, body):
        """Return True if this rule matches the given email fields.

        All configured patterns must match (AND semantics). Unset patterns
        are ignored. Regex errors cause the rule to not match (fail-safe).
        """
        self.ensure_one()
        checks = (
            (self.sender_pattern, email_from or ''),
            (self.subject_pattern, subject or ''),
            (self.body_pattern, body or ''),
        )
        matched_any = False
        for pattern, text in checks:
            if not pattern:
                continue
            matched_any = True
            if self.match_type == 'regex':
                try:
                    if not re.search(pattern, text, re.IGNORECASE):
                        return False
                except re.error as e:
                    _logger.warning("Rule %s regex error: %s", self.id, e)
                    return False
            else:
                if pattern.lower() not in text.lower():
                    return False
        return matched_any

    def record_hit(self):
        for r in self:
            r.write({
                'hit_count': r.hit_count + 1,
                'last_matched': fields.Datetime.now(),
            })
