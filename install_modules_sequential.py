#!/usr/bin/env python3
"""
Sequential module installation with better error handling
"""
import xmlrpc.client
import sys
import time

# Odoo connection settings
url = "http://localhost:8069"
db = "odoo"
username = "admin"
password = "admin"

def connect():
    """Connect to Odoo"""
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        if not uid:
            print("ERROR: Authentication failed!")
            sys.exit(1)
        print(f"✓ Connected to Odoo (UID: {uid})")
        return uid
    except Exception as e:
        print(f"ERROR: Connection failed: {str(e)}")
        sys.exit(1)

def install_module_safe(uid, models, module_name, max_retries=3):
    """Install a module with retries"""
    print(f"\n📦 Installing: {module_name}")

    for attempt in range(max_retries):
        try:
            # Check if already installed
            module_ids = models.execute_kw(
                db, uid, password,
                'ir.module.module', 'search',
                [[['name', '=', module_name]]]
            )

            if not module_ids:
                print(f"  ✗ Module not found")
                return False

            module_data = models.execute_kw(
                db, uid, password,
                'ir.module.module', 'read',
                [module_ids],
                {'fields': ['name', 'state']}
            )[0]

            if module_data['state'] == 'installed':
                print(f"  ℹ Already installed")
                return True

            # Install
            print(f"  ⏳ Installing (attempt {attempt + 1}/{max_retries})...")
            models.execute_kw(
                db, uid, password,
                'ir.module.module', 'button_immediate_install',
                [module_ids]
            )

            # Wait a bit
            time.sleep(2)

            # Verify installation
            module_data = models.execute_kw(
                db, uid, password,
                'ir.module.module', 'read',
                [module_ids],
                {'fields': ['state']}
            )[0]

            if module_data['state'] == 'installed':
                print(f"  ✓ Successfully installed")
                return True
            else:
                print(f"  ⚠ State: {module_data['state']}")

        except Exception as e:
            error_msg = str(e)
            if 'already' in error_msg.lower():
                print(f"  ℹ Already installed/installing")
                return True
            print(f"  ✗ Error (attempt {attempt + 1}): {error_msg[:150]}")
            if attempt < max_retries - 1:
                print(f"  ⏳ Waiting before retry...")
                time.sleep(5)

    return False

def main():
    """Main function"""
    print("="*70)
    print("🚀 Sequential Module Installation")
    print("="*70)

    uid = connect()
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

    # Update module list
    print("\n📋 Updating module list...")
    try:
        models.execute_kw(db, uid, password, 'ir.module.module', 'update_list', [])
        print("✓ Module list updated")
    except:
        print("⚠ Could not update list, continuing...")

    # Install in dependency order - one at a time with delays
    modules = [
        ('account', 'Accounting'),
        ('sale', 'Sales'),
        ('crm', 'CRM'),
        ('stock', 'Inventory'),
        ('hr', 'HR'),
        ('project', 'Project'),
        ('car_rental_fleet', 'Car Rental Fleet'),
        ('advanced_analytics', 'Advanced Analytics'),
        ('advanced_crm', 'Advanced CRM'),
        ('advanced_inventory', 'Advanced Inventory'),
        ('advanced_reports', 'Advanced Reports'),
    ]

    results = {}
    for module_name, description in modules:
        result = install_module_safe(uid, models, module_name)
        results[module_name] = result

        if result:
            print(f"  💤 Waiting 3 seconds before next module...")
            time.sleep(3)

    # Summary
    print("\n" + "="*70)
    print("📊 Summary")
    print("="*70)

    for module_name, result in results.items():
        status = "✓" if result else "✗"
        print(f"  {status} {module_name}")

    installed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    print(f"\n✓ Installed: {installed}")
    print(f"✗ Failed: {failed}")
    print("="*70)

if __name__ == '__main__':
    main()
