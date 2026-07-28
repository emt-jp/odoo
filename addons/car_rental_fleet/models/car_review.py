# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TdcCarReview(models.Model):
    """TDC Car Review.

    Stores customer reviews for fleet vehicles. Reviews start in draft state
    and require moderation before being published on the public site.
    Aggregated rating is exposed via fleet.vehicle.average_rating.
    """
    _name = 'tdc.car.review'
    _description = 'TDC Car Review'
    _order = 'create_date desc'
    _rec_name = 'title'

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehicle',
        required=True,
        ondelete='cascade',
        index=True,
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='restrict',
        index=True,
    )
    booking_id = fields.Many2one(
        'fleet.booking',
        string='Related Booking',
        ondelete='set null',
        help='Booking that this review is based on, used to verify ownership',
    )
    # Marketplace fields (emt-jp/tdc Phase 1): attribute the review to the
    # vendor so per-vendor ratings can be aggregated, and let the vendor reply.
    vendor_id = fields.Many2one(
        'res.partner', string='Vendor', index=True,
        help='The vendor who owns the reviewed vehicle (for per-vendor rating).',
    )
    vendor_reply = fields.Text(
        string='Vendor Reply',
        help='Optional public response from the vendor to this review.',
    )
    rating = fields.Integer(
        string='Rating',
        required=True,
        default=5,
        help='Star rating from 1 to 5',
    )
    title = fields.Char(string='Title', required=True)
    content = fields.Text(string='Content')
    language = fields.Char(
        string='Language',
        default='en',
        help='Review language code (e.g. en, ja)',
    )
    verified_booking = fields.Boolean(
        string='Verified Booking',
        default=False,
        help='True if this review is linked to a confirmed booking by the same customer',
    )
    state = fields.Selection([
        ('draft', 'Pending Moderation'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, index=True)

    helpful_count = fields.Integer(string='Helpful Votes', default=0)
    moderation_notes = fields.Text(string='Moderation Notes')

    _sql_constraints = [
        ('rating_range', 'CHECK(rating >= 1 AND rating <= 5)',
         'Rating must be between 1 and 5.'),
    ]

    @api.constrains('rating')
    def _check_rating(self):
        for record in self:
            if record.rating < 1 or record.rating > 5:
                raise ValidationError('Rating must be between 1 and 5.')

    def action_publish(self):
        """Approve and publish a draft review."""
        for record in self:
            record.state = 'published'
            record._recompute_vehicle_rating()
        return True

    def action_reject(self):
        """Reject a pending review."""
        for record in self:
            record.state = 'rejected'
            record._recompute_vehicle_rating()
        return True

    def _recompute_vehicle_rating(self):
        """Recompute average_rating on the linked fleet.vehicle."""
        self.ensure_one()
        if not self.vehicle_id:
            return
        published = self.search([
            ('vehicle_id', '=', self.vehicle_id.id),
            ('state', '=', 'published'),
        ])
        if published:
            avg = sum(r.rating for r in published) / len(published)
        else:
            avg = 0.0
        # Only write if the field exists on fleet.vehicle
        if 'average_rating' in self.vehicle_id._fields:
            self.vehicle_id.sudo().write({'average_rating': avg})

    @api.model
    def create(self, vals):
        record = super().create(vals)
        # Auto-detect verified booking if booking_id provided
        if record.booking_id and record.booking_id.customer_id.id == record.customer_id.id:
            if record.booking_id.state in ('confirmed', 'assigned'):
                record.verified_booking = True
        return record

    def write(self, vals):
        result = super().write(vals)
        if 'state' in vals:
            for record in self:
                record._recompute_vehicle_rating()
        return result
