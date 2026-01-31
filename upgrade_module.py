#!/usr/bin/env python3
"""Upgrade module via XML-RPC"""
import xmlrpc.client
import sys

url = "http://localhost:8069"
db = "odoo"
username = "admin"
password = "admin"

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
if not uid:
    print("ERROR: Authentication failed!")
    sys.exit(1)

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Find module
module_ids = models.execute_kw(
    db, uid, password,
    'ir.module.module', 'search',
    [[['name', '=', 'car_rental_fleet']]]
)

if not module_ids:
    print("Module not found!")
    sys.exit(1)

print(f"Found module, upgrading...")
try:
    models.execute_kw(
        db, uid, password,
        'ir.module.module', 'button_immediate_upgrade',
        [module_ids]
    )
    print("✓ Module upgrade initiated")
except Exception as e:
    print(f"Error: {e}")

