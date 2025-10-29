# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Add Odoo to Python path
sys.path.insert(0, '/opt/odoo')

# Set up test environment
os.environ['ODOO_RC'] = '/etc/odoo/odoo.conf'
os.environ['TESTING'] = 'true'

@pytest.fixture(scope='session')
def odoo_env():
    """Create Odoo environment for testing"""
    import odoo
    from odoo import api, SUPERUSER_ID
    
    # Initialize Odoo
    odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf'])

    # Connect to database and create an environment
    db = odoo.sql_db.db_connect('odoo_test')
    with db.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        yield env

@pytest.fixture
def test_db():
    """Test database fixture"""
    return 'odoo_test'

@pytest.fixture
def test_user():
    """Test user fixture"""
    return {
        'name': 'Test User',
        'login': 'test@example.com',
        'email': 'test@example.com',
        'password': 'test123',
    }

@pytest.fixture
def test_company():
    """Test company fixture"""
    return {
        'name': 'Test Company',
        'currency_id': 1,  # USD
        'country_id': 233,  # United States
    }

@pytest.fixture
def mock_enterprise_license():
    """Deprecated: enterprise licensing removed"""
    yield None

@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing"""
    with patch('redis.Redis') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_celery():
    """Mock Celery for testing"""
    with patch('celery.Celery') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def sample_vehicle_data():
    """Sample vehicle data for testing"""
    return {
        'name': 'Test Vehicle 001',
        'license_plate': 'TEST001',
        'vehicle_type': 'sedan',
        'rental_category': 'economy',
        'engine_type': 'gasoline',
        'transmission': 'automatic',
        'seating_capacity': 5,
        'daily_rate': 50.0,
        'weekly_rate': 300.0,
        'monthly_rate': 1000.0,
        'is_rental_vehicle': True,
    }

@pytest.fixture
def sample_rental_data(odoo_env):
    """Sample rental data for testing with concrete records and datetime objects"""
    from datetime import datetime
    # Ensure a customer exists
    customer = odoo_env['res.partner'].create({
        'name': 'Test Customer',
        'email': 'customer@test.com',
    })
    # Ensure a vehicle exists
    vehicle = odoo_env['fleet.vehicle'].create({
        'name': 'Test Vehicle 001',
        'license_plate': 'TEST001',
        'vehicle_type': 'sedan',
        'rental_category': 'economy',
        'daily_rate': 50.0,
        'is_rental_vehicle': True,
        'availability_status': 'available',
    })
    return {
        'customer_id': customer.id,
        'vehicle_id': vehicle.id,
        'start_date': datetime(2024, 1, 1, 10, 0, 0),
        'end_date': datetime(2024, 1, 3, 10, 0, 0),
        'pickup_location': 'Test Location',
        'return_location': 'Test Location',
        'daily_rate': 50.0,
    }

@pytest.fixture
def sample_booking_data(odoo_env):
    """Sample booking data for testing with concrete records and datetime objects"""
    from datetime import datetime
    customer = odoo_env['res.partner'].create({
        'name': 'Test Customer',
        'email': 'customer@test.com',
    })
    return {
        'customer_id': customer.id,
        'pickup_date': datetime(2024, 1, 1, 10, 0, 0),
        'return_date': datetime(2024, 1, 3, 10, 0, 0),
        'pickup_location': 'Test Location',
        'return_location': 'Test Location',
        'vehicle_type': 'sedan',
        'rental_category': 'economy',
    }

@pytest.fixture
def sample_maintenance_data(odoo_env):
    """Sample maintenance data for testing with concrete records and datetime objects"""
    from datetime import datetime
    vehicle = odoo_env['fleet.vehicle'].create({
        'name': 'Test Vehicle M',
        'license_plate': 'MAINT001',
        'vehicle_type': 'sedan',
        'rental_category': 'economy',
        'daily_rate': 50.0,
        'is_rental_vehicle': True,
        'availability_status': 'available',
    })
    return {
        'vehicle_id': vehicle.id,
        'maintenance_type': 'routine',
        'description': 'Regular maintenance service',
        'scheduled_date': datetime(2024, 1, 1, 9, 0, 0),
        'priority': 'medium',
        'estimated_duration': 2.0,
    }

@pytest.fixture
def sample_fuel_data(odoo_env):
    """Sample fuel data for testing with concrete records"""
    vehicle = odoo_env['fleet.vehicle'].create({
        'name': 'Test Vehicle F',
        'license_plate': 'FUEL001',
        'vehicle_type': 'sedan',
        'rental_category': 'economy',
        'daily_rate': 50.0,
        'is_rental_vehicle': True,
        'availability_status': 'available',
    })
    return {
        'vehicle_id': vehicle.id,
        'fuel_type': 'gasoline',
        'fuel_quantity': 50.0,
        'fuel_unit': 'liters',
        'unit_price': 1.5,
        'refuel_location': 'Test Station',
        'odometer_reading': 10000,
    }

@pytest.fixture
def sample_insurance_data(odoo_env):
    """Sample insurance data for testing with concrete records"""
    vehicle = odoo_env['fleet.vehicle'].create({
        'name': 'Test Vehicle I',
        'license_plate': 'INS001',
        'vehicle_type': 'sedan',
        'rental_category': 'economy',
        'daily_rate': 50.0,
        'is_rental_vehicle': True,
        'availability_status': 'available',
    })
    return {
        'vehicle_id': vehicle.id,
        'policy_number': 'POL001',
        'insurance_company': 'Test Insurance',
        'insurance_type': 'comprehensive',
        'coverage_amount': 50000.0,
        'premium_amount': 1000.0,
        'start_date': '2024-01-01',
        'expiry_date': '2024-12-31',
    }

@pytest.fixture
def sample_analytics_data():
    """Sample analytics data for testing"""
    return {
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'report_type': 'fleet_overview',
    }

# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security test"
    )
    config.addinivalue_line(
        "markers", "enterprise: mark test as enterprise feature test"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    for item in items:
        # Add enterprise marker to tests in enterprise modules
        if 'enterprise' in item.nodeid:
            item.add_marker(pytest.mark.enterprise)
        
        # Add unit marker to tests in unit directory
        if 'unit' in item.nodeid:
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to tests in integration directory
        if 'integration' in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Add e2e marker to tests in e2e directory
        if 'e2e' in item.nodeid:
            item.add_marker(pytest.mark.e2e)
        
        # Add performance marker to tests in performance directory
        if 'performance' in item.nodeid:
            item.add_marker(pytest.mark.performance)
        
        # Add security marker to tests in security directory
        if 'security' in item.nodeid:
            item.add_marker(pytest.mark.security)




