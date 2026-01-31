# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from collections import OrderedDict


class FleetPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        if 'booking_count' in counters:
            values['booking_count'] = request.env['fleet.booking'].search_count([
                ('customer_id', '=', partner.id)
            ]) if request.env['fleet.booking'].check_access_rights('read', raise_exception=False) else 0

        if 'rental_count' in counters:
            values['rental_count'] = request.env['fleet.rental'].search_count([
                ('customer_id', '=', partner.id)
            ]) if request.env['fleet.rental'].check_access_rights('read', raise_exception=False) else 0

        return values

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        values['booking_count'] = request.env['fleet.booking'].search_count([
            ('customer_id', '=', partner.id)
        ])
        values['rental_count'] = request.env['fleet.rental'].search_count([
            ('customer_id', '=', partner.id)
        ])

        return values

    # ==================== BOOKINGS ====================

    @http.route(['/my/bookings', '/my/bookings/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_bookings(self, page=1, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        FleetBooking = request.env['fleet.booking']

        domain = [('customer_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Booking Date'), 'order': 'booking_date desc'},
            'pickup': {'label': _('Pickup Date'), 'order': 'pickup_date desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'state': {'label': _('Status'), 'order': 'state'},
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'draft': {'label': _('Draft'), 'domain': [('state', '=', 'draft')]},
            'confirmed': {'label': _('Confirmed'), 'domain': [('state', '=', 'confirmed')]},
            'assigned': {'label': _('Assigned'), 'domain': [('state', '=', 'assigned')]},
            'cancelled': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancelled')]},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # Count for pager
        booking_count = FleetBooking.search_count(domain)

        # Pager
        pager = portal_pager(
            url='/my/bookings',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=booking_count,
            page=page,
            step=10,
        )

        # Content according to pager and target
        bookings = FleetBooking.search(domain, order=order, limit=10, offset=pager['offset'])

        values.update({
            'bookings': bookings,
            'page_name': 'booking',
            'pager': pager,
            'default_url': '/my/bookings',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })

        return request.render('car_rental_fleet.portal_my_bookings', values)

    @http.route(['/my/booking/<int:booking_id>'], type='http', auth='user', website=True)
    def portal_my_booking(self, booking_id, **kw):
        try:
            booking_sudo = self._document_check_access('fleet.booking', booking_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'booking': booking_sudo,
            'page_name': 'booking',
        }

        return request.render('car_rental_fleet.portal_my_booking', values)

    # ==================== RENTALS ====================

    @http.route(['/my/rentals', '/my/rentals/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_rentals(self, page=1, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        FleetRental = request.env['fleet.rental']

        domain = [('customer_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Start Date'), 'order': 'start_date desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'state': {'label': _('Status'), 'order': 'state'},
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'confirmed': {'label': _('Confirmed'), 'domain': [('state', '=', 'confirmed')]},
            'in_progress': {'label': _('In Progress'), 'domain': [('state', '=', 'in_progress')]},
            'completed': {'label': _('Completed'), 'domain': [('state', '=', 'completed')]},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # Count for pager
        rental_count = FleetRental.search_count(domain)

        # Pager
        pager = portal_pager(
            url='/my/rentals',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=rental_count,
            page=page,
            step=10,
        )

        # Content according to pager
        rentals = FleetRental.search(domain, order=order, limit=10, offset=pager['offset'])

        values.update({
            'rentals': rentals,
            'page_name': 'rental',
            'pager': pager,
            'default_url': '/my/rentals',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })

        return request.render('car_rental_fleet.portal_my_rentals', values)

    @http.route(['/my/rental/<int:rental_id>'], type='http', auth='user', website=True)
    def portal_my_rental(self, rental_id, **kw):
        try:
            rental_sudo = self._document_check_access('fleet.rental', rental_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'rental': rental_sudo,
            'page_name': 'rental',
        }

        return request.render('car_rental_fleet.portal_my_rental', values)
