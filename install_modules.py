#!/usr/bin/env python3
"""
Script to install and test custom Odoo modules
"""
import xmlrpc.client
import sys

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

def update_module_list(uid, models):
    """Update the module list"""
    print("\n📋 Updating module list...")
    try:
        models.execute_kw(
            db, uid, password,
            'ir.module.module', 'update_list',
            []
        )
        print("✓ Module list updated successfully")
        return True
    except Exception as e:
        print(f"✗ Error updating module list: {str(e)}")
        return False

def get_module_info(uid, models, module_name):
    """Get module information"""
    try:
        module_ids = models.execute_kw(
            db, uid, password,
            'ir.module.module', 'search',
            [[['name', '=', module_name]]]
        )
        if module_ids:
            module_data = models.execute_kw(
                db, uid, password,
                'ir.module.module', 'read',
                [module_ids],
                {'fields': ['name', 'state', 'summary']}
            )
            return module_data[0] if module_data else None
        return None
    except Exception as e:
        print(f"✗ Error getting module info: {str(e)}")
        return None

def install_module(uid, models, module_name):
    """Install a module"""
    print(f"\n📦 Installing module: {module_name}")

    # Get module info
    module_info = get_module_info(uid, models, module_name)
    if not module_info:
        print(f"  ✗ Module {module_name} not found in system")
        return False

    current_state = module_info['state']
    print(f"  Current state: {current_state}")

    if current_state == 'installed':
        print(f"  ℹ Module {module_name} is already installed")
        return True

    try:
        # Find the module
        module_ids = models.execute_kw(
            db, uid, password,
            'ir.module.module', 'search',
            [[['name', '=', module_name]]]
        )

        if not module_ids:
            print(f"  ✗ Module {module_name} not found")
            return False

        # Install the module
        models.execute_kw(
            db, uid, password,
            'ir.module.module', 'button_immediate_install',
            [module_ids]
        )

        print(f"  ✓ Module {module_name} installed successfully")
        return True

    except Exception as e:
        error_msg = str(e)
        print(f"  ✗ Error installing module: {error_msg[:200]}")
        return False

def main():
    """Main installation function"""
    print("="*70)
    print("🚀 Odoo Custom Module Installation")
    print("="*70)

    uid = connect()
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

    # Update module list first
    if not update_module_list(uid, models):
        print("\n⚠ Warning: Failed to update module list, continuing anyway...")

    # List of modules to install in order
    modules_to_install = [
        'sale',
        'crm',
        'stock',
        'product',
        'mail',
        'calendar',
        'hr',
        'fleet',
        'project',
        'account',
        'advanced_analytics',
        'advanced_crm',
        'advanced_inventory',
        'advanced_reports',
        'car_rental_fleet',
    ]

    results = {}

    for module_name in modules_to_install:
        result = install_module(uid, models, module_name)
        results[module_name] = result

    # Summary
    print("\n" + "="*70)
    print("📊 Installation Summary")
    print("="*70)

    installed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    for module_name, result in results.items():
        status = "✓ INSTALLED" if result else "✗ FAILED"
        print(f"  {status}: {module_name}")

    print("\n" + "="*70)
    print(f"Total: {len(results)} modules")
    print(f"✓ Installed: {installed}")
    print(f"✗ Failed: {failed}")
    print("="*70)

    if failed == 0:
        print("\n✅ All modules installed successfully!")
    else:
        print(f"\n⚠ {failed} modules failed to install")

if __name__ == '__main__':
    main()
