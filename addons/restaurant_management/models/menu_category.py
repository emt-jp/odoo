# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class MenuCategory(models.Model):
    _name = 'menu.category'
    _description = 'Menu Category'
    _order = 'sequence, name'

    name = fields.Char('Category Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    parent_id = fields.Many2one('menu.category', string='Parent Category', ondelete='restrict')
    child_ids = fields.One2many('menu.category', 'parent_id', string='Subcategories')
    menu_item_ids = fields.One2many('menu.item', 'category_id', string='Menu Items')
    item_count = fields.Integer('Items Count', compute='_compute_item_count', store=True)
    image = fields.Binary('Category Image')
    description = fields.Text('Description', translate=True)
    color = fields.Integer('Color Index', default=0)

    @api.depends('menu_item_ids')
    def _compute_item_count(self):
        for category in self:
            category.item_count = len(category.menu_item_ids)

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise models.ValidationError(_('You cannot create recursive categories.'))
