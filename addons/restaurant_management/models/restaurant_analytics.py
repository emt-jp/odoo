# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class RestaurantAnalytics(models.Model):
    _name = 'restaurant.analytics'
    _description = 'Restaurant Analytics Dashboard'

    name = fields.Char('Dashboard', default='Restaurant Analytics', required=True)

    # Today's Stats
    today_orders = fields.Integer('Today Orders', compute='_compute_dashboard_kpis')
    today_revenue = fields.Monetary('Today Revenue', compute='_compute_dashboard_kpis', currency_field='currency_id')
    today_guests = fields.Integer('Today Guests', compute='_compute_dashboard_kpis')
    avg_order_value = fields.Monetary('Avg Order Value', compute='_compute_dashboard_kpis', currency_field='currency_id')

    # Current Status
    active_orders = fields.Integer('Active Orders', compute='_compute_dashboard_kpis')
    occupied_tables = fields.Integer('Occupied Tables', compute='_compute_dashboard_kpis')
    available_tables = fields.Integer('Available Tables', compute='_compute_dashboard_kpis')
    reservations_today = fields.Integer('Reservations Today', compute='_compute_dashboard_kpis')
    upcoming_reservations = fields.Integer('Upcoming Reservations', compute='_compute_dashboard_kpis')

    # Performance
    avg_preparation_time = fields.Float('Avg Prep Time (min)', compute='_compute_dashboard_kpis')
    table_turnover_rate = fields.Float('Table Turnover Rate', compute='_compute_dashboard_kpis')

    # Popular Items
    top_selling_items = fields.Text('Top Selling Items', compute='_compute_dashboard_kpis')

    # Week Stats
    week_orders = fields.Integer('Week Orders', compute='_compute_dashboard_kpis')
    week_revenue = fields.Monetary('Week Revenue', compute='_compute_dashboard_kpis', currency_field='currency_id')

    # Month Stats
    month_orders = fields.Integer('Month Orders', compute='_compute_dashboard_kpis')
    month_revenue = fields.Monetary('Month Revenue', compute='_compute_dashboard_kpis', currency_field='currency_id')

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.model
    def get_dashboard(self):
        """Get or create the singleton dashboard record."""
        dashboard = self.search([], limit=1)
        if not dashboard:
            dashboard = self.create({'name': 'Restaurant Analytics'})
        return dashboard

    @api.depends()
    def _compute_dashboard_kpis(self):
        for record in self:
            today = fields.Date.today()

            # Today's orders
            today_orders = self.env['restaurant.order'].search([
                ('order_date', '>=', fields.Datetime.to_string(today)),
                ('state', 'in', ['confirmed', 'preparing', 'ready', 'served', 'done', 'paid'])
            ])

            record.today_orders = len(today_orders)
            record.today_revenue = sum(today_orders.mapped('total_amount'))
            record.today_guests = sum(today_orders.mapped('guest_count'))
            record.avg_order_value = record.today_revenue / record.today_orders if record.today_orders else 0

            # Active orders
            active_orders = self.env['restaurant.order'].search([
                ('state', 'in', ['confirmed', 'preparing', 'ready'])
            ])
            record.active_orders = len(active_orders)

            # Table status
            tables = self.env['restaurant.table'].search([('active', '=', True)])
            record.occupied_tables = len(tables.filtered(lambda t: t.status == 'occupied'))
            record.available_tables = len(tables.filtered(lambda t: t.status == 'available'))

            # Reservations
            today_reservations = self.env['restaurant.reservation'].search([
                ('reservation_date', '=', today),
                ('state', 'in', ['confirmed', 'seated'])
            ])
            record.reservations_today = len(today_reservations)

            upcoming_reservations = self.env['restaurant.reservation'].search([
                ('reservation_date', '>=', today),
                ('state', '=', 'confirmed')
            ])
            record.upcoming_reservations = len(upcoming_reservations)

            # Performance metrics
            completed_orders = today_orders.filtered(lambda o: o.actual_prep_time > 0)
            record.avg_preparation_time = sum(completed_orders.mapped('actual_prep_time')) / len(completed_orders) if completed_orders else 0

            # Week and Month stats
            from datetime import timedelta
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)

            week_orders = self.env['restaurant.order'].search([
                ('order_date', '>=', fields.Datetime.to_string(week_start)),
                ('state', 'in', ['done', 'paid'])
            ])
            record.week_orders = len(week_orders)
            record.week_revenue = sum(week_orders.mapped('total_amount'))

            month_orders = self.env['restaurant.order'].search([
                ('order_date', '>=', fields.Datetime.to_string(month_start)),
                ('state', 'in', ['done', 'paid'])
            ])
            record.month_orders = len(month_orders)
            record.month_revenue = sum(month_orders.mapped('total_amount'))

            record.table_turnover_rate = 0.0
            record.top_selling_items = ''
