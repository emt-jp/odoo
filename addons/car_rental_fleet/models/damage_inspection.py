# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class FleetDamageInspection(models.Model):
    _name = 'fleet.damage.inspection'
    _description = 'Vehicle Damage Inspection'
    _order = 'inspection_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Inspection Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True)
    rental_id = fields.Many2one('fleet.rental', string='Rental', tracking=True)

    # Inspection Details
    inspection_type = fields.Selection([
        ('pickup', 'Pickup (Before Rental)'),
        ('return', 'Return (After Rental)'),
        ('periodic', 'Periodic Inspection'),
        ('accident', 'Accident Report'),
    ], string='Inspection Type', required=True, tracking=True)

    inspection_date = fields.Datetime('Inspection Date', required=True, default=fields.Datetime.now, tracking=True)
    inspector_id = fields.Many2one('res.users', string='Inspector', default=lambda self: self.env.user, required=True)
    customer_id = fields.Many2one('res.partner', string='Customer')

    # Vehicle Status at Inspection
    odometer_reading = fields.Integer('Odometer Reading', required=True)
    fuel_level = fields.Selection([
        ('empty', 'Empty'),
        ('quarter', '1/4'),
        ('half', '1/2'),
        ('three_quarter', '3/4'),
        ('full', 'Full'),
    ], string='Fuel Level', required=True, default='full')

    # Overall Condition
    overall_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ], string='Overall Condition', required=True, default='good', tracking=True)

    # Inspection Items
    inspection_line_ids = fields.One2many('fleet.damage.inspection.line', 'inspection_id', string='Inspection Items')

    # Damage Records
    damage_ids = fields.One2many('fleet.damage.record', 'inspection_id', string='Damage Records')
    has_damage = fields.Boolean('Has Damage', compute='_compute_has_damage', store=True)
    total_damage_cost = fields.Monetary('Total Damage Cost', compute='_compute_damage_cost', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Signatures
    inspector_signature = fields.Binary('Inspector Signature')
    customer_signature = fields.Binary('Customer Signature')

    # Photos
    photo_front = fields.Image('Front Photo', max_width=1920, max_height=1080)
    photo_back = fields.Image('Back Photo', max_width=1920, max_height=1080)
    photo_left = fields.Image('Left Side Photo', max_width=1920, max_height=1080)
    photo_right = fields.Image('Right Side Photo', max_width=1920, max_height=1080)
    photo_interior = fields.Image('Interior Photo', max_width=1920, max_height=1080)
    photo_dashboard = fields.Image('Dashboard Photo', max_width=1920, max_height=1080)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
    ], string='Status', default='draft', tracking=True)

    # Notes
    notes = fields.Text('Notes')
    customer_comments = fields.Text('Customer Comments')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.damage.inspection') or _('New')
        return super().create(vals_list)

    @api.depends('damage_ids')
    def _compute_has_damage(self):
        for inspection in self:
            inspection.has_damage = bool(inspection.damage_ids)

    @api.depends('damage_ids.estimated_cost')
    def _compute_damage_cost(self):
        for inspection in self:
            inspection.total_damage_cost = sum(inspection.damage_ids.mapped('estimated_cost'))

    def action_start_inspection(self):
        """Start the inspection"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft inspections can be started."))

        # Create default inspection lines if not exists
        if not self.inspection_line_ids:
            self._create_default_inspection_lines()

        self.write({'state': 'in_progress'})

    def action_complete_inspection(self):
        """Complete the inspection"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_("Only in-progress inspections can be completed."))

        # Validate all inspection items are checked
        unchecked = self.inspection_line_ids.filtered(lambda l: not l.is_checked)
        if unchecked:
            raise UserError(_("Please check all inspection items before completing."))

        self.write({'state': 'completed'})

    def action_approve_inspection(self):
        """Approve the inspection"""
        self.ensure_one()
        if self.state != 'completed':
            raise UserError(_("Only completed inspections can be approved."))

        self.write({'state': 'approved'})

        # If this is a return inspection with damages, create charges
        if self.inspection_type == 'return' and self.has_damage and self.rental_id:
            self._create_damage_charges()

    def action_reset_to_draft(self):
        """Reset to draft"""
        self.ensure_one()
        self.write({'state': 'draft'})

    def _create_default_inspection_lines(self):
        """Create default inspection checklist items"""
        default_items = [
            # Exterior
            ('exterior', 'Front Bumper', 'Check for scratches, dents, or damage'),
            ('exterior', 'Rear Bumper', 'Check for scratches, dents, or damage'),
            ('exterior', 'Hood', 'Check for dents or scratches'),
            ('exterior', 'Roof', 'Check for dents or hail damage'),
            ('exterior', 'Left Front Fender', 'Check for damage'),
            ('exterior', 'Right Front Fender', 'Check for damage'),
            ('exterior', 'Left Rear Fender', 'Check for damage'),
            ('exterior', 'Right Rear Fender', 'Check for damage'),
            ('exterior', 'Left Front Door', 'Check for dents, scratches'),
            ('exterior', 'Right Front Door', 'Check for dents, scratches'),
            ('exterior', 'Left Rear Door', 'Check for dents, scratches'),
            ('exterior', 'Right Rear Door', 'Check for dents, scratches'),
            ('exterior', 'Trunk/Boot', 'Check condition and operation'),
            ('exterior', 'Windshield', 'Check for chips or cracks'),
            ('exterior', 'Rear Window', 'Check for damage'),
            ('exterior', 'Side Mirrors', 'Check both mirrors'),
            ('exterior', 'Headlights', 'Check both working'),
            ('exterior', 'Tail Lights', 'Check both working'),
            ('exterior', 'Turn Signals', 'Check all working'),
            # Wheels & Tires
            ('wheels', 'Front Left Tire', 'Check tread and pressure'),
            ('wheels', 'Front Right Tire', 'Check tread and pressure'),
            ('wheels', 'Rear Left Tire', 'Check tread and pressure'),
            ('wheels', 'Rear Right Tire', 'Check tread and pressure'),
            ('wheels', 'Spare Tire', 'Check presence and condition'),
            ('wheels', 'Wheel Rims', 'Check for damage'),
            # Interior
            ('interior', 'Dashboard', 'Check for damage'),
            ('interior', 'Steering Wheel', 'Check condition'),
            ('interior', 'Seats', 'Check all seats condition'),
            ('interior', 'Seat Belts', 'Check all working'),
            ('interior', 'Floor Mats', 'Check presence and condition'),
            ('interior', 'Carpet', 'Check for stains or damage'),
            ('interior', 'Headliner', 'Check for stains or damage'),
            ('interior', 'Door Panels', 'Check all doors'),
            ('interior', 'Center Console', 'Check condition'),
            ('interior', 'Glove Box', 'Check operation'),
            ('interior', 'Air Conditioning', 'Check working'),
            ('interior', 'Heater', 'Check working'),
            ('interior', 'Radio/Infotainment', 'Check working'),
            ('interior', 'Horn', 'Check working'),
            ('interior', 'Wipers', 'Check working'),
            # Mechanical
            ('mechanical', 'Engine Start', 'Check starts properly'),
            ('mechanical', 'Brakes', 'Check operation'),
            ('mechanical', 'Parking Brake', 'Check operation'),
            ('mechanical', 'Transmission', 'Check operation'),
            ('mechanical', 'Clutch (if manual)', 'Check operation'),
            # Documents & Accessories
            ('accessories', 'Registration Document', 'Check present'),
            ('accessories', 'Insurance Document', 'Check present'),
            ('accessories', 'Vehicle Manual', 'Check present'),
            ('accessories', 'Jack', 'Check present'),
            ('accessories', 'Wheel Wrench', 'Check present'),
            ('accessories', 'Warning Triangle', 'Check present'),
            ('accessories', 'First Aid Kit', 'Check present'),
            ('accessories', 'Fire Extinguisher', 'Check present'),
        ]

        lines = []
        for sequence, (category, item_name, description) in enumerate(default_items, 1):
            lines.append({
                'inspection_id': self.id,
                'sequence': sequence,
                'category': category,
                'item_name': item_name,
                'description': description,
            })

        self.env['fleet.damage.inspection.line'].create(lines)

    def _create_damage_charges(self):
        """Create rental charges for damages"""
        if not self.rental_id:
            return

        for damage in self.damage_ids:
            self.env['fleet.rental.charge'].create({
                'rental_id': self.rental_id.id,
                'charge_type': 'damage',
                'description': f"Damage: {damage.damage_type} - {damage.location}\n{damage.description}",
                'amount': damage.estimated_cost,
            })


class FleetDamageInspectionLine(models.Model):
    _name = 'fleet.damage.inspection.line'
    _description = 'Damage Inspection Checklist Item'
    _order = 'sequence, id'

    inspection_id = fields.Many2one('fleet.damage.inspection', string='Inspection', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)

    category = fields.Selection([
        ('exterior', 'Exterior'),
        ('wheels', 'Wheels & Tires'),
        ('interior', 'Interior'),
        ('mechanical', 'Mechanical'),
        ('accessories', 'Documents & Accessories'),
    ], string='Category', required=True)

    item_name = fields.Char('Item', required=True)
    description = fields.Char('Description')

    # Check Results
    is_checked = fields.Boolean('Checked', default=False)
    condition = fields.Selection([
        ('ok', 'OK'),
        ('minor', 'Minor Issue'),
        ('major', 'Major Issue'),
        ('missing', 'Missing'),
        ('na', 'N/A'),
    ], string='Condition', default='ok')

    notes = fields.Char('Notes')
    photo = fields.Image('Photo', max_width=800, max_height=600)


class FleetDamageRecord(models.Model):
    _name = 'fleet.damage.record'
    _description = 'Vehicle Damage Record'
    _order = 'create_date desc'

    inspection_id = fields.Many2one('fleet.damage.inspection', string='Inspection', required=True, ondelete='cascade')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', related='inspection_id.vehicle_id', store=True)

    # Damage Details
    damage_type = fields.Selection([
        ('scratch', 'Scratch'),
        ('dent', 'Dent'),
        ('crack', 'Crack'),
        ('chip', 'Chip'),
        ('tear', 'Tear'),
        ('stain', 'Stain'),
        ('broken', 'Broken'),
        ('missing', 'Missing'),
        ('mechanical', 'Mechanical Failure'),
        ('other', 'Other'),
    ], string='Damage Type', required=True)

    location = fields.Selection([
        ('front_bumper', 'Front Bumper'),
        ('rear_bumper', 'Rear Bumper'),
        ('hood', 'Hood'),
        ('roof', 'Roof'),
        ('trunk', 'Trunk'),
        ('left_front_fender', 'Left Front Fender'),
        ('right_front_fender', 'Right Front Fender'),
        ('left_rear_fender', 'Left Rear Fender'),
        ('right_rear_fender', 'Right Rear Fender'),
        ('left_front_door', 'Left Front Door'),
        ('right_front_door', 'Right Front Door'),
        ('left_rear_door', 'Left Rear Door'),
        ('right_rear_door', 'Right Rear Door'),
        ('windshield', 'Windshield'),
        ('rear_window', 'Rear Window'),
        ('left_mirror', 'Left Mirror'),
        ('right_mirror', 'Right Mirror'),
        ('headlight_left', 'Left Headlight'),
        ('headlight_right', 'Right Headlight'),
        ('taillight_left', 'Left Taillight'),
        ('taillight_right', 'Right Taillight'),
        ('wheel_fl', 'Front Left Wheel'),
        ('wheel_fr', 'Front Right Wheel'),
        ('wheel_rl', 'Rear Left Wheel'),
        ('wheel_rr', 'Rear Right Wheel'),
        ('interior_dashboard', 'Dashboard'),
        ('interior_seats', 'Seats'),
        ('interior_carpet', 'Carpet'),
        ('interior_headliner', 'Headliner'),
        ('interior_other', 'Interior Other'),
        ('engine', 'Engine'),
        ('other', 'Other'),
    ], string='Location', required=True)

    severity = fields.Selection([
        ('minor', 'Minor'),
        ('moderate', 'Moderate'),
        ('major', 'Major'),
        ('severe', 'Severe'),
    ], string='Severity', required=True, default='minor')

    description = fields.Text('Description', required=True)

    # Cost
    estimated_cost = fields.Monetary('Estimated Repair Cost', currency_field='currency_id')
    actual_cost = fields.Monetary('Actual Repair Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Photos
    photo_1 = fields.Image('Photo 1', max_width=1920, max_height=1080)
    photo_2 = fields.Image('Photo 2', max_width=1920, max_height=1080)
    photo_3 = fields.Image('Photo 3', max_width=1920, max_height=1080)

    # Status
    is_repaired = fields.Boolean('Repaired', default=False)
    repair_date = fields.Date('Repair Date')
    repair_notes = fields.Text('Repair Notes')

    # Pre-existing damage
    is_preexisting = fields.Boolean('Pre-existing Damage', default=False, help='Was this damage present before the rental?')
