# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RestaurantTable(models.Model):
    _name = 'restaurant.table'
    _description = 'Restaurant Table'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'floor_id, sequence, name'

    name = fields.Char('Table Number', required=True, tracking=True)
    floor_id = fields.Many2one('restaurant.floor', string='Floor', required=True, ondelete='restrict')
    sequence = fields.Integer('Sequence', default=10)
    capacity = fields.Integer('Capacity (Seats)', required=True, default=4, tracking=True)
    status = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('cleaning', 'Cleaning'),
        ('maintenance', 'Maintenance'),
    ], string='Status', default='available', required=True, tracking=True)

    shape = fields.Selection([
        ('square', 'Square'),
        ('rectangle', 'Rectangle'),
        ('round', 'Round'),
        ('oval', 'Oval'),
    ], string='Table Shape', default='square')

    position_x = fields.Integer('Position X', help='X coordinate for floor plan')
    position_y = fields.Integer('Position Y', help='Y coordinate for floor plan')

    current_order_id = fields.Many2one('restaurant.order', string='Current Order', readonly=True)
    active = fields.Boolean('Active', default=True)
    notes = fields.Text('Notes')

    # Stats
    total_orders = fields.Integer('Total Orders', compute='_compute_stats', store=True)
    total_revenue = fields.Monetary('Total Revenue', compute='_compute_stats', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.depends('name')
    def _compute_stats(self):
        for table in self:
            orders = self.env['restaurant.order'].search([('table_id', '=', table.id), ('state', 'in', ['done', 'paid'])])
            table.total_orders = len(orders)
            table.total_revenue = sum(orders.mapped('total_amount'))

    @api.constrains('capacity')
    def _check_capacity(self):
        for table in self:
            if table.capacity < 1:
                raise ValidationError(_('Table capacity must be at least 1 person.'))

    def action_set_available(self):
        self.write({'status': 'available', 'current_order_id': False})

    def action_set_occupied(self):
        self.write({'status': 'occupied'})

    def action_set_cleaning(self):
        self.write({'status': 'cleaning'})
