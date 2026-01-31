# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class RestaurantFloor(models.Model):
    _name = 'restaurant.floor'
    _description = 'Restaurant Floor'
    _order = 'sequence, name'

    name = fields.Char('Floor Name', required=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    table_ids = fields.One2many('restaurant.table', 'floor_id', string='Tables')
    table_count = fields.Integer('Total Tables', compute='_compute_table_stats', store=True)
    available_tables = fields.Integer('Available Tables', compute='_compute_table_stats')
    occupied_tables = fields.Integer('Occupied Tables', compute='_compute_table_stats')
    reserved_tables = fields.Integer('Reserved Tables', compute='_compute_table_stats')
    total_capacity = fields.Integer('Total Capacity', compute='_compute_table_stats', store=True)

    @api.depends('table_ids', 'table_ids.status', 'table_ids.capacity')
    def _compute_table_stats(self):
        for floor in self:
            tables = floor.table_ids
            floor.table_count = len(tables)
            floor.available_tables = len(tables.filtered(lambda t: t.status == 'available'))
            floor.occupied_tables = len(tables.filtered(lambda t: t.status == 'occupied'))
            floor.reserved_tables = len(tables.filtered(lambda t: t.status == 'reserved'))
            floor.total_capacity = sum(tables.mapped('capacity'))
