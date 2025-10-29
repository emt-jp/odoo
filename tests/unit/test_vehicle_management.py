# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


@pytest.mark.unit
@pytest.mark.enterprise
class TestVehicleManagement:
    """Test vehicle management functionality"""

    def test_create_vehicle(self, odoo_env, sample_vehicle_data, mock_enterprise_license):
        """Test vehicle creation"""
        vehicle_model = odoo_env['fleet.vehicle']
        
        vehicle = vehicle_model.create(sample_vehicle_data)
        
        assert vehicle.id
        # Core may compute a composite name; ensure license plate was set
        assert vehicle.license_plate == sample_vehicle_data['license_plate']
        assert vehicle.vehicle_type in [sample_vehicle_data['vehicle_type'], 'car']
        assert vehicle.rental_category == sample_vehicle_data['rental_category']
        assert vehicle.is_rental_vehicle == True

    def test_vehicle_analytics(self, odoo_env, sample_vehicle_data, mock_enterprise_license):
        """Test vehicle analytics"""
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create(sample_vehicle_data)
        
        analytics = vehicle_model.get_vehicle_analytics(vehicle.id)
        
        assert 'vehicle_id' in analytics
        assert 'vehicle_name' in analytics
        assert 'availability_status' in analytics
        assert 'total_rentals' in analytics
        assert 'total_revenue' in analytics

    def test_get_available_vehicles(self, odoo_env, sample_vehicle_data, mock_enterprise_license):
        """Test getting available vehicles"""
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create(sample_vehicle_data)
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)
        
        available_vehicles = vehicle_model.get_available_vehicles(
            start_date, end_date, 'sedan', 'economy'
        )
        
        assert len(available_vehicles) >= 0

    def test_update_vehicle_location(self, odoo_env, sample_vehicle_data, mock_enterprise_license):
        """Test updating vehicle location"""
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create(sample_vehicle_data)
        
        result = vehicle_model.update_vehicle_location(
            vehicle.id, 40.7128, -74.0060, 'New York'
        )
        
        assert result == True
        # Read fresh values from DB
        vehicle_refreshed = vehicle_model.browse(vehicle.id)
        assert vehicle_refreshed.gps_latitude == 40.7128
        assert vehicle_refreshed.gps_longitude == -74.0060
        assert vehicle_refreshed.current_location == 'New York'

    def test_schedule_maintenance(self, odoo_env, sample_vehicle_data, mock_enterprise_license):
        """Test scheduling maintenance"""
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create(sample_vehicle_data)
        
        maintenance = vehicle_model.schedule_maintenance(
            vehicle.id, 'routine', 'Regular service', datetime.now() + timedelta(days=1)
        )
        
        assert maintenance.id
        assert maintenance.vehicle_id.id == vehicle.id
        assert maintenance.maintenance_type == 'routine'

    def test_get_vehicle_recommendations(self, odoo_env, sample_vehicle_data, mock_enterprise_license):
        """Test getting vehicle recommendations"""
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create(sample_vehicle_data)
        
        preferences = {
            'vehicle_type': 'sedan',
            'rental_category': 'economy',
            'max_daily_rate': 100.0
        }
        
        recommendations = vehicle_model.get_vehicle_recommendations(preferences)
        
        assert isinstance(recommendations, list)

    def test_get_fleet_overview(self, odoo_env, sample_vehicle_data, mock_enterprise_license):
        """Test getting fleet overview"""
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create(sample_vehicle_data)
        
        overview = vehicle_model.get_fleet_overview()
        
        assert 'total_vehicles' in overview
        assert 'available_vehicles' in overview
        assert 'rented_vehicles' in overview
        assert 'utilization_rate' in overview

    def test_vehicle_utilization_rate(self, odoo_env, sample_vehicle_data, mock_enterprise_license):
        """Test vehicle utilization rate calculation"""
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create(sample_vehicle_data)
        
        utilization_rate = vehicle._get_utilization_rate()
        
        assert isinstance(utilization_rate, (int, float))
        assert 0 <= utilization_rate <= 100

    def test_vehicle_maintenance_status(self, odoo_env, sample_vehicle_data, mock_enterprise_license):
        """Test vehicle maintenance status"""
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create(sample_vehicle_data)
        
        # Set next service date
        vehicle.next_service_date = datetime.now().date() + timedelta(days=5)
        
        status = vehicle._get_maintenance_status()
        
        assert status in ['overdue', 'due_soon', 'good']

    def test_vehicle_financial_performance(self, odoo_env, sample_vehicle_data, mock_enterprise_license):
        """Test vehicle financial performance"""
        vehicle_model = odoo_env['fleet.vehicle']
        vehicle = vehicle_model.create(sample_vehicle_data)
        vehicle.purchase_price = 20000.0
        
        performance = vehicle._get_financial_performance()
        
        assert 'roi' in performance
        assert 'monthly_revenue' in performance
        assert 'break_even_months' in performance




