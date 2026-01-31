#!/usr/bin/env python3
"""
Test script to verify module installation and basic functionality
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

def check_module_installed(uid, models, module_name):
    """Check if module is installed"""
    models.execute_kw(
        db, uid, password,
        'ir.module.module', 'search_read',
        [[['name', '=', module_name], ['state', '=', 'installed']]],
        {'fields': ['name', 'state', 'summary']}
    )
    result = models.execute_kw(
        db, uid, password,
        'ir.module.module', 'search_read',
        [[['name', '=', module_name]]],
        {'fields': ['name', 'state', 'summary']}
    )
    return result

def install_module(uid, models, module_name):
    """Install a module"""
    print(f"\n📦 Installing module: {module_name}")
    module_ids = models.execute_kw(
        db, uid, password,
        'ir.module.module', 'search',
        [[['name', '=', module_name]]]
    )
    if not module_ids:
        print(f"  ✗ Module {module_name} not found!")
        return False
    
    try:
        models.execute_kw(
            db, uid, password,
            'ir.module.module', 'button_immediate_install',
            [module_ids]
        )
        print(f"  ✓ Module {module_name} installation initiated")
        return True
    except Exception as e:
        print(f"  ✗ Error installing {module_name}: {e}")
        return False

def test_model_exists(uid, models, model_name):
    """Test if a model exists"""
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
        print(f"  ✗ Model {model_name} error: {e}")
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
        print(f"  ✗ Error creating record in {model_name}: {e}")
        return False

def test_insurance_module(uid, models):
    """Test insurance documentation module"""
    print("\n" + "="*60)
    print("🧪 Testing Insurance Documentation Module")
    print("="*60)
    
    # Test models
    models_to_test = [
        'fleet.insurance',
        'fleet.insurance.claim',
        'fleet.document'
    ]
    
    results = {}
    for model_name in models_to_test:
        print(f"\n📋 Testing model: {model_name}")
        results[model_name] = test_model_exists(uid, models, model_name)
    
    # Test creating a vehicle first (required for insurance)
    print("\n🚗 Creating test vehicle...")
    vehicle_id = test_create_record(uid, models, 'fleet.vehicle', {
        'name': 'Test Vehicle - Insurance Module',
        'license_plate': 'TEST-001',
    })
    
    if not vehicle_id:
        print("  ⚠ Cannot test insurance without a vehicle")
        return results
    
    # Test creating insurance policy
    print("\n📄 Testing Insurance Policy Creation...")
    today = datetime.now().date()
    future_date = today + timedelta(days=365)
    
    insurance_id = test_create_record(uid, models, 'fleet.insurance', {
        'vehicle_id': vehicle_id,
        'policy_number': 'TEST-POL-001',
        'insurance_company': 'Test Insurance Co.',
        'insurance_type': 'comprehensive',
        'coverage_amount': 50000.0,
        'premium_amount': 1200.0,
        'start_date': str(today),
        'expiry_date': str(future_date),
        'status': 'active',
    })
    
    if insurance_id:
        results['insurance_create'] = True
        
        # Test creating a claim
        print("\n📋 Testing Insurance Claim Creation...")
        claim_id = test_create_record(uid, models, 'fleet.insurance.claim', {
            'insurance_id': insurance_id,
            'claim_number': 'TEST-CLAIM-001',
            'claim_date': str(today),
            'incident_date': str(today),
            'incident_location': 'Test Location',
            'claim_type': 'accident',
            'claim_amount': 5000.0,
            'description': 'Test claim description',
            'status': 'submitted',
        })
        results['claim_create'] = bool(claim_id)
        
        # Test creating a document
        print("\n📑 Testing Document Creation...")
        # Note: document_file is required, but we'll skip binary for now
        try:
            doc_id = test_create_record(uid, models, 'fleet.document', {
                'vehicle_id': vehicle_id,
                'document_type': 'registration',
                'document_name': 'Test Registration',
                'document_number': 'DOC-001',
                'issue_date': str(today),
                'expiry_date': str(future_date),
                'document_file': False,  # Skip binary for test
            })
            results['document_create'] = bool(doc_id)
        except Exception as e:
            print(f"  ⚠ Document creation skipped (binary field required): {e}")
            results['document_create'] = False
    
    return results

def main():
    """Main test function"""
    print("="*60)
    print("🚀 Odoo Module Testing Script")
    print("="*60)
    
    # Connect
    uid = connect()
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    # Check module status
    print("\n📦 Checking module status...")
    module_status = check_module_installed(uid, models, 'car_rental_fleet')
    
    if module_status:
        for module in module_status:
            print(f"  Module: {module['name']}")
            print(f"  State: {module['state']}")
            if 'summary' in module:
                print(f"  Summary: {module['summary']}")
    
    # Install if not installed
    if not module_status or module_status[0]['state'] != 'installed':
        print("\n⚠ Module not installed. Attempting installation...")
        if install_module(uid, models, 'car_rental_fleet'):
            print("  ⏳ Please wait for installation to complete, then run this script again.")
            return
    else:
        print("\n✓ Module is installed")
    
    # Test insurance module
    results = test_insurance_module(uid, models)
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("⚠ Some tests failed. Check the output above.")
    print("="*60)

if __name__ == '__main__':
    main()

