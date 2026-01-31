# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RestaurantOrder(models.Model):
    _inherit = 'restaurant.order'

    # Inventory tracking
    stock_move_ids = fields.One2many('stock.move', 'restaurant_order_id', string='Stock Moves')
    inventory_consumed = fields.Boolean('Inventory Consumed', default=False, copy=False)

    def action_confirm(self):
        """Override to consume inventory when order is confirmed"""
        res = super().action_confirm()

        for order in self:
            if not order.inventory_consumed:
                order._consume_inventory()

        return res

    def _consume_inventory(self):
        """Consume inventory based on order items and their recipes"""
        self.ensure_one()

        for line in self.order_line_ids:
            menu_item = line.product_id

            # Check if this menu item has a recipe
            recipe = self.env['restaurant.recipe'].search([
                ('menu_item_id', '=', menu_item.id)
            ], limit=1)

            if recipe:
                # Consume ingredients based on quantity ordered
                moves = recipe.action_consume_ingredients(quantity=line.quantity)

                # Link moves to this order
                for move in moves:
                    move.restaurant_order_id = self.id
                    move.recipe_id = recipe.id

        self.inventory_consumed = True


class RestaurantOrderLine(models.Model):
    _inherit = 'restaurant.order.line'

    # Show if ingredients are available
    ingredients_available = fields.Boolean('Ingredients Available', compute='_compute_ingredients_available')

    @api.depends('product_id', 'quantity')
    def _compute_ingredients_available(self):
        for line in self:
            recipe = self.env['restaurant.recipe'].search([
                ('menu_item_id', '=', line.product_id.id)
            ], limit=1)

            if recipe:
                # Check if all ingredients have sufficient stock
                all_available = all(
                    ing.available_qty >= (ing.quantity * line.quantity)
                    for ing in recipe.ingredient_ids
                )
                line.ingredients_available = all_available
            else:
                # No recipe, assume available
                line.ingredients_available = True
