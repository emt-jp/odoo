#!/usr/bin/env python3
"""
Script to export data from remote Odoo instance and import to Docker instance
"""
import xmlrpc.client
import sys
import json
from datetime import datetime

# Remote Odoo connection (od.emoment.tech)
REMOTE_URL = "https://od.emoment.tech"  # Update if different
REMOTE_DB = "odoo"  # Update with your database name
REMOTE_USERNAME = "admin"  # Update with your username
REMOTE_PASSWORD = "admin"  # Update with your password

# Local Docker Odoo connection
LOCAL_URL = "http://localhost:8069"
LOCAL_DB = "odoo"
LOCAL_USERNAME = "admin"
LOCAL_PASSWORD = "admin"

def connect_remote():
    """Connect to remote Odoo instance"""
    print(f"Connecting to remote Odoo: {REMOTE_URL}")
    common = xmlrpc.client.ServerProxy(f'{REMOTE_URL}/xmlrpc/2/common')
    uid = common.authenticate(REMOTE_DB, REMOTE_USERNAME, REMOTE_PASSWORD, {})
    if not uid:
        print("ERROR: Remote authentication failed!")
        print("Please check your credentials in the script.")
        sys.exit(1)
    print(f"✓ Connected to remote Odoo (UID: {uid})")
    return uid

def connect_local():
    """Connect to local Docker Odoo instance"""
    print(f"\nConnecting to local Odoo: {LOCAL_URL}")
    common = xmlrpc.client.ServerProxy(f'{LOCAL_URL}/xmlrpc/2/common')
    uid = common.authenticate(LOCAL_DB, LOCAL_USERNAME, LOCAL_PASSWORD, {})
    if not uid:
        print("ERROR: Local authentication failed!")
        sys.exit(1)
    print(f"✓ Connected to local Odoo (UID: {uid})")
    return uid

def export_model_data(remote_models, model_name, domain=None):
    """Export data from a model"""
    if domain is None:
        domain = []
    
    try:
        # Get all records
        record_ids = remote_models.execute_kw(
            REMOTE_DB, remote_uid, REMOTE_PASSWORD,
            model_name, 'search',
            [domain]
        )
        
        if not record_ids:
            return []
        
        # Read records with all fields
        fields = remote_models.execute_kw(
            REMOTE_DB, remote_uid, REMOTE_PASSWORD,
            model_name, 'fields_get',
            [],
            {'attributes': ['string', 'type', 'required']}
        )
        
        # Get field names (exclude computed and related fields that can't be written)
        field_names = [f for f in fields.keys() 
                      if fields[f].get('type') not in ['one2many', 'many2many'] 
                      and not fields[f].get('readonly', False)
                      and f not in ['id', '__last_update', 'create_uid', 'write_uid', 'create_date', 'write_date']]
        
        # Read records
        records = remote_models.execute_kw(
            REMOTE_DB, remote_uid, REMOTE_PASSWORD,
            model_name, 'read',
            [record_ids],
            {'fields': field_names}
        )
        
        return records
    except Exception as e:
        print(f"  ⚠ Error exporting {model_name}: {e}")
        return []

def import_model_data(local_models, model_name, records):
    """Import data to a model"""
    if not records:
        return 0
    
    imported = 0
    skipped = 0
    
    for record in records:
        try:
            # Remove id and other fields that shouldn't be imported
            data = {k: v for k, v in record.items() 
                   if k not in ['id', '__last_update', 'create_uid', 'write_uid', 'create_date', 'write_date']}
            
            # Try to create
            local_models.execute_kw(
                LOCAL_DB, local_uid, LOCAL_PASSWORD,
                model_name, 'create',
                [data]
            )
            imported += 1
        except Exception as e:
            skipped += 1
            if skipped <= 3:  # Show first 3 errors
                print(f"    ⚠ Skipped record: {str(e)[:80]}")
    
    return imported, skipped

def export_import_models():
    """Export and import specific models"""
    print("\n" + "="*70)
    print("📦 Exporting and Importing Data")
    print("="*70)
    
    # Models to export/import (add more as needed)
    models_to_export = [
        'fleet.vehicle',
        'fleet.booking',
        'fleet.rental',
        'fleet.insurance',
        'fleet.insurance.claim',
        'fleet.document',
        'fleet.maintenance',
        'fleet.driver',
        'fleet.fuel.management',
        'fleet.gps.tracking',
        'res.partner',  # Customers
    ]
    
    results = {}
    
    for model_name in models_to_export:
        print(f"\n📋 Processing: {model_name}")
        
        # Export from remote
        print(f"  Exporting from remote...")
        records = export_model_data(remote_models, model_name)
        print(f"  ✓ Exported {len(records)} records")
        
        if not records:
            results[model_name] = {'exported': 0, 'imported': 0, 'skipped': 0}
            continue
        
        # Import to local
        print(f"  Importing to local...")
        imported, skipped = import_model_data(local_models, model_name, records)
        print(f"  ✓ Imported {imported} records, skipped {skipped}")
        
        results[model_name] = {
            'exported': len(records),
            'imported': imported,
            'skipped': skipped
        }
    
    # Summary
    print("\n" + "="*70)
    print("📊 Import Summary")
    print("="*70)
    for model_name, result in results.items():
        print(f"  {model_name}:")
        print(f"    Exported: {result['exported']}")
        print(f"    Imported: {result['imported']}")
        print(f"    Skipped: {result['skipped']}")
    
    total_exported = sum(r['exported'] for r in results.values())
    total_imported = sum(r['imported'] for r in results.values())
    total_skipped = sum(r['skipped'] for r in results.values())
    
    print("\n" + "="*70)
    print(f"Total: Exported {total_exported}, Imported {total_imported}, Skipped {total_skipped}")
    print("="*70)

def main():
    """Main function"""
    global remote_uid, local_uid, remote_models, local_models
    
    print("="*70)
    print("🔄 Odoo Data Export/Import Tool")
    print("="*70)
    print("\n⚠️  IMPORTANT: Update credentials in the script before running!")
    print(f"   Remote: {REMOTE_URL}")
    print(f"   Local: {LOCAL_URL}\n")
    
    response = input("Have you updated the credentials? (yes/no): ")
    if response.lower() != 'yes':
        print("Please update REMOTE_URL, REMOTE_DB, REMOTE_USERNAME, REMOTE_PASSWORD in the script.")
        sys.exit(1)
    
    # Connect
    remote_uid = connect_remote()
    local_uid = connect_local()
    
    remote_models = xmlrpc.client.ServerProxy(f'{REMOTE_URL}/xmlrpc/2/object')
    local_models = xmlrpc.client.ServerProxy(f'{LOCAL_URL}/xmlrpc/2/object')
    
    # Export and import
    export_import_models()
    
    print("\n✅ Data export/import completed!")

if __name__ == '__main__':
    main()

