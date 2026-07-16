#!/usr/bin/env python3
"""
Create TJ TECH vendor + vendor bill for Velfire board repair (2026-04-20)

Invoice:
  - Vendor:    TJ TECH Co., Ltd (TJ TECH 株式会社)
  - Amount:    JPY 1,404,324 (subtotal 1,263,892 + consumption tax 10% 140,432)
  - Service:   アルファード 板金修理費 (Alphard/Velfire board repair)
  - Period:    2026年04月
  - Bank:      SBI Sumishin Net Bank (0038) / 法人第一支店 (106) / 普通 2972531

Environment variables (required):
  ODOO_URL       e.g. https://odoo.emoment.tech
  ODOO_DB        e.g. odoo
  ODOO_USERNAME  e.g. admin
  ODOO_PASSWORD  (required — no default)

Usage:
  export ODOO_PASSWORD=...
  python3 scripts/create_tjtech_vendor_bill.py
"""
import os
import ssl
import xmlrpc.client
from datetime import date

URL = os.environ.get("ODOO_URL", "https://odoo.emoment.tech")
DB = os.environ.get("ODOO_DB", "odoo")
USERNAME = os.environ.get("ODOO_USERNAME", "admin")
PASSWORD = os.environ["ODOO_PASSWORD"]  # Required

# ---------------------------------------------------------------------
# Invoice data extracted from Scan20260420.pdf
# ---------------------------------------------------------------------
VENDOR = {
    "name": "TJ TECH Co., Ltd",
    "company_type": "company",
    "is_company": True,
    "supplier_rank": 1,
    "street": "Green Haimu Ogino 101, 136-1 Miwa-cho",
    "city": "Machida City",
    "state": "Tokyo",
    "zip": "195-0051",
    "country_code": "JP",
    "phone": "045-90-03083",
    "comment": "テイージエイテック / TJ TECH 株式会社",
}

BANK = {
    "bank_name": "SBI Sumishin Net Bank (住信SBIネット銀行)",
    "bank_code": "0038",
    "branch": "法人第一支店 (Corporate First Branch)",
    "branch_code": "106",
    "account_type": "普通 (Ordinary)",
    "account_number": "2972531",
    "account_holder": "テイージエイテック（カ",
}

BILL = {
    "vendor_ref": "TJTECH-2026-04",      # put real invoice no if present
    "invoice_date": "2026-04-20",
    "description": "アルファード (Velfire/Alphard) 板金修理費 - 2026年04月",
    "subtotal_jpy": 1263892,
    "tax_rate_pct": 10,
    "tax_amount_jpy": 140432,
    "total_jpy": 1404324,
}


def connect():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common", context=ctx)
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        raise SystemExit("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", context=ctx)
    print(f"Connected to {URL} as UID {uid}")
    return uid, models


def call(models, uid, model, method, args, kwargs=None):
    return models.execute_kw(DB, uid, PASSWORD, model, method, args, kwargs or {})


def get_or_create_vendor(models, uid):
    """Search for existing vendor by name; create if missing."""
    existing = call(models, uid, "res.partner", "search",
                    [[["name", "=", VENDOR["name"]], ["supplier_rank", ">", 0]]])
    if existing:
        print(f"Vendor already exists: ID {existing[0]}")
        return existing[0]

    # Resolve JP country id
    country_ids = call(models, uid, "res.country", "search",
                       [[["code", "=", VENDOR["country_code"]]]])
    country_id = country_ids[0] if country_ids else False

    # Resolve Tokyo state id (optional)
    state_ids = []
    if country_id:
        state_ids = call(models, uid, "res.country.state", "search",
                         [[["country_id", "=", country_id],
                           ["name", "ilike", VENDOR["state"]]]])

    vendor_vals = {
        "name": VENDOR["name"],
        "company_type": VENDOR["company_type"],
        "is_company": VENDOR["is_company"],
        "supplier_rank": VENDOR["supplier_rank"],
        "street": VENDOR["street"],
        "city": VENDOR["city"],
        "zip": VENDOR["zip"],
        "phone": VENDOR["phone"],
        "comment": VENDOR["comment"],
    }
    if country_id:
        vendor_vals["country_id"] = country_id
    if state_ids:
        vendor_vals["state_id"] = state_ids[0]

    vendor_id = call(models, uid, "res.partner", "create", [vendor_vals])
    print(f"Created vendor: ID {vendor_id}")
    return vendor_id


def add_bank_account(models, uid, vendor_id):
    """Attach bank account to vendor (idempotent)."""
    existing = call(models, uid, "res.partner.bank", "search",
                    [[["partner_id", "=", vendor_id],
                      ["acc_number", "=", BANK["account_number"]]]])
    if existing:
        print(f"Bank account already linked: ID {existing[0]}")
        return existing[0]

    bank_vals = {
        "partner_id": vendor_id,
        "acc_number": BANK["account_number"],
        "acc_holder_name": BANK["account_holder"],
    }
    # Try to find the bank master record
    bank_ids = call(models, uid, "res.bank", "search",
                    [[["name", "ilike", "SBI Sumishin"]]])
    if not bank_ids:
        # Create bank record
        bank_id = call(models, uid, "res.bank", "create",
                       [{"name": BANK["bank_name"], "bic": ""}])
        bank_vals["bank_id"] = bank_id
        print(f"Created bank master record: ID {bank_id}")
    else:
        bank_vals["bank_id"] = bank_ids[0]

    bank_acc_id = call(models, uid, "res.partner.bank", "create", [bank_vals])
    print(f"Linked bank account: ID {bank_acc_id}")

    # Annotate branch info in vendor comment (Odoo doesn't have native branch code field)
    branch_note = (f"\n\nBank: {BANK['bank_name']}\n"
                   f"Bank Code: {BANK['bank_code']}\n"
                   f"Branch: {BANK['branch']} (Code: {BANK['branch_code']})\n"
                   f"Account Type: {BANK['account_type']}")
    current = call(models, uid, "res.partner", "read", [vendor_id], {"fields": ["comment"]})
    merged = (current[0].get("comment") or "") + branch_note
    call(models, uid, "res.partner", "write", [[vendor_id], {"comment": merged}])
    return bank_acc_id


def find_expense_account(models, uid):
    """Locate a vehicle-repair / expense account. Fallback to any expense account."""
    candidates = call(models, uid, "account.account", "search_read",
                      [[["account_type", "=", "expense"]]],
                      {"fields": ["id", "code", "name"], "limit": 500})
    for kw in ("repair", "maintenance", "vehicle", "修繕", "車両"):
        for a in candidates:
            if kw.lower() in (a["name"] or "").lower():
                print(f"Expense account: {a['code']} {a['name']} (ID {a['id']})")
                return a["id"]
    if candidates:
        a = candidates[0]
        print(f"Fallback expense account: {a['code']} {a['name']} (ID {a['id']})")
        return a["id"]
    raise SystemExit("No expense account found")


def find_purchase_tax(models, uid, rate_pct):
    """Find a Japan 10% purchase tax."""
    tax_ids = call(models, uid, "account.tax", "search_read",
                   [[["type_tax_use", "=", "purchase"],
                     ["amount", "=", float(rate_pct)]]],
                   {"fields": ["id", "name", "amount"], "limit": 5})
    if tax_ids:
        print(f"Purchase tax: {tax_ids[0]['name']} ({tax_ids[0]['amount']}%)")
        return tax_ids[0]["id"]
    print(f"WARNING: no {rate_pct}% purchase tax found — bill will be created tax-free")
    return None


def create_vendor_bill(models, uid, vendor_id):
    """Create vendor bill in draft state."""
    expense_account_id = find_expense_account(models, uid)
    tax_id = find_purchase_tax(models, uid, BILL["tax_rate_pct"])

    line = {
        "name": BILL["description"],
        "quantity": 1,
        "price_unit": BILL["subtotal_jpy"],
        "account_id": expense_account_id,
    }
    if tax_id:
        line["tax_ids"] = [(6, 0, [tax_id])]
    else:
        line["tax_ids"] = [(5, 0, 0)]

    bill_vals = {
        "move_type": "in_invoice",          # Vendor Bill
        "partner_id": vendor_id,
        "ref": BILL["vendor_ref"],
        "invoice_date": BILL["invoice_date"],
        "invoice_line_ids": [(0, 0, line)],
    }
    bill_id = call(models, uid, "account.move", "create", [bill_vals])

    bill = call(models, uid, "account.move", "read", [bill_id],
                {"fields": ["name", "amount_untaxed", "amount_tax",
                            "amount_total", "state", "currency_id"]})[0]
    print(f"\nCreated vendor bill: {bill['name']} (ID {bill_id})")
    print(f"  Subtotal: {bill['amount_untaxed']:,.0f}")
    print(f"  Tax:      {bill['amount_tax']:,.0f}")
    print(f"  Total:    {bill['amount_total']:,.0f}")
    print(f"  State:    {bill['state']} (draft — review and confirm in Odoo)")

    # Sanity check against expected total
    if round(bill["amount_total"]) != BILL["total_jpy"]:
        print(f"\n  WARNING: total mismatch. Expected {BILL['total_jpy']:,}, "
              f"got {bill['amount_total']:,.0f}. Check currency / tax config.")
    return bill_id


def main():
    uid, models = connect()
    print("\n[1/3] Vendor")
    vendor_id = get_or_create_vendor(models, uid)
    print("\n[2/3] Bank account")
    add_bank_account(models, uid, vendor_id)
    print("\n[3/3] Vendor bill")
    create_vendor_bill(models, uid, vendor_id)
    print("\nDone. Review the draft bill in Odoo, then Confirm → Register Payment.")


if __name__ == "__main__":
    main()
