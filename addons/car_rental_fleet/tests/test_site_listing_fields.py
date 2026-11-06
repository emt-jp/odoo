# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSiteListingFields(TransactionCase):
    """The api-adapter's public fleet feed filters on these flags (tdc#406).

    It queries `tdc_hide_<site> = False`, so a new car must store False, never
    null, or it would silently drop out of the feed.
    """

    def test_new_car_is_not_hidden_anywhere(self):
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Site Test Brand'})
        model = self.env['fleet.vehicle.model'].create({'name': 'Site Test Model', 'brand_id': brand.id})
        car = self.env['fleet.vehicle'].create({'model_id': model.id, 'license_plate': 'SITE-1'})
        for field in ('tdc_hide_88roads', 'tdc_hide_tabi_rv', 'tdc_hide_prince'):
            self.assertIs(car[field], False, field)
        # and the feed's domain finds it
        found = self.env['fleet.vehicle'].search([
            ('id', '=', car.id),
            ('tdc_hide_88roads', '=', False),
            ('tdc_hide_tabi_rv', '=', False),
            ('tdc_hide_prince', '=', False),
        ])
        self.assertEqual(found, car)

    def test_hide_flag_excludes_from_feed_domain(self):
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Site Test Brand 2'})
        model = self.env['fleet.vehicle.model'].create({'name': 'Site Test Model 2', 'brand_id': brand.id})
        car = self.env['fleet.vehicle'].create({
            'model_id': model.id, 'license_plate': 'SITE-2', 'tdc_hide_prince': True,
        })
        found = self.env['fleet.vehicle'].search([('id', '=', car.id), ('tdc_hide_prince', '=', False)])
        self.assertFalse(found)
