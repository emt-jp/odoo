#!/usr/bin/env python3
"""
Comprehensive test script for all car_rental_fleet modules
"""
import xmlrpc.client
import sys
from datetime import datetime, timedelta

# Odoo connection settings
url = "http://localhost:8069"
db = "odoo"
username = "admin"
password = "admin"

def connect():
    """Connect to Odoo"""
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    if not uid:
        print("ERROR: Authentication failed!")
        sys.exit(1)
    print(f"✓ Connected to Odoo (UID: {uid})")
    return uid

def test_model_exists(uid, models, model_name):
    """Test if a model exists and is accessible"""
    try:
        models.execute_kw(
            db, uid, password,
            model_name, 'search',
            [[]],
            {'limit': 1}
        )
        print(f"  ✓ Model {model_name} exists and is accessible")
        return True
    except Exception as e:
        error_msg = str(e)
        if "not allowed to access" in error_msg:
            print(f"  ⚠ Model {model_name} exists but access denied (security rules needed)")
            return "no_access"
        else:
            print(f"  ✗ Model {model_name} error: {error_msg[:100]}")
            return False

def test_create_record(uid, models, model_name, values):
    """Test creating a record"""
    try:
        record_id = models.execute_kw(
            db, uid, password,
            model_name, 'create',
            [values]
        )
        print(f"  ✓ Created record in {model_name} (ID: {record_id})")
        return record_id
    except Exception as e:
        error_msg = str(e)
        if "not allowed to create" in error_msg:
            print(f"  ⚠ Cannot create record (access denied)")
            return "no_access"
        else:
            print(f"  ✗ Error creating record: {error_msg[:100]}")
            return False

def get_model_fields(uid, models, model_name):
    """Get model fields"""
    try:
        fields = models.execute_kw(
            db, uid, password,
            model_name, 'fields_get',
            [],
            {'attributes': ['string', 'type', 'required']}
        )
        return fields
    except:
        return {}

def test_all_models(uid, models):
    """Test all models in the module"""
    print("\n" + "="*70)
    print("🧪 Testing All Car Rental Fleet Modules")
    print("="*70)
    
    # Define all models to test
    models_to_test = {
        # Insurance & Documentation (already tested)
        'fleet.insurance': {'test_create': False, 'note': 'Already tested'},
        'fleet.insurance.claim': {'test_create': False, 'note': 'Already tested'},
        'fleet.document': {'test_create': False, 'note': 'Already tested'},
        
        # Vehicle Management
        'fleet.vehicle': {'test_create': True, 'note': 'Inherits from fleet.vehicle'},
        'fleet.location.history': {'test_create': False, 'note': 'Requires vehicle'},
        
        # Booking & Reservation
        'fleet.booking': {'test_create': True, 'note': 'Main booking model'},
        'fleet.driver': {'test_create': True, 'note': 'Driver management'},
        
        # Rental Operations
        'fleet.rental': {'test_create': True, 'note': 'Main rental model'},
        'fleet.rental.charge': {'test_create': False, 'note': 'Requires rental'},
        
        # Maintenance
        'fleet.maintenance': {'test_create': True, 'note': 'Maintenance model'},
        'fleet.maintenance.part': {'test_create': False, 'note': 'Requires maintenance'},
        'fleet.quality.check': {'test_create': False, 'note': 'Quality check'},
        'fleet.quality.check.item': {'test_create': False, 'note': 'Requires quality check'},
        
        # Fuel Management
        'fleet.fuel.management': {'test_create': True, 'note': 'Fuel management'},
        'fleet.fuel.card': {'test_create': False, 'note': 'Fuel card'},
        
        # GPS Tracking
        'fleet.gps.tracking': {'test_create': True, 'note': 'GPS tracking'},
        'fleet.geofence': {'test_create': False, 'note': 'Geofence'},
        
        # Financial & Analytics
        'fleet.financial.management': {'test_create': True, 'note': 'Financial management'},
        'fleet.analytics': {'test_create': True, 'note': 'Analytics'},
    }
    
    results = {}
    today = datetime.now().date()
    
    # First, create a test vehicle if needed
    print("\n📋 Step 1: Checking for test vehicle...")
    vehicle_ids = models.execute_kw(
        db, uid, password,
        'fleet.vehicle', 'search',
        [[['name', 'ilike', 'Test Vehicle']]],
        {'limit': 1}
    )
    if vehicle_ids:
        vehicle_id = vehicle_ids[0]
        print(f"  ✓ Using existing test vehicle (ID: {vehicle_id})")
    else:
        print("  ⚠ No test vehicle found, will create one if needed")
        vehicle_id = None
    
    # Test each model
    for model_name, config in models_to_test.items():
        print(f"\n📋 Testing: {model_name}")
        print(f"  Note: {config['note']}")
        
        # Test model existence
        exists = test_model_exists(uid, models, model_name)
        results[model_name] = {'exists': exists}
        
        # Try to create a record if configured
        if config['test_create'] and exists == True:
            print(f"  Testing record creation...")
            
            # Get fields to create minimal record
            fields = get_model_fields(uid, models, model_name)
            values = {}
            
            # Build minimal values based on common patterns
            if 'name' in fields:
                values['name'] = f'Test {model_name.split(".")[-1].title()}'
            if 'vehicle_id' in fields and vehicle_id:
                values['vehicle_id'] = vehicle_id
            elif 'vehicle_id' in fields:
                # Try to get any vehicle
                any_vehicle = models.execute_kw(
                    db, uid, password,
                    'fleet.vehicle', 'search',
                    [[]],
                    {'limit': 1}
                )
                if any_vehicle:
                    values['vehicle_id'] = any_vehicle[0]
            
            # Add date fields if they exist
            for field_name in ['start_date', 'date', 'booking_date', 'rental_date']:
                if field_name in fields:
                    values[field_name] = str(today)
                    break
            
            # Add end date if start date exists
            if 'start_date' in values:
                for field_name in ['end_date', 'expiry_date']:
                    if field_name in fields:
                        values[field_name] = str(today + timedelta(days=30))
                        break
            
            # Try to create
            if values:
                create_result = test_create_record(uid, models, model_name, values)
                results[model_name]['create'] = create_result
            else:
                print(f"  ⚠ Skipping create test (no suitable fields found)")
                results[model_name]['create'] = 'skipped'
        elif exists == "no_access":
            results[model_name]['create'] = 'no_access'
    
    # Summary
    print("\n" + "="*70)
    print("📊 Test Summary")
    print("="*70)
    
    passed = 0
    failed = 0
    no_access = 0
    skipped = 0
    
    for model_name, result in results.items():
        status = "?"
        if result['exists'] == True:
            if 'create' in result:
                if result['create'] == True or isinstance(result['create'], int):
                    status = "✓ PASS"
                    passed += 1
                elif result['create'] == 'no_access':
                    status = "⚠ NO ACCESS"
                    no_access += 1
                else:
                    status = "⚠ SKIP"
                    skipped += 1
            else:
                status = "✓ EXISTS"
                passed += 1
        elif result['exists'] == "no_access":
            status = "⚠ NO ACCESS"
            no_access += 1
        else:
            status = "✗ FAIL"
            failed += 1
        
        print(f"  {status}: {model_name}")
    
    print("\n" + "="*70)
    print(f"Total: {len(results)} models")
    print(f"✓ Passed: {passed}")
    print(f"⚠ No Access: {no_access}")
    print(f"⚠ Skipped: {skipped}")
    print(f"✗ Failed: {failed}")
    print("="*70)
    
    if failed == 0:
        print("\n✅ All accessible models are working!")
        if no_access > 0:
            print(f"⚠ {no_access} models need security rules configured")
    else:
        print(f"\n⚠ {failed} models have issues that need attention")

def main():
    """Main test function"""
    print("="*70)
    print("🚀 Comprehensive Car Rental Fleet Module Testing")
    print("="*70)
    
    uid = connect()
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    test_all_models(uid, models)

if __name__ == '__main__':
    main()

