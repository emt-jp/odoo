# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class RestaurantOrder(models.Model):
    _name = 'restaurant.order'
    _description = 'Restaurant Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char('Order Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    table_id = fields.Many2one('restaurant.table', string='Table', tracking=True)
    floor_id = fields.Many2one('restaurant.floor', string='Floor', related='table_id.floor_id', store=True, readonly=True)

    order_type = fields.Selection([
        ('dine_in', 'Dine In'),
        ('takeout', 'Takeout'),
        ('delivery', 'Delivery'),
    ], string='Order Type', required=True, default='dine_in', tracking=True)

    customer_id = fields.Many2one('res.partner', string='Customer')
    customer_name = fields.Char('Customer Name')
    customer_phone = fields.Char('Phone')
    delivery_address = fields.Text('Delivery Address')

    waiter_id = fields.Many2one('res.users', string='Waiter/Server', default=lambda self: self.env.user, tracking=True)

    order_date = fields.Datetime('Order Date', required=True, default=fields.Datetime.now, tracking=True)
    kitchen_time = fields.Datetime('Sent to Kitchen', readonly=True)
    ready_time = fields.Datetime('Ready Time', readonly=True)
    served_time = fields.Datetime('Served Time', readonly=True)
    closed_time = fields.Datetime('Closed Time', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'In Kitchen'),
        ('ready', 'Ready'),
        ('served', 'Served'),
        ('done', 'Done'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    line_ids = fields.One2many('restaurant.order.line', 'order_id', string='Order Lines')

    # Pricing
    subtotal = fields.Monetary('Subtotal', compute='_compute_amounts', store=True, currency_field='currency_id')
    tax_amount = fields.Monetary('Tax', compute='_compute_amounts', store=True, currency_field='currency_id')
    discount_amount = fields.Monetary('Discount', currency_field='currency_id')
    discount_percent = fields.Float('Discount %', digits=(5, 2))
    total_amount = fields.Monetary('Total', compute='_compute_amounts', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Payment
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mobile', 'Mobile Payment'),
        ('online', 'Online Payment'),
    ], string='Payment Method')
    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
    ], string='Payment Status', default='unpaid', compute='_compute_payment_status', store=True)

    paid_amount = fields.Monetary('Paid Amount', currency_field='currency_id')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)

    # Additional info
    guest_count = fields.Integer('Number of Guests', default=1)
    notes = fields.Text('Special Instructions')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
    ], string='Priority', default='0')

    # Timing
    preparation_time = fields.Integer('Est. Prep Time (min)', compute='_compute_preparation_time', store=True)
    actual_prep_time = fields.Integer('Actual Prep Time (min)', compute='_compute_actual_prep_time')

    @api.depends('line_ids', 'line_ids.price_subtotal', 'line_ids.tax_amount', 'discount_amount', 'discount_percent')
    def _compute_amounts(self):
        for order in self:
            subtotal = sum(order.line_ids.mapped('price_subtotal'))
            tax_total = sum(order.line_ids.mapped('tax_amount'))

            discount = order.discount_amount
            if order.discount_percent > 0:
                discount = subtotal * (order.discount_percent / 100)

            order.subtotal = subtotal
            order.tax_amount = tax_total
            order.total_amount = subtotal + tax_total - discount

    @api.depends('total_amount', 'paid_amount')
    def _compute_payment_status(self):
        for order in self:
            if order.paid_amount >= order.total_amount and order.total_amount > 0:
                order.payment_status = 'paid'
            elif order.paid_amount > 0:
                order.payment_status = 'partial'
            else:
                order.payment_status = 'unpaid'

    @api.depends('line_ids', 'line_ids.menu_item_id', 'line_ids.menu_item_id.preparation_time')
    def _compute_preparation_time(self):
        for order in self:
            if order.line_ids:
                order.preparation_time = max(order.line_ids.mapped('menu_item_id.preparation_time') or [15])
            else:
                order.preparation_time = 0

    @api.depends('kitchen_time', 'ready_time')
    def _compute_actual_prep_time(self):
        for order in self:
            if order.kitchen_time and order.ready_time:
                delta = order.ready_time - order.kitchen_time
                order.actual_prep_time = int(delta.total_seconds() / 60)
            else:
                order.actual_prep_time = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('restaurant.order') or _('New')
        orders = super().create(vals_list)
        return orders

    def action_confirm(self):
        for order in self:
            if not order.line_ids:
                raise UserError(_('Cannot confirm an order without items.'))
            order.write({'state': 'confirmed'})
            if order.table_id:
                order.table_id.write({'status': 'occupied', 'current_order_id': order.id})

    def action_send_to_kitchen(self):
        self.write({
            'state': 'preparing',
            'kitchen_time': fields.Datetime.now(),
        })

    def action_mark_ready(self):
        self.write({
            'state': 'ready',
            'ready_time': fields.Datetime.now(),
        })

    def action_mark_served(self):
        self.write({
            'state': 'served',
            'served_time': fields.Datetime.now(),
        })

    def action_mark_done(self):
        self.write({
            'state': 'done',
            'closed_time': fields.Datetime.now(),
        })
        if self.table_id:
            self.table_id.write({'status': 'available', 'current_order_id': False})

    def action_process_payment(self):
        for order in self:
            if order.payment_status != 'paid':
                raise UserError(_('Please complete payment first.'))
            order.write({
                'state': 'paid',
                'closed_time': fields.Datetime.now(),
            })
            if order.table_id:
                order.table_id.write({'status': 'cleaning', 'current_order_id': False})

    def action_cancel(self):
        if self.state not in ['draft', 'confirmed']:
            raise UserError(_('Cannot cancel orders that are being prepared or completed.'))
        self.write({'state': 'cancelled'})
        if self.table_id and self.table_id.current_order_id == self:
            self.table_id.write({'status': 'available', 'current_order_id': False})


class RestaurantOrderLine(models.Model):
    _name = 'restaurant.order.line'
    _description = 'Restaurant Order Line'
    _order = 'order_id, sequence, id'

    order_id = fields.Many2one('restaurant.order', string='Order', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    menu_item_id = fields.Many2one('menu.item', string='Menu Item', required=True, ondelete='restrict')
    name = fields.Char('Description', related='menu_item_id.name', store=True)

    quantity = fields.Float('Quantity', default=1.0, digits=(12, 2), required=True)
    price_unit = fields.Monetary('Unit Price', required=True, currency_field='currency_id')
    price_subtotal = fields.Monetary('Subtotal', compute='_compute_amount', store=True, currency_field='currency_id')
    tax_ids = fields.Many2many('account.tax', string='Taxes', related='menu_item_id.tax_ids')
    tax_amount = fields.Monetary('Tax Amount', compute='_compute_amount', store=True, currency_field='currency_id')
    price_total = fields.Monetary('Total', compute='_compute_amount', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', store=True)

    notes = fields.Text('Special Instructions')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
    ], string='Status', default='pending')

    @api.depends('quantity', 'price_unit', 'tax_ids')
    def _compute_amount(self):
        for line in self:
            subtotal = line.quantity * line.price_unit
            line.price_subtotal = subtotal

            # Simple tax calculation
            tax_amount = 0.0
            if line.tax_ids:
                for tax in line.tax_ids:
                    if tax.amount_type == 'percent':
                        tax_amount += subtotal * (tax.amount / 100.0)

            line.tax_amount = tax_amount
            line.price_total = subtotal + tax_amount

    @api.onchange('menu_item_id')
    def _onchange_menu_item(self):
        if self.menu_item_id:
            self.price_unit = self.menu_item_id.list_price
