# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockAlert(models.Model):
    _name = 'stock.alert'
    _description = 'Stock Alert/Notification'
    _order = 'priority desc, create_date desc'

    name = fields.Char('Alert', compute='_compute_name', store=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')

    alert_type = fields.Selection([
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('overstock', 'Overstock'),
    ], string='Alert Type', required=True)

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Critical'),
    ], string='Priority', default='1')

    current_qty = fields.Float('Current Quantity', digits='Product Unit of Measure')
    threshold_qty = fields.Float('Threshold Quantity', digits='Product Unit of Measure')
    recommended_order_qty = fields.Float('Recommended Order Qty', digits='Product Unit of Measure')

    state = fields.Selection([
        ('active', 'Active'),
        ('resolved', 'Resolved'),
        ('ignored', 'Ignored'),
    ], string='Status', default='active', required=True)

    resolved_date = fields.Datetime('Resolved Date')
    resolved_by = fields.Many2one('res.users', string='Resolved By')
    notes = fields.Text('Notes')

    # For expiration alerts
    expiration_date = fields.Date('Expiration Date')
    days_until_expiry = fields.Integer('Days Until Expiry')

    @api.depends('alert_type', 'product_id.name')
    def _compute_name(self):
        type_labels = dict(self._fields['alert_type'].selection)
        for alert in self:
            alert.name = f"{type_labels.get(alert.alert_type)}: {alert.product_id.name}"

    def action_create_purchase_order(self):
        """Quick action to create purchase order from alert"""
        self.ensure_one()
        return self.product_id.product_tmpl_id.action_create_purchase_order()

    def action_resolve(self):
        """Mark alert as resolved"""
        self.write({
            'state': 'resolved',
            'resolved_date': fields.Datetime.now(),
            'resolved_by': self.env.user.id,
        })

    def action_ignore(self):
        """Ignore this alert"""
        self.state = 'ignored'

    @api.model
    def _generate_stock_alerts(self):
        """
        Cron job to generate stock alerts based on product thresholds.
        This should be run daily.
        """
        # Clear old resolved alerts (older than 30 days)
        old_alerts = self.search([
            ('state', 'in', ['resolved', 'ignored']),
            ('create_date', '<', fields.Datetime.now() - fields.Datetime.timedelta(days=30))
        ])
        old_alerts.unlink()

        # Get all products with inventory tracking
        products = self.env['product.product'].search([
            ('type', '=', 'product'),
            '|', ('is_ingredient', '=', True),
            ('is_consumable_supply', '=', True)
        ])

        for product in products:
            product_tmpl = product.product_tmpl_id

            # Check for out of stock
            if product.qty_available <= 0:
                self._create_alert_if_not_exists(product, 'out_of_stock', '3', {
                    'current_qty': product.qty_available,
                    'threshold_qty': 0,
                    'recommended_order_qty': product_tmpl.reorder_quantity or 1,
                })

            # Check for low stock
            elif product_tmpl.min_stock_level and product.qty_available <= product_tmpl.min_stock_level:
                self._create_alert_if_not_exists(product, 'low_stock', '2', {
                    'current_qty': product.qty_available,
                    'threshold_qty': product_tmpl.min_stock_level,
                    'recommended_order_qty': product_tmpl.reorder_quantity or 1,
                })

            # Check for expiration
            if product_tmpl.use_expiration_date and product.expiration_date:
                days_until_expiry = (product.expiration_date - fields.Date.today()).days

                if days_until_expiry < 0:
                    # Expired
                    self._create_alert_if_not_exists(product, 'expired', '3', {
                        'expiration_date': product.expiration_date,
                        'days_until_expiry': days_until_expiry,
                    })
                elif days_until_expiry <= product_tmpl.alert_days_before_expiry:
                    # Expiring soon
                    self._create_alert_if_not_exists(product, 'expiring_soon', '1', {
                        'expiration_date': product.expiration_date,
                        'days_until_expiry': days_until_expiry,
                    })

            # Check for overstock
            if product_tmpl.max_stock_level and product.qty_available >= product_tmpl.max_stock_level:
                self._create_alert_if_not_exists(product, 'overstock', '0', {
                    'current_qty': product.qty_available,
                    'threshold_qty': product_tmpl.max_stock_level,
                })

    def _create_alert_if_not_exists(self, product, alert_type, priority, values):
        """Helper to create alert only if it doesn't already exist"""
        existing = self.search([
            ('product_id', '=', product.id),
            ('alert_type', '=', alert_type),
            ('state', '=', 'active'),
        ], limit=1)

        if not existing:
            values.update({
                'product_id': product.id,
                'alert_type': alert_type,
                'priority': priority,
            })
            self.create(values)
