# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RestaurantRecipe(models.Model):
    _name = 'restaurant.recipe'
    _description = 'Restaurant Recipe (Bill of Materials)'
    _order = 'name'

    name = fields.Char('Recipe Name', required=True)
    menu_item_id = fields.Many2one('menu.item', string='Menu Item', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Finished Product', required=True)

    # Recipe details
    serving_size = fields.Float('Serving Size', default=1.0, required=True)
    yield_quantity = fields.Float('Yield Quantity', default=1.0, help='Number of servings this recipe produces')
    prep_time = fields.Float('Prep Time (minutes)')
    cook_time = fields.Float('Cook Time (minutes)')
    total_time = fields.Float('Total Time (minutes)', compute='_compute_total_time', store=True)

    # Recipe lines (ingredients)
    ingredient_ids = fields.One2many('restaurant.recipe.line', 'recipe_id', string='Ingredients')

    # Cost calculation
    total_cost = fields.Monetary('Total Cost', compute='_compute_costs', store=True, currency_field='currency_id')
    cost_per_serving = fields.Monetary('Cost Per Serving', compute='_compute_costs', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Instructions
    instructions = fields.Html('Cooking Instructions')
    notes = fields.Text('Notes')

    # Categorization
    category = fields.Selection([
        ('appetizer', 'Appetizer'),
        ('main', 'Main Course'),
        ('side', 'Side Dish'),
        ('dessert', 'Dessert'),
        ('beverage', 'Beverage'),
        ('sauce', 'Sauce/Condiment'),
    ], string='Category')

    active = fields.Boolean('Active', default=True)

    @api.depends('prep_time', 'cook_time')
    def _compute_total_time(self):
        for recipe in self:
            recipe.total_time = (recipe.prep_time or 0) + (recipe.cook_time or 0)

    @api.depends('ingredient_ids.subtotal', 'yield_quantity')
    def _compute_costs(self):
        for recipe in self:
            recipe.total_cost = sum(recipe.ingredient_ids.mapped('subtotal'))
            recipe.cost_per_serving = recipe.total_cost / recipe.yield_quantity if recipe.yield_quantity else 0

    def action_consume_ingredients(self, quantity=1.0):
        """
        Consume ingredients from inventory when a dish is ordered.
        This creates stock moves for all ingredients.
        """
        self.ensure_one()

        # Get production location (where ingredients are consumed)
        production_location = self.env.ref('stock.location_production', raise_if_not_found=False)
        if not production_location:
            production_location = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)

        # Get stock location (where ingredients come from)
        stock_location = self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)

        if not stock_location or not production_location:
            raise models.UserError('Production or stock location not configured!')

        moves = []
        for ingredient in self.ingredient_ids:
            # Calculate quantity needed based on number of servings
            qty_needed = ingredient.quantity * quantity

            move = self.env['stock.move'].create({
                'name': f'Consume: {ingredient.product_id.name} for {self.name}',
                'product_id': ingredient.product_id.id,
                'product_uom_qty': qty_needed,
                'product_uom': ingredient.uom_id.id,
                'location_id': stock_location.id,
                'location_dest_id': production_location.id,
                'origin': f'Recipe: {self.name}',
            })
            move._action_confirm()
            move._action_assign()
            moves.append(move)

        return moves

    def action_view_cost_analysis(self):
        """Open cost analysis view for this recipe"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Cost Analysis: {self.name}',
            'res_model': 'restaurant.recipe',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class RestaurantRecipeLine(models.Model):
    _name = 'restaurant.recipe.line'
    _description = 'Recipe Ingredient Line'
    _order = 'sequence, id'

    sequence = fields.Integer('Sequence', default=10)
    recipe_id = fields.Many2one('restaurant.recipe', string='Recipe', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product',
        string='Ingredient',
        required=True,
        domain="[('is_ingredient', '=', True)]"
    )

    # Quantity
    quantity = fields.Float('Quantity', required=True, default=1.0, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)

    # Cost
    unit_cost = fields.Monetary('Unit Cost', related='product_id.standard_price', readonly=True, currency_field='currency_id')
    subtotal = fields.Monetary('Subtotal', compute='_compute_subtotal', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='recipe_id.currency_id')

    # Stock availability
    available_qty = fields.Float('Available Quantity', related='product_id.qty_available', readonly=True)
    is_available = fields.Boolean('Is Available', compute='_compute_is_available')

    # Notes
    preparation_notes = fields.Char('Preparation Notes', help='e.g., diced, chopped, minced')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id

    @api.depends('quantity', 'unit_cost')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_cost

    @api.depends('quantity', 'available_qty')
    def _compute_is_available(self):
        for line in self:
            line.is_available = line.available_qty >= line.quantity
