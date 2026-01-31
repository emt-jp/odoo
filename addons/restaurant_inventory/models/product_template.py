# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Restaurant-specific fields
    is_ingredient = fields.Boolean('Is Ingredient', default=False)
    is_consumable_supply = fields.Boolean('Is Consumable Supply', default=False)

    # Storage information
    storage_location = fields.Selection([
        ('dry', 'Dry Storage'),
        ('refrigerated', 'Refrigerated'),
        ('frozen', 'Frozen'),
        ('bar', 'Bar'),
        ('other', 'Other'),
    ], string='Storage Location')

    # Expiration tracking
    use_expiration_date = fields.Boolean('Track Expiration', default=False)
    expiration_days = fields.Integer('Shelf Life (Days)', help='Days until expiration after receipt')
    alert_days_before_expiry = fields.Integer('Alert Days Before Expiry', default=7)

    # Reordering
    min_stock_level = fields.Float('Minimum Stock Level', digits='Product Unit of Measure')
    max_stock_level = fields.Float('Maximum Stock Level', digits='Product Unit of Measure')
    reorder_point = fields.Float('Reorder Point', digits='Product Unit of Measure')
    reorder_quantity = fields.Float('Reorder Quantity', digits='Product Unit of Measure')

    # Supplier info
    default_supplier_id = fields.Many2one('res.partner', string='Default Supplier', domain=[('supplier_rank', '>', 0)])
    lead_time_days = fields.Integer('Lead Time (Days)', default=3)

    # Cost tracking
    last_purchase_price = fields.Float('Last Purchase Price', digits='Product Price')
    average_cost = fields.Float('Average Cost', compute='_compute_average_cost', store=True, digits='Product Price')

    # Usage statistics
    total_consumed = fields.Float('Total Consumed', compute='_compute_consumption_stats', digits='Product Unit of Measure')
    consumption_last_30_days = fields.Float('Consumed (Last 30 Days)', compute='_compute_consumption_stats', digits='Product Unit of Measure')
    waste_last_30_days = fields.Float('Waste (Last 30 Days)', compute='_compute_waste_stats', digits='Product Unit of Measure')

    # Stock alerts
    is_low_stock = fields.Boolean('Low Stock', compute='_compute_stock_alerts', store=True)
    is_out_of_stock = fields.Boolean('Out of Stock', compute='_compute_stock_alerts', store=True)
    days_until_stockout = fields.Integer('Days Until Stockout', compute='_compute_stock_alerts')

    # Recipe/BOM related
    is_prepared_dish = fields.Boolean('Is Prepared Dish', default=False)
    recipe_id = fields.Many2one('restaurant.recipe', string='Recipe')
    recipe_yield = fields.Float('Recipe Yield (Servings)', default=1.0)

    @api.depends('stock_quant_ids.quantity', 'stock_quant_ids.location_id')
    def _compute_average_cost(self):
        for product in self:
            quants = product.stock_quant_ids.filtered(
                lambda q: q.location_id.usage == 'internal' and q.quantity > 0
            )
            if quants:
                total_value = sum(q.quantity * q.inventory_value / q.quantity if q.quantity else 0 for q in quants)
                total_qty = sum(q.quantity for q in quants)
                product.average_cost = total_value / total_qty if total_qty else 0
            else:
                product.average_cost = 0

    @api.depends('stock_move_ids')
    def _compute_consumption_stats(self):
        for product in self:
            thirty_days_ago = fields.Datetime.now() - timedelta(days=30)

            # Get consumption moves (from stock to production/customer)
            consumption_moves = product.stock_move_ids.filtered(
                lambda m: m.state == 'done'
                and m.location_id.usage == 'internal'
                and m.location_dest_id.usage in ('production', 'customer')
                and m.date >= thirty_days_ago
            )

            product.consumption_last_30_days = sum(consumption_moves.mapped('product_uom_qty'))
            product.total_consumed = sum(product.stock_move_ids.filtered(
                lambda m: m.state == 'done'
                and m.location_id.usage == 'internal'
            ).mapped('product_uom_qty'))

    def _compute_waste_stats(self):
        for product in self:
            thirty_days_ago = fields.Datetime.now() - timedelta(days=30)
            waste_moves = product.stock_move_ids.filtered(
                lambda m: m.state == 'done'
                and m.location_dest_id.usage == 'inventory'  # Scrapped/wasted
                and m.date >= thirty_days_ago
            )
            product.waste_last_30_days = sum(waste_moves.mapped('product_uom_qty'))

    @api.depends('qty_available', 'min_stock_level', 'consumption_last_30_days')
    def _compute_stock_alerts(self):
        for product in self:
            # Check if out of stock
            product.is_out_of_stock = product.qty_available <= 0

            # Check if low stock
            product.is_low_stock = (
                not product.is_out_of_stock
                and product.min_stock_level
                and product.qty_available <= product.min_stock_level
            )

            # Calculate days until stockout
            if product.consumption_last_30_days > 0:
                daily_consumption = product.consumption_last_30_days / 30
                if daily_consumption > 0:
                    product.days_until_stockout = int(product.qty_available / daily_consumption)
                else:
                    product.days_until_stockout = 9999
            else:
                product.days_until_stockout = 9999

    def action_create_purchase_order(self):
        """Quick action to create purchase order for this product"""
        self.ensure_one()

        if not self.default_supplier_id:
            raise models.UserError('No default supplier set for this product!')

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.default_supplier_id.id,
            'order_line': [(0, 0, {
                'product_id': self.product_variant_ids[0].id,
                'product_qty': self.reorder_quantity or 1.0,
                'price_unit': self.last_purchase_price or 0,
            })],
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order',
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Lot/batch specific expiration
    expiration_date = fields.Date('Expiration Date')
    is_expired = fields.Boolean('Is Expired', compute='_compute_is_expired')
    days_until_expiry = fields.Integer('Days Until Expiry', compute='_compute_is_expired')

    @api.depends('expiration_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for product in self:
            if product.expiration_date:
                product.is_expired = product.expiration_date < today
                delta = (product.expiration_date - today).days
                product.days_until_expiry = delta if delta >= 0 else 0
            else:
                product.is_expired = False
                product.days_until_expiry = 9999
