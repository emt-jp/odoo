#!/usr/bin/env python3
"""
Confirm the YANS HOLIDAY invoice and register a 2000 SGD partial payment
"""
import xmlrpc.client
import ssl
import os

URL = os.environ.get("ODOO_URL", "https://odoo.emoment.tech")
DB = os.environ.get("ODOO_DB", "odoo")
USERNAME = os.environ.get("ODOO_USERNAME", "admin")
PASSWORD = os.environ["ODOO_PASSWORD"]  # Required, no default for security

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

    invoice_id = 1969

    # Check current state
    invoice = models.execute_kw(DB, uid, PASSWORD,
        'account.move', 'read',
        [invoice_id],
        {'fields': ['name', 'state', 'amount_total', 'amount_residual', 'currency_id']}
    )
    print(f"Invoice: {invoice[0]['name']}, State: {invoice[0]['state']}, Total: {invoice[0]['amount_total']}")

    # Step 1: Confirm/post the invoice if still draft
    if invoice[0]['state'] == 'draft':
        print("Confirming invoice...")
        models.execute_kw(DB, uid, PASSWORD,
            'account.move', 'action_post',
            [[invoice_id]]
        )
        # Re-read after posting
        invoice = models.execute_kw(DB, uid, PASSWORD,
            'account.move', 'read',
            [invoice_id],
            {'fields': ['name', 'state', 'amount_total', 'amount_residual', 'currency_id']}
        )
        print(f"Invoice confirmed: {invoice[0]['name']}, State: {invoice[0]['state']}")

    # Step 2: Register partial payment of 2000 SGD
    currency_id = invoice[0]['currency_id'][0] if invoice[0]['currency_id'] else False
    print(f"Registering payment of 2,000 SGD...")

    # Use the register payment wizard
    payment_register = models.execute_kw(DB, uid, PASSWORD,
        'account.payment.register', 'create',
        [{
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': 2000.0,
            'currency_id': currency_id,
        }],
        {'context': {
            'active_model': 'account.move',
            'active_ids': [invoice_id],
        }}
    )
    print(f"Payment register wizard ID: {payment_register}")

    # Execute the payment
    models.execute_kw(DB, uid, PASSWORD,
        'account.payment.register', 'action_create_payments',
        [[payment_register]],
        {'context': {
            'active_model': 'account.move',
            'active_ids': [invoice_id],
        }}
    )

    # Check updated invoice
    invoice = models.execute_kw(DB, uid, PASSWORD,
        'account.move', 'read',
        [invoice_id],
        {'fields': ['name', 'state', 'amount_total', 'amount_residual', 'payment_state']}
    )
    print(f"\nInvoice updated:")
    print(f"  Number: {invoice[0]['name']}")
    print(f"  Total: {invoice[0]['amount_total']} SGD")
    print(f"  Amount Due: {invoice[0]['amount_residual']} SGD")
    print(f"  Payment Status: {invoice[0]['payment_state']}")
    print("\nDone!")

if __name__ == '__main__':
    main()
