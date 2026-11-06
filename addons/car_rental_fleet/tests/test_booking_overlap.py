# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBookingOverlap(TransactionCase):
    """Two active bookings or date blocks may not hold the same car at once."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        brand = cls.env['fleet.vehicle.model.brand'].create({'name': 'Overlap Test Brand'})
        model = cls.env['fleet.vehicle.model'].create({'name': 'Overlap Test Model', 'brand_id': brand.id})
        cls.car = cls.env['fleet.vehicle'].create({'model_id': model.id, 'license_plate': 'TEST-1'})
        cls.other_car = cls.env['fleet.vehicle'].create({'model_id': model.id, 'license_plate': 'TEST-2'})
        cls.customer = cls.env['res.partner'].create({'name': 'Overlap Test Customer'})
        # Far enough ahead that the pickup-date checks never interfere.
        cls.t0 = datetime.now().replace(hour=1, minute=0, second=0, microsecond=0) + timedelta(days=30)

    def _at(self, days, hours=0):
        return self.t0 + timedelta(days=days, hours=hours)

    def _booking(self, start, end, car=None, **vals):
        return self.env['fleet.booking'].create({
            'customer_id': self.customer.id,
            'contact_phone': '000',
            'pickup_location': 'Kasai',
            'return_location': 'Kasai',
            'assigned_vehicle_id': (car or self.car).id,
            'pickup_date': start,
            'return_date': end,
            **vals,
        })

    def _block(self, start, end, car=None, **vals):
        return self.env['fleet.booking'].create({
            'booking_kind': 'block',
            'block_reason': 'personal',
            'assigned_vehicle_id': (car or self.car).id,
            'pickup_date': start,
            'return_date': end,
            **vals,
        })

    # --- create --------------------------------------------------------------

    def test_overlapping_booking_is_refused(self):
        self._booking(self._at(0), self._at(3))
        with self.assertRaises(ValidationError):
            self._booking(self._at(2), self._at(5))

    def test_contained_booking_is_refused(self):
        self._booking(self._at(0), self._at(10))
        with self.assertRaises(ValidationError):
            self._booking(self._at(2), self._at(3))

    def test_back_to_back_is_allowed(self):
        self._booking(self._at(0), self._at(3))
        self._booking(self._at(3), self._at(5))

    def test_other_car_is_independent(self):
        self._booking(self._at(0), self._at(3))
        self._booking(self._at(1), self._at(2), car=self.other_car)

    def test_draft_counts_as_active(self):
        # Web bookings are pay-at-pickup drafts and are real reservations.
        self._booking(self._at(0), self._at(3), state='draft')
        with self.assertRaises(ValidationError):
            self._booking(self._at(1), self._at(2))

    def test_cancelled_and_expired_do_not_count(self):
        self._booking(self._at(0), self._at(3), state='cancelled')
        self._booking(self._at(0), self._at(3), state='expired')
        self._booking(self._at(0), self._at(3))

    def test_inactive_new_record_is_not_checked(self):
        self._booking(self._at(0), self._at(3))
        self._booking(self._at(1), self._at(2), state='cancelled')

    def test_booking_without_car_is_not_checked(self):
        self._booking(self._at(0), self._at(3))
        self.env['fleet.booking'].create({
            'customer_id': self.customer.id, 'contact_phone': '0',
            'pickup_location': 'x', 'return_location': 'x',
            'pickup_date': self._at(1), 'return_date': self._at(2),
        })

    def test_overlap_within_one_create_is_refused(self):
        with self.assertRaises(ValidationError):
            self.env['fleet.booking'].create([
                {'customer_id': self.customer.id, 'contact_phone': '0', 'pickup_location': 'x',
                 'return_location': 'x', 'assigned_vehicle_id': self.car.id,
                 'pickup_date': self._at(0), 'return_date': self._at(3)},
                {'customer_id': self.customer.id, 'contact_phone': '0', 'pickup_location': 'x',
                 'return_location': 'x', 'assigned_vehicle_id': self.car.id,
                 'pickup_date': self._at(1), 'return_date': self._at(4)},
            ])

    # --- write ---------------------------------------------------------------

    def test_moving_into_another_booking_is_refused(self):
        self._booking(self._at(0), self._at(3))
        later = self._booking(self._at(5), self._at(7))
        with self.assertRaises(ValidationError):
            later.write({'pickup_date': self._at(2)})

    def test_changing_car_into_a_clash_is_refused(self):
        self._booking(self._at(0), self._at(3))
        on_other = self._booking(self._at(1), self._at(2), car=self.other_car)
        with self.assertRaises(ValidationError):
            on_other.write({'assigned_vehicle_id': self.car.id})

    def test_reactivating_into_a_clash_is_refused(self):
        self._booking(self._at(0), self._at(3))
        cancelled = self._booking(self._at(1), self._at(2), state='cancelled')
        with self.assertRaises(ValidationError):
            cancelled.write({'state': 'confirmed'})

    def test_existing_overlap_does_not_block_unrelated_writes(self):
        """History already holds overlaps (#42/#52 on car #33). A payment
        marking one paid, a note, or a cancel must still go through."""
        first = self._booking(self._at(0), self._at(3))
        second = self._booking(self._at(5), self._at(7))
        # Recreate legacy overlapping data behind the ORM's back.
        self.env.cr.execute(
            'UPDATE fleet_booking SET pickup_date = %s WHERE id = %s', [self._at(1), second.id])
        second.invalidate_recordset()
        second.write({'state': 'paid'})
        second.write({'internal_notes': 'paid by link'})
        # Rewriting the same dates is not a move either.
        second.write({'pickup_date': second.pickup_date, 'return_date': second.return_date})
        first.write({'state': 'cancelled'})

    def test_existing_overlap_still_refuses_a_real_move(self):
        self._booking(self._at(0), self._at(3))
        second = self._booking(self._at(5), self._at(7))
        self.env.cr.execute(
            'UPDATE fleet_booking SET pickup_date = %s WHERE id = %s', [self._at(1), second.id])
        second.invalidate_recordset()
        with self.assertRaises(ValidationError):
            second.write({'return_date': self._at(8)})

    # --- date blocks -----------------------------------------------------------

    def test_block_fills_its_own_required_fields(self):
        # state='draft' is what the form sends (the field default); a block is never a draft.
        block = self._block(self._at(0), self._at(3), estimated_total_amount=5000, state='draft')
        self.assertEqual(block.customer_id, self.env.company.partner_id)
        self.assertEqual(block.state, 'confirmed')
        self.assertEqual(block.source, 'direct')
        self.assertTrue(block.name.startswith('BLK-'))
        self.assertEqual(block.estimated_total_amount, 0)
        self.assertFalse(block.vendor_id)

    def test_default_get_prefills_block_form(self):
        vals = self.env['fleet.booking'].with_context(default_booking_kind='block').default_get(
            ['booking_kind', 'customer_id', 'contact_phone', 'pickup_location', 'return_location', 'state'])
        self.assertEqual(vals['customer_id'], self.env.company.partner_id.id)
        self.assertEqual(vals['state'], 'confirmed')
        self.assertTrue(vals['contact_phone'])

    def test_block_refuses_a_booking(self):
        self._block(self._at(0), self._at(3))
        with self.assertRaises(ValidationError):
            self._booking(self._at(2), self._at(4))

    def test_booking_refuses_a_block(self):
        self._booking(self._at(0), self._at(3))
        with self.assertRaises(ValidationError):
            self._block(self._at(1), self._at(2))

    def test_removed_block_frees_the_dates_without_mailing(self):
        block = self._block(self._at(0), self._at(3))
        before = self.env['mail.message'].search_count([('subject', 'like', 'Booking Cancelled')])
        block.action_cancel_booking()
        self.assertEqual(block.state, 'cancelled')
        after = self.env['mail.message'].search_count([('subject', 'like', 'Booking Cancelled')])
        self.assertEqual(before, after, 'a block has no customer to send a cancellation to')
        self._booking(self._at(0), self._at(3))

    def test_blocks_are_left_out_of_booking_analytics(self):
        booking_model = self.env['fleet.booking']
        start = (datetime.now() - timedelta(days=1)).date()
        end = (datetime.now() + timedelta(days=1)).date()
        before = booking_model.get_booking_analytics(start, end)['total_bookings']
        self._block(self._at(0), self._at(3))
        self.assertEqual(booking_model.get_booking_analytics(start, end)['total_bookings'], before)
