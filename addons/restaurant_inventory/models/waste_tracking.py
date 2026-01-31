# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WasteTracking(models.Model):
    _name = 'waste.tracking'
    _description = 'Restaurant Waste Tracking'
    _order = 'date desc'

    name = fields.Char('Reference', required=True, copy=False, readonly=True, default='New')
    date = fields.Datetime('Date', required=True, default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Reported By', default=lambda self: self.env.user, required=True)

    # Waste lines
    waste_line_ids = fields.One2many('waste.tracking.line', 'waste_id', string='Waste Items')

    # Totals
    total_items = fields.Integer('Total Items', compute='_compute_totals')
    total_value = fields.Monetary('Total Value', compute='_compute_totals', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True)

    notes = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('waste.tracking') or 'New'
        return super().create(vals)

    @api.depends('waste_line_ids.quantity', 'waste_line_ids.waste_value')
    def _compute_totals(self):
        for waste in self:
            waste.total_items = len(waste.waste_line_ids)
            waste.total_value = sum(waste.waste_line_ids.mapped('waste_value'))

    def action_confirm(self):
        """Confirm waste and create stock moves to scrap location"""
        for waste in self:
            if waste.state != 'draft':
                continue

            # Get scrap/waste location
            scrap_location = self.env.ref('stock.stock_location_scrapped', raise_if_not_found=False)
            if not scrap_location:
                scrap_location = self.env['stock.location'].search([('scrap_location', '=', True)], limit=1)

            stock_location = self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)

            if not stock_location or not scrap_location:
                raise models.UserError('Scrap location not configured!')

            # Create stock moves for each waste item
            for line in waste.waste_line_ids:
                self.env['stock.move'].create({
                    'name': f'Waste: {line.product_id.name} - {line.reason}',
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.uom_id.id,
                    'location_id': stock_location.id,
                    'location_dest_id': scrap_location.id,
                    'origin': waste.name,
                })._action_confirm()

            waste.state = 'confirmed'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_draft(self):
        self.state = 'draft'


class WasteTrackingLine(models.Model):
    _name = 'waste.tracking.line'
    _description = 'Waste Tracking Line'

    waste_id = fields.Many2one('waste.tracking', string='Waste Record', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)

    quantity = fields.Float('Quantity', required=True, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='Unit', required=True)

    # Cost
    unit_cost = fields.Monetary('Unit Cost', related='product_id.standard_price', readonly=True, currency_field='currency_id')
    waste_value = fields.Monetary('Waste Value', compute='_compute_waste_value', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='waste_id.currency_id')

    # Reason
    reason = fields.Selection([
        ('expired', 'Expired/Spoiled'),
        ('damaged', 'Damaged'),
        ('overproduction', 'Overproduction'),
        ('prep_waste', 'Preparation Waste'),
        ('customer_return', 'Customer Return'),
        ('contaminated', 'Contaminated'),
        ('other', 'Other'),
    ], string='Reason', required=True)

    notes = fields.Char('Notes')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id

    @api.depends('quantity', 'unit_cost')
    def _compute_waste_value(self):
        for line in self:
            line.waste_value = line.quantity * line.unit_cost
