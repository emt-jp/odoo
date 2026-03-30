# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class HrEmployeeDocument(models.Model):
    _name = 'hr.employee.document'
    _description = 'Employee Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date asc, name'

    name = fields.Char(string='Document Name', required=True, tracking=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, ondelete='cascade',
    )
    document_type_id = fields.Many2one(
        'hr.document.type', string='Document Type', required=True, tracking=True,
    )
    document_number = fields.Char(string='Document Number', tracking=True)
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    has_expiry = fields.Boolean(related='document_type_id.has_expiry')
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'hr_employee_document_attachment_rel',
        'document_id',
        'attachment_id',
        string='Attachments',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('valid', 'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='Status', compute='_compute_state', store=True)
    note = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
    )

    @api.depends('expiry_date')
    def _compute_state(self):
        today = fields.Date.today()
        for doc in self:
            if not doc.expiry_date:
                doc.state = 'valid'
            elif doc.expiry_date < today:
                doc.state = 'expired'
            elif doc.expiry_date <= today + timedelta(days=doc.document_type_id.expiry_warning_days or 30):
                doc.state = 'expiring'
            else:
                doc.state = 'valid'

    def _cron_check_document_expiry(self):
        """Scheduled action to check for expiring documents and notify HR."""
        today = fields.Date.today()
        expiring_docs = self.search([
            ('expiry_date', '!=', False),
            ('expiry_date', '<=', today + timedelta(days=30)),
            ('expiry_date', '>=', today),
        ])
        for doc in expiring_docs:
            days_left = (doc.expiry_date - today).days
            doc.activity_schedule(
                'mail.mail_activity_data_warning',
                date_deadline=doc.expiry_date,
                summary=f'{doc.name} expires in {days_left} days',
                user_id=doc.employee_id.parent_id.user_id.id or self.env.ref('base.user_admin').id,
            )
