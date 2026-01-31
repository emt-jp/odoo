# -*- coding: utf-8 -*-
from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    # Link to restaurant order if this move was triggered by an order
    restaurant_order_id = fields.Many2one('restaurant.order', string='Restaurant Order', ondelete='set null')
    recipe_id = fields.Many2one('restaurant.recipe', string='Recipe', ondelete='set null')
    is_waste = fields.Boolean('Is Waste/Scrap', compute='_compute_is_waste', store=True)

    @api.depends('location_dest_id')
    def _compute_is_waste(self):
        for move in self:
            move.is_waste = move.location_dest_id.scrap_location or move.location_dest_id.usage == 'inventory'
