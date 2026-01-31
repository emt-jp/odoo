# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class RentalCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'rental_count' in counters:
            partner = request.env.user.partner_id
            values['rental_count'] = request.env['rental.booking'].search_count([
                ('partner_id', '=', partner.id),
            ])
        return values

    @http.route(['/my/rentals', '/my/rentals/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_rentals(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        partner = request.env.user.partner_id
        Booking = request.env['rental.booking']

        domain = [('partner_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'pickup': {'label': _('Pickup Date'), 'order': 'pickup_date desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'confirmed': {'label': _('Confirmed'), 'domain': [('state', '=', 'confirmed')]},
            'in_progress': {'label': _('In Progress'), 'domain': [('state', '=', 'in_progress')]},
            'completed': {'label': _('Completed'), 'domain': [('state', '=', 'completed')]},
            'cancelled': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancelled')]},
        }

        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        rental_count = Booking.search_count(domain)
        pager = portal_pager(
            url='/my/rentals',
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=rental_count,
            page=page,
            step=self._items_per_page
        )

        rentals = Booking.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            'rentals': rentals,
            'page_name': 'rental',
            'pager': pager,
            'default_url': '/my/rentals',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        })

        return request.render('car_rental_website.portal_my_rentals', values)

    @http.route(['/my/rental/<int:rental_id>'], type='http', auth='public', website=True)
    def portal_my_rental(self, rental_id, access_token=None, **kw):
        rental = request.env['rental.booking'].sudo().browse(rental_id)

        if not rental.exists():
            return request.redirect('/my/rentals')

        # Check access
        if access_token and rental.access_token == access_token:
            pass  # Access granted via token
        elif request.env.user._is_public():
            return request.redirect('/web/login?redirect=/my/rental/%s' % rental_id)
        elif rental.partner_id != request.env.user.partner_id:
            return request.redirect('/my/rentals')

        values = self._prepare_portal_layout_values()
        values.update({
            'rental': rental,
            'page_name': 'rental',
        })

        return request.render('car_rental_website.portal_my_rental', values)

    @http.route(['/my/rental/<int:rental_id>/cancel'], type='http', auth='public', website=True, methods=['POST'])
    def portal_rental_cancel(self, rental_id, access_token=None, **kw):
        rental = request.env['rental.booking'].sudo().browse(rental_id)

        if not rental.exists():
            return request.redirect('/my/rentals')

        # Check access
        if access_token and rental.access_token == access_token:
            pass  # Access granted via token
        elif request.env.user._is_public():
            return request.redirect('/web/login')
        elif rental.partner_id != request.env.user.partner_id:
            return request.redirect('/my/rentals')

        # Cancel the booking
        if rental.state not in ['completed', 'cancelled']:
            rental.action_cancel()

        if access_token:
            return request.redirect('/my/rental/%s?access_token=%s' % (rental_id, access_token))
        return request.redirect('/my/rental/%s' % rental_id)

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        values['rental_count'] = request.env['rental.booking'].search_count([
            ('partner_id', '=', partner.id),
        ])
        return values

    @http.route(['/my/license'], type='http', auth='user', website=True)
    def portal_my_license(self, **kw):
        """Display driving license information page"""
        partner = request.env.user.partner_id
        countries = request.env['res.country'].sudo().search([])

        values = self._prepare_portal_layout_values()
        values.update({
            'partner': partner,
            'countries': countries,
            'page_name': 'license',
        })

        return request.render('car_rental_website.portal_driving_license', values)

    @http.route(['/my/license/update'], type='http', auth='user', website=True, methods=['POST'])
    def portal_license_update(self, **post):
        """Update driving license information"""
        import base64

        partner = request.env.user.partner_id
        values = {}

        # Text fields
        if 'driving_license_number' in post:
            values['driving_license_number'] = post.get('driving_license_number')
        if 'driving_license_expiry' in post and post.get('driving_license_expiry'):
            values['driving_license_expiry'] = post.get('driving_license_expiry')
        if 'driving_license_country_id' in post and post.get('driving_license_country_id'):
            values['driving_license_country_id'] = int(post.get('driving_license_country_id'))
        if 'birthdate' in post and post.get('birthdate'):
            values['birthdate'] = post.get('birthdate')

        # File uploads
        if 'driving_license_front' in request.httprequest.files:
            file_front = request.httprequest.files['driving_license_front']
            if file_front and file_front.filename:
                values['driving_license_front'] = base64.b64encode(file_front.read())

        if 'driving_license_back' in request.httprequest.files:
            file_back = request.httprequest.files['driving_license_back']
            if file_back and file_back.filename:
                values['driving_license_back'] = base64.b64encode(file_back.read())

        if values:
            # Reset verification if license details changed
            if any(k in values for k in ['driving_license_number', 'driving_license_front', 'driving_license_back']):
                values['driving_license_verified'] = False

            partner.sudo().write(values)

        return request.redirect('/my/license')
