#!/usr/bin/env python3
"""
Create a customer invoice for YANS HOLIDAY PTE LTD with Balaji Group Japan Visit product
"""
import xmlrpc.client
import ssl

URL = "https://odoo.emoment.tech"
DB = "odoo"
USERNAME = "admin"
PASSWORD = "admin"

def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common', context=ctx)
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        print("Authentication failed!")
        return
    print(f"Connected (UID: {uid})")

    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=ctx)

    # Get the customer
    partner_ids = models.execute_kw(DB, uid, PASSWORD,
        'res.partner', 'search',
        [[['name', '=', 'YANS HOLIDAY PTE LTD']]]
    )
    if not partner_ids:
        print("Customer not found!")
        return
    partner_id = partner_ids[0]
    print(f"Found customer ID: {partner_id}")

    # Get the product
    product_ids = models.execute_kw(DB, uid, PASSWORD,
        'product.product', 'search',
        [[['name', '=', 'Balaji Group Japan Visit']]]
    )
    if not product_ids:
        print("Product not found!")
        return
    product_id = product_ids[0]
    print(f"Found product ID: {product_id}")

    # Get product details
    product = models.execute_kw(DB, uid, PASSWORD,
        'product.product', 'read',
        [product_id],
        {'fields': ['list_price', 'name']}
    )
    price = product[0]['list_price']
    print(f"Product price: {price}")

    # Create the invoice
    invoice_id = models.execute_kw(DB, uid, PASSWORD,
        'account.move', 'create',
        [{
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product_id,
                'name': 'Balaji Group Japan Visit - 960,000 JPY equivalent in SGD',
                'quantity': 1,
                'price_unit': price,
                'tax_ids': [(5, 0, 0)],  # No tax
            })],
        }]
    )
    print(f"Created invoice (ID: {invoice_id})")

    # Read invoice number
    invoice = models.execute_kw(DB, uid, PASSWORD,
        'account.move', 'read',
        [invoice_id],
        {'fields': ['name', 'amount_total', 'state']}
    )
    print(f"Invoice: {invoice[0]['name']}")
    print(f"Total: {invoice[0]['amount_total']}")
    print(f"State: {invoice[0]['state']} (draft)")
    print("\nDone! Invoice is in draft - you can review and confirm it in Odoo.")

if __name__ == '__main__':
    main()
