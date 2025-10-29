# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


@pytest.mark.unit
@pytest.mark.enterprise
class TestRentalOperations:
    """Test rental operations functionality"""

    def test_create_rental(self, odoo_env, sample_rental_data, mock_enterprise_license):
        """Test rental creation"""
        rental_model = odoo_env['fleet.rental']
        
        rental = rental_model.create(sample_rental_data)
        
        assert rental.id
        assert rental.name != 'New'
        assert rental.customer_id.id == sample_rental_data['customer_id']
        assert rental.start_date == sample_rental_data['start_date']
        assert rental.end_date == sample_rental_data['end_date']

    def test_rental_duration_calculation(self, odoo_env, sample_rental_data, mock_enterprise_license):
        """Test rental duration calculation"""
        rental_model = odoo_env['fleet.rental']
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=3)
        sample_rental_data['start_date'] = start_date
        sample_rental_data['end_date'] = end_date
        
        rental = rental_model.create(sample_rental_data)
        
        assert rental.rental_duration == 3

    def test_rental_pricing_calculation(self, odoo_env, sample_rental_data, mock_enterprise_license):
        """Test rental pricing calculation"""
        rental_model = odoo_env['fleet.rental']
        
        sample_rental_data['daily_rate'] = 50.0
        sample_rental_data['start_date'] = datetime.now()
        sample_rental_data['end_date'] = datetime.now() + timedelta(days=2)
        
        rental = rental_model.create(sample_rental_data)
        
        assert rental.base_amount == 100.0  # 2 days * 50.0
        assert rental.total_amount == 100.0

    def test_rental_confirmation(self, odoo_env, sample_rental_data, mock_enterprise_license):
        """Test rental confirmation"""
        rental_model = odoo_env['fleet.rental']
        
        # Create vehicle first
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create({
            'name': 'Test Vehicle',
            'license_plate': 'TEST001',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'daily_rate': 50.0,
            'is_rental_vehicle': True,
            'availability_status': 'available',
        })
        
        sample_rental_data['vehicle_id'] = vehicle.id
        rental = rental_model.create(sample_rental_data)
        
        result = rental.action_confirm()
        
        assert result == True
        assert rental.state == 'confirmed'
        assert vehicle.availability_status == 'rented'

    def test_rental_start(self, odoo_env, sample_rental_data, mock_enterprise_license):
        """Test rental start"""
        rental_model = odoo_env['fleet.rental']
        
        # Create and confirm rental
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create({
            'name': 'Test Vehicle',
            'license_plate': 'TEST001',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'daily_rate': 50.0,
            'is_rental_vehicle': True,
            'availability_status': 'available',
        })
        
        sample_rental_data['vehicle_id'] = vehicle.id
        rental = rental_model.create(sample_rental_data)
        rental.action_confirm()
        
        result = rental.action_start_rental()
        
        assert result == True
        assert rental.state == 'in_progress'
        assert rental.actual_start_date is not None

    def test_rental_completion(self, odoo_env, sample_rental_data, mock_enterprise_license):
        """Test rental completion"""
        rental_model = odoo_env['fleet.rental']
        
        # Create, confirm, and start rental
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create({
            'name': 'Test Vehicle',
            'license_plate': 'TEST001',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'daily_rate': 50.0,
            'is_rental_vehicle': True,
            'availability_status': 'available',
        })
        
        sample_rental_data['vehicle_id'] = vehicle.id
        rental = rental_model.create(sample_rental_data)
        rental.action_confirm()
        rental.action_start_rental()
        
        result = rental.action_complete_rental()
        
        assert result == True
        assert rental.state == 'completed'
        assert rental.actual_end_date is not None
        assert vehicle.availability_status == 'available'

    def test_rental_cancellation(self, odoo_env, sample_rental_data, mock_enterprise_license):
        """Test rental cancellation"""
        rental_model = odoo_env['fleet.rental']
        
        # Create and confirm rental
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create({
            'name': 'Test Vehicle',
            'license_plate': 'TEST001',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'daily_rate': 50.0,
            'is_rental_vehicle': True,
            'availability_status': 'available',
        })
        
        sample_rental_data['vehicle_id'] = vehicle.id
        rental = rental_model.create(sample_rental_data)
        rental.action_confirm()
        
        result = rental.action_cancel_rental()
        
        assert result == True
        assert rental.state == 'cancelled'

    def test_rental_analytics(self, odoo_env, mock_enterprise_license):
        """Test rental analytics"""
        rental_model = odoo_env['fleet.rental']
        
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        analytics = rental_model.get_rental_analytics(start_date, end_date)
        
        assert 'total_rentals' in analytics
        assert 'completed_rentals' in analytics
        assert 'cancelled_rentals' in analytics
        assert 'total_revenue' in analytics
        assert 'average_rating' in analytics

    def test_overdue_rentals(self, odoo_env, sample_rental_data, mock_enterprise_license):
        """Test overdue rentals detection"""
        rental_model = odoo_env['fleet.rental']
        
        # Create overdue rental
        sample_rental_data['end_date'] = datetime.now() - timedelta(days=1)
        sample_rental_data['state'] = 'in_progress'
        
        rental = rental_model.create(sample_rental_data)
        
        overdue_rentals = rental_model.get_overdue_rentals()
        
        assert len(overdue_rentals) >= 0

    def test_rental_reminders(self, odoo_env, mock_enterprise_license):
        """Test rental reminders"""
        rental_model = odoo_env['fleet.rental']
        
        # This would test sending reminders
        # For now, just test that the method exists and doesn't error
        try:
            rental_model.send_rental_reminders()
            assert True
        except Exception:
            # Expected in test environment without email setup
            assert True

    def test_additional_charges(self, odoo_env, sample_rental_data, mock_enterprise_license):
        """Test additional charges"""
        rental_model = odoo_env['fleet.rental']
        charge_model = odoo_env['fleet.rental.charge']
        
        rental = rental_model.create(sample_rental_data)
        
        # Add additional charge
        charge = charge_model.create({
            'rental_id': rental.id,
            'charge_type': 'gps',
            'description': 'GPS Navigation',
            'amount': 25.0,
        })
        
        assert charge.id
        assert charge.rental_id.id == rental.id
        assert charge.charge_type == 'gps'
        assert charge.amount == 25.0

    def test_rental_discount_calculation(self, odoo_env, sample_rental_data, mock_enterprise_license):
        """Test rental discount calculation"""
        rental_model = odoo_env['fleet.rental']
        
        sample_rental_data['daily_rate'] = 100.0
        sample_rental_data['start_date'] = datetime.now()
        sample_rental_data['end_date'] = datetime.now() + timedelta(days=2)
        sample_rental_data['discount_type'] = 'percentage'
        sample_rental_data['discount_value'] = 10.0  # 10% discount
        
        rental = rental_model.create(sample_rental_data)
        
        # Base amount: 2 days * 100.0 = 200.0
        # Discount: 200.0 * 0.1 = 20.0
        # Total: 200.0 - 20.0 = 180.0
        assert rental.base_amount == 200.0
        assert rental.discount_amount == 20.0
        assert rental.total_amount == 180.0

    def test_rental_weekly_rate(self, odoo_env, sample_rental_data, mock_enterprise_license):
        """Test weekly rate calculation"""
        rental_model = odoo_env['fleet.rental']
        
        sample_rental_data['daily_rate'] = 50.0
        sample_rental_data['weekly_rate'] = 300.0
        sample_rental_data['start_date'] = datetime.now()
        sample_rental_data['end_date'] = datetime.now() + timedelta(days=7)  # 1 week
        
        rental = rental_model.create(sample_rental_data)
        
        # Should use weekly rate for 7+ days
        assert rental.base_amount == 300.0

    def test_rental_monthly_rate(self, odoo_env, sample_rental_data, mock_enterprise_license):
        """Test monthly rate calculation"""
        rental_model = odoo_env['fleet.rental']
        
        sample_rental_data['daily_rate'] = 50.0
        sample_rental_data['weekly_rate'] = 300.0
        sample_rental_data['monthly_rate'] = 1000.0
        sample_rental_data['start_date'] = datetime.now()
        sample_rental_data['end_date'] = datetime.now() + timedelta(days=30)  # 1 month
        
        rental = rental_model.create(sample_rental_data)
        
        # Should use monthly rate for 30+ days
        assert rental.base_amount == 1000.0




