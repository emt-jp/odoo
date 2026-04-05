#!/usr/bin/env python3
"""
Import invoices, customers, and vendors from old Odoo (CVPS) to GCP Odoo.

Source: Odoo 17 on CVPS (46.250.252.111) - JP Company (ID 5) - exported via SQL
Target: Odoo 19 on GCP Cloud Run - eMoment Japan KK (ID 4)
"""

import xmlrpc.client
import json
import sys

# --- Target (GCP Odoo 19) ---
DST_URL = "https://odoo-1060033871022.asia-northeast1.run.app"
DST_DB = "odoo"
DST_USER = "admin"
DST_PWD = "admin"

# --- Mapping (Old CVPS → GCP) ---
SALE_TAX_MAP = {52: 60}       # 10% sale tax
PURCHASE_TAX_MAP = {56: 64}   # 10% purchase tax
SALE_JOURNAL_ID = 37    # GCP Sales journal
PURCHASE_JOURNAL_ID = 38  # GCP Purchase journal
CURRENCY_JPY = 25       # JPY currency ID (same in both)

# Data files (exported via SQL from CVPS)
INVOICES_FILE = "/tmp/cvps_invoices.json"
LINES_FILE = "/tmp/cvps_invoice_lines.json"


def connect_target():
    """Connect to GCP Odoo"""
    print(f"Connecting to target: {DST_URL}")
    common = xmlrpc.client.ServerProxy(f'{DST_URL}/xmlrpc/2/common')
    uid = common.authenticate(DST_DB, DST_USER, DST_PWD, {})
    if not uid:
        print("ERROR: Target authentication failed!")
        sys.exit(1)
    models = xmlrpc.client.ServerProxy(f'{DST_URL}/xmlrpc/2/object')
    print(f"  Connected (UID: {uid})")
    return uid, models


def load_data():
    """Load exported JSON data"""
    print("\n=== Loading exported data ===")
    with open(INVOICES_FILE) as f:
        invoices = json.load(f)
    with open(LINES_FILE) as f:
        lines = json.load(f)

    # Group lines by move_id
    lines_by_move = {}
    for line in lines:
        move_id = line['move_id']
        if move_id not in lines_by_move:
            lines_by_move[move_id] = []
        lines_by_move[move_id].append(line)

    # Attach lines to invoices
    for inv in invoices:
        inv['lines'] = lines_by_move.get(inv['id'], [])

    print(f"  Loaded {len(invoices)} invoices with {len(lines)} lines")
    for inv in invoices:
        print(f"    {inv['name']} ({inv['move_type']}) {inv['partner_name']}: "
              f"{len(inv['lines'])} lines, total={inv['amount_total']}")

    return invoices


def import_invoices(dst_uid, dst_models, invoices):
    """Import invoices into GCP Odoo"""
    print("\n=== Importing Invoices to GCP ===")

    created = 0
    errors = 0

    for inv in invoices:
        try:
            # Determine journal and tax map
            if inv['move_type'] in ('out_invoice', 'out_refund'):
                journal_id = SALE_JOURNAL_ID
                tax_map = SALE_TAX_MAP
            else:
                journal_id = PURCHASE_JOURNAL_ID
                tax_map = PURCHASE_TAX_MAP

            # Build invoice lines
            invoice_lines = []
            for line in inv['lines']:
                # Map tax IDs
                mapped_taxes = []
                for old_tax_id in (line.get('tax_ids') or []):
                    new_tax_id = tax_map.get(old_tax_id)
                    if new_tax_id:
                        mapped_taxes.append(new_tax_id)

                line_vals = {
                    'name': line['name'],
                    'quantity': line['quantity'],
                    'price_unit': line['price_unit'],
                    'discount': line.get('discount', 0) or 0,
                    'tax_ids': [(6, 0, mapped_taxes)] if mapped_taxes else False,
                }

                # Product ID (same IDs in both systems)
                if line.get('product_id'):
                    line_vals['product_id'] = line['product_id']

                invoice_lines.append((0, 0, line_vals))

            # Create invoice
            move_vals = {
                'move_type': inv['move_type'],
                'journal_id': journal_id,
                'partner_id': inv['partner_id'],
                'currency_id': CURRENCY_JPY,
                'invoice_date': inv['invoice_date'],
                'date': inv['invoice_date'],
                'invoice_line_ids': invoice_lines,
                'ref': inv.get('ref') or inv['name'],
            }

            if inv.get('invoice_date_due'):
                move_vals['invoice_date_due'] = inv['invoice_date_due']
            if inv.get('narration'):
                move_vals['narration'] = inv['narration']

            new_id = dst_models.execute_kw(
                DST_DB, dst_uid, DST_PWD,
                'account.move', 'create',
                [move_vals]
            )

            # Post the invoice if it was posted in source
            if inv['state'] == 'posted':
                dst_models.execute_kw(
                    DST_DB, dst_uid, DST_PWD,
                    'account.move', 'action_post',
                    [[new_id]]
                )
                status = "posted"
            else:
                status = "draft"

            print(f"  OK: {inv['name']} -> ID {new_id} ({status})")
            created += 1

        except Exception as e:
            print(f"  ERROR: {inv['name']} -> {e}")
            errors += 1

    print(f"\n=== Summary ===")
    print(f"  Created: {created}")
    print(f"  Errors:  {errors}")
    return created, errors


def main():
    # Connect to GCP Odoo
    dst_uid, dst_models = connect_target()

    # Load exported data from JSON files
    invoices = load_data()

    if not invoices:
        print("No invoices to import!")
        return

    # Import to target
    created, errors = import_invoices(dst_uid, dst_models, invoices)

    if errors == 0:
        print("\nAll invoices imported successfully!")
    else:
        print(f"\n{errors} invoices failed. Check errors above.")


if __name__ == '__main__':
    main()
