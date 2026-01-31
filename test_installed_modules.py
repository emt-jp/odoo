#!/usr/bin/env python3
"""
Test currently installed Odoo modules
"""
import xmlrpc.client
import sys

url = "http://localhost:8069"
db = "odoo"
username = "admin"
password = "admin"

def test_module(models, uid, module_name, model_name):
    """Test if a module's main model is accessible"""
    try:
        count = models.execute_kw(
            db, uid, password,
            model_name, 'search_count',
            [[]]
        )
        print(f"  ✓ {module_name}: {model_name} accessible ({count} records)")
        return True
    except Exception as e:
        error = str(e)[:100]
        print(f"  ✗ {module_name}: Error - {error}")
        return False

def main():
    print("="*70)
    print("🧪 Testing Installed Odoo Modules")
    print("="*70)

    # Connect
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        if not uid:
            print("ERROR: Authentication failed!")
            return

        print(f"✓ Connected (UID: {uid})\n")
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

        # Test installed modules
        tests = [
            ("base", "res.users"),
            ("web", "ir.ui.view"),
            ("mail", "mail.message"),
            ("product", "product.product"),
            ("calendar", "calendar.event"),
            ("fleet", "fleet.vehicle"),
            ("bus", "bus.bus"),
        ]

        results = {}
        for module, model in tests:
            results[module] = test_module(models, uid, module, model)

        # Summary
        print("\n" + "="*70)
        print("📊 Test Summary")
        print("="*70)
        passed = sum(1 for v in results.values() if v)
        failed = sum(1 for v in results.values() if not v)

        print(f"✓ Passed: {passed}/{len(results)}")
        print(f"✗ Failed: {failed}/{len(results)}")

        if failed == 0:
            print("\n✅ All installed modules are working correctly!")
        else:
            print(f"\n⚠ {failed} module(s) have issues")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return

if __name__ == '__main__':
    main()
