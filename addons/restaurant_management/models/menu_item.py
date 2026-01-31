# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MenuItem(models.Model):
    _name = 'menu.item'
    _description = 'Menu Item'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'category_id, sequence, name'

    name = fields.Char('Item Name', required=True, translate=True, tracking=True)
    description = fields.Text('Description', translate=True)
    category_id = fields.Many2one('menu.category', string='Category', required=True, ondelete='restrict', tracking=True)
    sequence = fields.Integer('Sequence', default=10)

    # Pricing
    list_price = fields.Monetary('Sale Price', required=True, default=0.0, currency_field='currency_id', tracking=True)
    cost_price = fields.Monetary('Cost Price', currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    tax_ids = fields.Many2many('account.tax', string='Taxes')

    # Product details
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict')
    image = fields.Binary('Image', attachment=True)

    # Availability
    active = fields.Boolean('Active', default=True, tracking=True)
    available = fields.Boolean('Available for Order', default=True, tracking=True)
    available_for_takeout = fields.Boolean('Available for Takeout', default=True)
    available_for_delivery = fields.Boolean('Available for Delivery', default=True)

    # Dietary info
    is_vegetarian = fields.Boolean('Vegetarian')
    is_vegan = fields.Boolean('Vegan')
    is_gluten_free = fields.Boolean('Gluten Free')
    is_spicy = fields.Boolean('Spicy')
    spice_level = fields.Selection([
        ('1', 'Mild'),
        ('2', 'Medium'),
        ('3', 'Hot'),
        ('4', 'Extra Hot'),
    ], string='Spice Level')

    allergen_info = fields.Text('Allergen Information')
    preparation_time = fields.Integer('Preparation Time (minutes)', default=15)

    # Stats
    total_orders = fields.Integer('Times Ordered', compute='_compute_stats', store=True)
    total_revenue = fields.Monetary('Total Revenue', compute='_compute_stats', store=True, currency_field='currency_id')
    avg_rating = fields.Float('Average Rating', compute='_compute_stats', digits=(3, 2))

    # Stock management
    track_stock = fields.Boolean('Track Stock')
    current_stock = fields.Float('Current Stock', digits=(12, 2))
    min_stock_level = fields.Float('Minimum Stock Level', digits=(12, 2))
    out_of_stock = fields.Boolean('Out of Stock', compute='_compute_out_of_stock', store=True)

    @api.depends('track_stock', 'current_stock', 'min_stock_level')
    def _compute_out_of_stock(self):
        for item in self:
            if item.track_stock:
                item.out_of_stock = item.current_stock <= item.min_stock_level
            else:
                item.out_of_stock = False

    @api.depends('name')
    def _compute_stats(self):
        for item in self:
            # This would be computed from order lines
            item.total_orders = 0
            item.total_revenue = 0.0
            item.avg_rating = 0.0

    @api.constrains('list_price')
    def _check_price(self):
        for item in self:
            if item.list_price < 0:
                raise ValidationError(_('Sale price cannot be negative.'))

    def action_toggle_availability(self):
        for item in self:
            item.available = not item.available
