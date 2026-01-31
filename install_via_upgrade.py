#!/usr/bin/env python3
"""
Install modules using database upgrade approach
"""
import psycopg2
import time

print("="*70)
print("🚀 Installing Odoo Modules via Database Update")
print("="*70)

# Database connection
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="odoo",
    user="odoo",
    password="odoo"
)
cur = conn.cursor()

# List of modules to install
modules_to_install = [
    'auth_signup',
    'portal',
    'account',
    'sale_management',
    'crm',
    'stock',
    'hr',
    'project',
]

print("\n📦 Marking modules for installation...")
for module in modules_to_install:
    try:
        # Check if module exists
        cur.execute(
            "SELECT id, state FROM ir_module_module WHERE name = %s",
            (module,)
        )
        result = cur.fetchone()

        if not result:
            print(f"  ✗ Module {module} not found in database")
            continue

        module_id, current_state = result

        if current_state == 'installed':
            print(f"  ℹ {module}: already installed")
        else:
            # Mark for installation
            cur.execute(
                "UPDATE ir_module_module SET state = 'to install' WHERE id = %s",
                (module_id,)
            )
            conn.commit()
            print(f"  ✓ {module}: marked for installation (was: {current_state})")

    except Exception as e:
        print(f"  ✗ Error with {module}: {str(e)}")
        conn.rollback()

# Now trigger upgrade
print("\n🔄 Modules marked. Restart Odoo to apply changes.")
print("\n" + "="*70)
print("📊 Current module states:")
print("="*70)

cur.execute("""
    SELECT name, state
    FROM ir_module_module
    WHERE name IN ('auth_signup', 'portal', 'account', 'sale_management', 'crm', 'stock', 'hr', 'project', 'car_rental_fleet', 'advanced_analytics', 'advanced_crm', 'advanced_inventory', 'advanced_reports')
    ORDER BY name
""")

for row in cur.fetchall():
    name, state = row
    symbol = "✓" if state == "installed" else "⏳" if state == "to install" else "○"
    print(f"  {symbol} {name}: {state}")

cur.close()
conn.close()

print("\n" + "="*70)
print("✅ Done! Restart Odoo to complete installation.")
print("="*70)
