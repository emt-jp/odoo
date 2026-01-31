# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class RestaurantReservation(models.Model):
    _name = 'restaurant.reservation'
    _description = 'Restaurant Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reservation_date desc, reservation_time desc'

    name = fields.Char('Reservation Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    customer_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    customer_name = fields.Char('Customer Name', required=True, tracking=True)
    customer_phone = fields.Char('Phone', required=True, tracking=True)
    customer_email = fields.Char('Email')

    reservation_date = fields.Date('Reservation Date', required=True, tracking=True)
    reservation_time = fields.Float('Time', required=True, help='Time in 24h format (e.g., 18.5 for 6:30 PM)', tracking=True)
    duration_hours = fields.Float('Duration (hours)', default=2.0)

    guest_count = fields.Integer('Number of Guests', required=True, default=2, tracking=True)
    table_id = fields.Many2one('restaurant.table', string='Assigned Table')
    floor_id = fields.Many2one('restaurant.floor', string='Floor', related='table_id.floor_id', store=True, readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('seated', 'Seated'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    special_requests = fields.Text('Special Requests')
    occasion = fields.Selection([
        ('birthday', 'Birthday'),
        ('anniversary', 'Anniversary'),
        ('business', 'Business Meeting'),
        ('other', 'Other'),
    ], string='Occasion')

    created_by_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    order_id = fields.Many2one('restaurant.order', string='Related Order', readonly=True)

    reminder_sent = fields.Boolean('Reminder Sent', default=False)
    notes = fields.Text('Internal Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('restaurant.reservation') or _('New')
        reservations = super().create(vals_list)
        return reservations

    @api.constrains('guest_count')
    def _check_guest_count(self):
        for reservation in self:
            if reservation.guest_count < 1:
                raise ValidationError(_('Number of guests must be at least 1.'))

    @api.constrains('table_id', 'guest_count')
    def _check_table_capacity(self):
        for reservation in self:
            if reservation.table_id and reservation.guest_count > reservation.table_id.capacity:
                raise ValidationError(_(
                    'The selected table can accommodate maximum %s guests, but you have %s guests.'
                ) % (reservation.table_id.capacity, reservation.guest_count))

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        if self.table_id:
            self.table_id.write({'status': 'reserved'})

    def action_seat(self):
        if not self.table_id:
            raise ValidationError(_('Please assign a table first.'))

        # Create order automatically
        order = self.env['restaurant.order'].create({
            'table_id': self.table_id.id,
            'order_type': 'dine_in',
            'customer_id': self.customer_id.id if self.customer_id else False,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'guest_count': self.guest_count,
            'notes': self.special_requests,
        })

        self.write({
            'state': 'seated',
            'order_id': order.id,
        })
        self.table_id.write({'status': 'occupied', 'current_order_id': order.id})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'restaurant.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_mark_no_show(self):
        self.write({'state': 'no_show'})
        if self.table_id and self.table_id.status == 'reserved':
            self.table_id.write({'status': 'available'})

    def action_cancel(self):
        if self.state == 'seated':
            raise ValidationError(_('Cannot cancel reservation after guests are seated.'))
        self.write({'state': 'cancelled'})
        if self.table_id and self.table_id.status == 'reserved':
            self.table_id.write({'status': 'available'})
