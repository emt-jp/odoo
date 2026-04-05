#!/usr/bin/env python3
"""
Check and fix currency on YANS HOLIDAY invoice and product
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

    # Find SGD currency
    sgd_ids = models.execute_kw(DB, uid, PASSWORD,
        'res.currency', 'search',
        [[['name', '=', 'SGD']]]
    )
    if not sgd_ids:
        print("SGD currency not found, checking available currencies...")
        all_currencies = models.execute_kw(DB, uid, PASSWORD,
            'res.currency', 'search_read',
            [[['active', '=', True]]],
            {'fields': ['name', 'symbol']}
        )
        for c in all_currencies:
            print(f"  {c['name']} ({c['symbol']})")

        # Try to activate SGD
        sgd_inactive = models.execute_kw(DB, uid, PASSWORD,
            'res.currency', 'search',
            [[['name', '=', 'SGD'], ['active', '=', False]]]
        )
        if sgd_inactive:
            models.execute_kw(DB, uid, PASSWORD,
                'res.currency', 'write',
                [[sgd_inactive[0]], {'active': True}]
            )
            sgd_ids = sgd_inactive
            print(f"Activated SGD currency (ID: {sgd_ids[0]})")
        else:
            print("SGD currency does not exist at all!")
            return

    sgd_id = sgd_ids[0]
    print(f"SGD currency ID: {sgd_id}")

    # Fix product template currency (pricelist currency)
    product_tmpl_ids = models.execute_kw(DB, uid, PASSWORD,
        'product.template', 'search',
        [[['name', '=', 'Balaji Group Japan Visit']]]
    )
    if product_tmpl_ids:
        print(f"Product template ID: {product_tmpl_ids[0]}")
        # Read current product details
        prod = models.execute_kw(DB, uid, PASSWORD,
            'product.template', 'read',
            [product_tmpl_ids[0]],
            {'fields': ['name', 'list_price', 'currency_id']}
        )
        print(f"  Current currency: {prod[0]['currency_id']}")
        print(f"  Current price: {prod[0]['list_price']}")

    # Fix invoice - need to reset to draft, change currency, then repost
    invoice_id = 1969
    invoice = models.execute_kw(DB, uid, PASSWORD,
        'account.move', 'read',
        [invoice_id],
        {'fields': ['name', 'state', 'currency_id', 'amount_total', 'amount_residual', 'payment_state']}
    )
    print(f"\nInvoice {invoice[0]['name']}:")
    print(f"  Current currency: {invoice[0]['currency_id']}")
    print(f"  State: {invoice[0]['state']}")
    print(f"  Payment state: {invoice[0]['payment_state']}")

    # Reset to draft to change currency
    if invoice[0]['state'] == 'posted':
        print("\nResetting invoice to draft...")
        models.execute_kw(DB, uid, PASSWORD,
            'account.move', 'button_draft',
            [[invoice_id]]
        )

    # Update currency to SGD
    print(f"Setting currency to SGD...")
    models.execute_kw(DB, uid, PASSWORD,
        'account.move', 'write',
        [[invoice_id], {
            'currency_id': sgd_id,
        }]
    )

    # Re-confirm
    print("Re-confirming invoice...")
    models.execute_kw(DB, uid, PASSWORD,
        'account.move', 'action_post',
        [[invoice_id]]
    )

    # Verify
    invoice = models.execute_kw(DB, uid, PASSWORD,
        'account.move', 'read',
        [invoice_id],
        {'fields': ['name', 'state', 'currency_id', 'amount_total', 'amount_residual', 'payment_state']}
    )
    print(f"\nUpdated invoice:")
    print(f"  Currency: {invoice[0]['currency_id']}")
    print(f"  Total: {invoice[0]['amount_total']}")
    print(f"  Amount Due: {invoice[0]['amount_residual']}")
    print(f"  Payment state: {invoice[0]['payment_state']}")

    # Also fix the company/product currency if needed
    # Check company currency
    company = models.execute_kw(DB, uid, PASSWORD,
        'res.company', 'search_read',
        [[]],
        {'fields': ['name', 'currency_id'], 'limit': 1}
    )
    print(f"\nCompany: {company[0]['name']}, Currency: {company[0]['currency_id']}")

    print("\nDone!")

if __name__ == '__main__':
    main()
