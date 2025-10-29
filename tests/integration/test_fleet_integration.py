# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytest
from datetime import datetime, timedelta


@pytest.mark.integration
@pytest.mark.enterprise
class TestFleetIntegration:
    """Test fleet management integration scenarios"""

    def test_complete_rental_workflow(self, odoo_env, mock_enterprise_license):
        """Test complete rental workflow from booking to completion"""
        # Create customer
        customer = odoo_env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@test.com',
            'phone': '+1234567890',
        })
        
        # Create vehicle
        vehicle = odoo_env['fleet.vehicle'].create({
            'name': 'Test Vehicle 001',
            'license_plate': 'TEST001',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'daily_rate': 50.0,
            'is_rental_vehicle': True,
            'availability_status': 'available',
        })
        
        # Create booking
        booking = odoo_env['fleet.booking'].create({
            'customer_id': customer.id,
            'pickup_date': datetime.now() + timedelta(hours=1),
            'return_date': datetime.now() + timedelta(days=2),
            'pickup_location': 'Test Location',
            'return_location': 'Test Location',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'contact_phone': '+10000000000',
        })
        
        # Confirm booking
        booking.action_confirm_booking()
        assert booking.state == 'confirmed'
        
        # Assign vehicle
        booking.action_assign_vehicle(vehicle.id)
        assert booking.state == 'assigned'
        assert booking.assigned_vehicle_id.id == vehicle.id
        
        # Check that rental was created
        assert booking.rental_id
        rental = booking.rental_id
        assert rental.state == 'confirmed'
        
        # Start rental
        rental.action_start_rental()
        assert rental.state == 'in_progress'
        assert vehicle.availability_status == 'rented'
        
        # Complete rental
        rental.action_complete_rental()
        assert rental.state == 'completed'
        assert vehicle.availability_status == 'available'

    def test_maintenance_workflow(self, odoo_env, mock_enterprise_license):
        """Test maintenance workflow"""
        # Create vehicle
        vehicle = odoo_env['fleet.vehicle'].create({
            'name': 'Test Vehicle 002',
            'license_plate': 'TEST002',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'daily_rate': 50.0,
            'is_rental_vehicle': True,
            'availability_status': 'available',
        })
        
        # Schedule maintenance
        maintenance = odoo_env['fleet.maintenance'].create({
            'vehicle_id': vehicle.id,
            'maintenance_type': 'routine',
            'description': 'Regular maintenance service',
            'scheduled_date': datetime.now() + timedelta(hours=1),
            'priority': 'medium',
            'estimated_duration': 2.0,
        })
        
        # Start maintenance
        maintenance.action_start_maintenance()
        assert maintenance.status == 'in_progress'
        assert vehicle.availability_status == 'maintenance'
        
        # Complete maintenance
        maintenance.action_complete_maintenance()
        assert maintenance.status == 'completed'
        assert vehicle.availability_status == 'available'

    def test_fuel_management_workflow(self, odoo_env, mock_enterprise_license):
        """Test fuel management workflow"""
        # Create vehicle
        vehicle = odoo_env['fleet.vehicle'].create({
            'name': 'Test Vehicle 003',
            'license_plate': 'TEST003',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'daily_rate': 50.0,
            'is_rental_vehicle': True,
            'engine_type': 'gasoline',
        })
        
        # Create fuel record
        fuel_record = odoo_env['fleet.fuel.management'].create_fuel_record(vehicle.id, {
            'fuel_type': 'gasoline',
            'fuel_quantity': 50.0,
            'fuel_unit': 'liters',
            'unit_price': 1.5,
            'refuel_location': 'Test Station',
            'odometer_reading': 10000,
        })
        
        assert fuel_record.id
        assert fuel_record.vehicle_id.id == vehicle.id
        assert fuel_record.fuel_type == 'gasoline'
        assert fuel_record.total_cost == 75.0  # 50 * 1.5

    def test_insurance_management_workflow(self, odoo_env, mock_enterprise_license):
        """Test insurance management workflow"""
        # Create vehicle
        vehicle = odoo_env['fleet.vehicle'].create({
            'name': 'Test Vehicle 004',
            'license_plate': 'TEST004',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'daily_rate': 50.0,
            'is_rental_vehicle': True,
        })
        
        # Create insurance policy
        insurance = odoo_env['fleet.insurance'].create_insurance_policy(vehicle.id, {
            'policy_number': 'POL001',
            'insurance_company': 'Test Insurance',
            'insurance_type': 'comprehensive',
            'coverage_amount': 50000.0,
            'premium_amount': 1000.0,
            'start_date': '2024-01-01',
            'expiry_date': '2024-12-31',
        })
        
        assert insurance.id
        assert insurance.vehicle_id.id == vehicle.id
        assert insurance.policy_number == 'POL001'
        assert insurance.status == 'active'

    def test_analytics_integration(self, odoo_env, mock_enterprise_license):
        """Test analytics integration"""
        # Create some test data
        customer = odoo_env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@test.com',
        })
        
        vehicle = odoo_env['fleet.vehicle'].create({
            'name': 'Test Vehicle 005',
            'license_plate': 'TEST005',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'daily_rate': 50.0,
            'is_rental_vehicle': True,
        })
        
        # Create rental
        rental = odoo_env['fleet.rental'].create({
            'vehicle_id': vehicle.id,
            'customer_id': customer.id,
            'start_date': datetime.now() - timedelta(days=1),
            'end_date': datetime.now() + timedelta(days=1),
            'pickup_location': 'Test Location',
            'return_location': 'Test Location',
            'daily_rate': 50.0,
            'state': 'completed',
        })
        
        # Test analytics
        analytics = odoo_env['fleet.analytics'].generate_fleet_overview()
        
        assert 'fleet_metrics' in analytics
        assert 'rental_metrics' in analytics
        assert 'cost_metrics' in analytics

    def test_gps_tracking_integration(self, odoo_env, mock_enterprise_license):
        """Test GPS tracking integration"""
        # Create vehicle
        vehicle = odoo_env['fleet.vehicle'].create({
            'name': 'Test Vehicle 006',
            'license_plate': 'TEST006',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'daily_rate': 50.0,
            'is_rental_vehicle': True,
        })
        
        # Update vehicle location
        result = odoo_env['fleet.vehicle'].update_vehicle_location(
            vehicle.id, 40.7128, -74.0060, 'New York'
        )
        
        assert result == True
        
        # Get vehicle location
        location = odoo_env['fleet.gps.tracking'].get_vehicle_location(vehicle.id)
        
        assert location
        assert location['latitude'] == 40.7128
        assert location['longitude'] == -74.0060
        assert location['location_name'] == 'New York'

    def test_enterprise_licensing_integration(self, odoo_env):
        """Enterprise licensing removed; assert model is absent"""
        assert 'license.management' not in odoo_env.registry.models

    def test_car_rental_workflow(self, odoo_env, mock_enterprise_license):
        """Test complete car rental workflow"""
        # Create customer
        customer = odoo_env['res.partner'].create({
            'name': 'Car Rental Customer',
            'email': 'rental@test.com',
            'phone': '+1234567890',
        })
        
        # Create vehicle
        vehicle = odoo_env['fleet.vehicle'].create({
            'name': 'Rental Car 001',
            'license_plate': 'RENT001',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'daily_rate': 50.0,
            'weekly_rate': 300.0,
            'monthly_rate': 1000.0,
            'is_rental_vehicle': True,
            'availability_status': 'available',
        })
        
        # Create rental using wizard
        wizard = odoo_env['rental.booking.wizard'].create({
            'customer_id': customer.id,
            'pickup_date': datetime.now() + timedelta(hours=1),
            'return_date': datetime.now() + timedelta(days=2),
            'pickup_location': 'Airport',
            'return_location': 'Airport',
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'selected_vehicle_id': vehicle.id,
        })
        
        # Create rental
        rental = wizard.action_create_rental()
        
        assert rental['type'] == 'ir.actions.act_window'
        assert rental['res_model'] == 'fleet.rental'




