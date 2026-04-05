#!/usr/bin/env python3
"""
Create YANS HOLIDAY PTE LTD customer and Balaji Group Japan Visit product in Odoo
"""
import xmlrpc.client
import ssl
import os

# Odoo connection
URL = os.environ.get("ODOO_URL", "https://odoo.emoment.tech")
DB = os.environ.get("ODOO_DB", "odoo")
USERNAME = os.environ.get("ODOO_USERNAME", "admin")
PASSWORD = os.environ["ODOO_PASSWORD"]  # Required, no default for security

def main():
    # Allow self-signed certs if needed
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common', context=ctx)
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        print("Authentication failed! Check credentials.")
        return
    print(f"Connected to Odoo (UID: {uid})")

    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=ctx)

    # --- 1. Create Customer: YANS HOLIDAY PTE LTD ---
    # Check if customer already exists
    existing = models.execute_kw(DB, uid, PASSWORD,
        'res.partner', 'search',
        [[['name', '=', 'YANS HOLIDAY PTE LTD']]]
    )

    if existing:
        partner_id = existing[0]
        print(f"Customer already exists (ID: {partner_id}), updating...")
        models.execute_kw(DB, uid, PASSWORD,
            'res.partner', 'write',
            [[partner_id], {
                'street': '42, Cuff Road',
                'city': 'Singapore',
                'zip': '209752',
                'phone': '+65-97377949 / 97377089',
                'email': 'yansholiday@gmail.com',
                'is_company': True,
                'customer_rank': 1,
            }]
        )
    else:
        # Find Singapore country
        sg_country = models.execute_kw(DB, uid, PASSWORD,
            'res.country', 'search',
            [[['code', '=', 'SG']]]
        )
        country_id = sg_country[0] if sg_country else False

        partner_id = models.execute_kw(DB, uid, PASSWORD,
            'res.partner', 'create',
            [{
                'name': 'YANS HOLIDAY PTE LTD',
                'company_type': 'company',
                'is_company': True,
                'street': '42, Cuff Road',
                'city': 'Singapore',
                'zip': '209752',
                'country_id': country_id,
                'phone': '+65-97377949 / 97377089',
                'email': 'yansholiday@gmail.com',
                'customer_rank': 1,
            }]
        )
        print(f"Created customer: YANS HOLIDAY PTE LTD (ID: {partner_id})")

    # --- 2. Create Product: Balaji Group Japan Visit ---
    # 960,000 JPY = 7,708.80 SGD (rate: 0.00803)
    price_sgd = 960000 * 0.00803  # 7708.80

    existing_product = models.execute_kw(DB, uid, PASSWORD,
        'product.template', 'search',
        [[['name', '=', 'Balaji Group Japan Visit']]]
    )

    if existing_product:
        product_id = existing_product[0]
        print(f"Product already exists (ID: {product_id}), updating...")
        models.execute_kw(DB, uid, PASSWORD,
            'product.template', 'write',
            [[product_id], {
                'list_price': price_sgd,
                'taxes_id': [(5, 0, 0)],  # Remove all taxes
            }]
        )
    else:
        product_id = models.execute_kw(DB, uid, PASSWORD,
            'product.template', 'create',
            [{
                'name': 'Balaji Group Japan Visit',
                'type': 'service',
                'list_price': price_sgd,
                'taxes_id': [(5, 0, 0)],  # No tax
                'description_sale': 'Balaji group japan visit - Total: 960,000 JPY (equivalent in SGD)',
                'sale_ok': True,
                'purchase_ok': False,
            }]
        )
        print(f"Created product: Balaji Group Japan Visit (ID: {product_id})")
        print(f"  Price: {price_sgd:.2f} SGD (960,000 JPY)")
        print(f"  Tax: None")

    print("\nDone!")

if __name__ == '__main__':
    main()
