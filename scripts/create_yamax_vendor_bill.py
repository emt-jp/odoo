#!/usr/bin/env python3
"""
Create Yamax Estate vendor + move-in settlement bill (Monfore Jujo A)

Invoice (精算表): モンフォーレ十条 A rental settlement
  - Landlord:  株式会社ヤマックス・エステート (Yamax Estate Co., Ltd)
  - Tenant:    株式会社eMoment Japan KK
  - Property:  モンフォーレ十条 A
  - Due date:  2026-04-23 AM
  - Total:     ¥548,300

Line breakdown (6 accounting lines):
  1. Shop rent (May+Jun)         ¥140,000 + 10% tax ¥14,000 = ¥154,000
  2. Shop common fee (May+Jun)    ¥12,000 + 10% tax ¥1,200  = ¥13,200
  3. Residential rent (May+Jun)   ¥154,000  (tax-exempt under JP law)
  4. Guarantor fee                ¥146,000 + 10% tax ¥14,600 = ¥160,600
  5. Insurance 2yr (PREPAID)      ¥44,500   (tax-exempt)
  6. Name-change admin fee        ¥20,000 + 10% tax ¥2,000   = ¥22,000
  TOTAL:                                                    = ¥548,300

Bank transfer to:
  Mizuho Bank (0001) Oku Branch (497) / 普通 1976387 / 株式会社ヤマックス・エステート

Env vars:
  ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD
"""
import os, ssl, xmlrpc.client

URL = os.environ.get("ODOO_URL", "https://odoo.emoment.tech")
DB = os.environ.get("ODOO_DB", "odoo")
USERNAME = os.environ.get("ODOO_USERNAME", "admin")
PASSWORD = os.environ["ODOO_PASSWORD"]

# --------------------- Data ---------------------
VENDOR = {
    "name": "株式会社ヤマックス・エステート (Yamax Estate Co., Ltd)",
    "vat": "T2011501007324",   # Qualified invoice registration number
    "street": "1-3-9 Showacho",
    "city": "Kita-ku, Tokyo",
    "zip": "114-0011",
    "phone": "03-5692-7272",
    "comment": ("Landlord for モンフォーレ十条 A\n"
                "Qualified invoice no: T2011501007324"),
}

BANK = {
    "bank_name": "Mizuho Bank (みずほ銀行)",
    "bank_code": "0001",
    "branch_name": "尾久支店 (Oku Branch)",
    "branch_code": "497",
    "account_type": "普通 (Ordinary)",
    "account_number": "1976387",
    "account_holder": "株式会社ヤマックス・エステート",
}

BILL = {
    "ref": "MONFORE-2026-04",          # use invoice number if available
    "invoice_date": "2026-04-23",      # also payment due date
    "date_due": "2026-04-23",
}

# Account IDs discovered earlier from the chart of accounts
ACCT_RENTAL = 395            # 511700 Rental Expenses
ACCT_COMMISSION = 402        # 512400 Commission Expenses (for guarantor + admin fee)
ACCT_INSURANCE = 390         # 511200 Insurance Expenses
# Note: no "prepaid expenses" asset account was in the expense list — book insurance
# to 511200 for now, flag to accountant for prepaid treatment manually if required.

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common", context=ctx)
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
if not uid:
    raise SystemExit("Odoo authentication failed")
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", context=ctx)


def call(model, method, args, kwargs=None):
    return models.execute_kw(DB, uid, PASSWORD, model, method, args, kwargs or {})


# --------------------- 1. Vendor ---------------------
existing = call("res.partner", "search",
                [[["vat", "=", VENDOR["vat"]]]])
if not existing:
    existing = call("res.partner", "search",
                    [[["name", "ilike", "ヤマックス"]]])

if existing:
    vendor_id = existing[0]
    print(f"Vendor exists: ID {vendor_id}")
else:
    jp_country = call("res.country", "search",
                      [[["code", "=", "JP"]]])
    vals = {
        "name": VENDOR["name"],
        "company_type": "company",
        "is_company": True,
        "supplier_rank": 1,
        "street": VENDOR["street"],
        "city": VENDOR["city"],
        "zip": VENDOR["zip"],
        "phone": VENDOR["phone"],
        "vat": VENDOR["vat"],
        "comment": VENDOR["comment"],
    }
    if jp_country:
        vals["country_id"] = jp_country[0]
    vendor_id = call("res.partner", "create", [vals])
    print(f"Created vendor: ID {vendor_id}")

# --------------------- 2. Bank account ---------------------
existing_acc = call("res.partner.bank", "search",
                    [[["partner_id", "=", vendor_id],
                      ["acc_number", "=", BANK["account_number"]]]])
if existing_acc:
    print(f"Bank account exists: ID {existing_acc[0]}")
else:
    bank_master = call("res.bank", "search",
                       [[["name", "ilike", "Mizuho"]]])
    if not bank_master:
        bank_master = [call("res.bank", "create",
                            [{"name": BANK["bank_name"]}])]
        print(f"Created Mizuho bank master: ID {bank_master[0]}")
    acc_id = call("res.partner.bank", "create",
                  [{
                      "partner_id": vendor_id,
                      "acc_number": BANK["account_number"],
                      "acc_holder_name": BANK["account_holder"],
                      "bank_id": bank_master[0],
                  }])
    print(f"Created bank account: ID {acc_id}")
    # Append branch info to vendor comment
    current = call("res.partner", "read", [vendor_id], {"fields": ["comment"]})[0]
    note = (f"\n\nBank: {BANK['bank_name']} ({BANK['bank_code']})\n"
            f"Branch: {BANK['branch_name']} ({BANK['branch_code']})\n"
            f"Account: {BANK['account_type']} {BANK['account_number']}\n"
            f"Holder: {BANK['account_holder']}")
    merged = (current.get("comment") or "") + note
    call("res.partner", "write", [[vendor_id], {"comment": merged}])

# --------------------- 3. Tax ---------------------
tax_10_ids = call("account.tax", "search",
                  [[["type_tax_use", "=", "purchase"], ["amount", "=", 10.0]]],
                  {"limit": 1})
tax_10 = tax_10_ids[0] if tax_10_ids else None

# --------------------- 4. Bill ---------------------
def line(name, amount, account_id, taxed=True):
    vals = {
        "name": name,
        "quantity": 1,
        "price_unit": amount,
        "account_id": account_id,
    }
    if taxed and tax_10:
        vals["tax_ids"] = [(6, 0, [tax_10])]
    else:
        vals["tax_ids"] = [(5, 0, 0)]
    return (0, 0, vals)

lines = [
    line("店舗家賃 Shop rent (May+Jun 2026) - モンフォーレ十条A",
         140000, ACCT_RENTAL, taxed=True),
    line("店舗共益費 Shop common fee (May+Jun 2026)",
         12000, ACCT_RENTAL, taxed=True),
    line("住居家賃 Residential rent (May+Jun 2026) - 非課税",
         154000, ACCT_RENTAL, taxed=False),
    line("保証会社加入料 Guarantor enrolment fee (one-time)",
         146000, ACCT_COMMISSION, taxed=True),
    line("総合補償保険 Insurance 2yr (PREPAID — accountant to amortise ¥1,854/mo × 24)",
         44500, ACCT_INSURANCE, taxed=False),
    line("名義変更事務手数料 Name-change admin fee",
         20000, ACCT_COMMISSION, taxed=True),
]

bill_id = call("account.move", "create",
               [{
                   "move_type": "in_invoice",
                   "partner_id": vendor_id,
                   "ref": BILL["ref"],
                   "invoice_date": BILL["invoice_date"],
                   "invoice_date_due": BILL["date_due"],
                   "invoice_line_ids": lines,
               }])

bill = call("account.move", "read", [bill_id],
            {"fields": ["name", "state", "amount_untaxed",
                        "amount_tax", "amount_total"]})[0]
print(f"\nCreated bill (draft): ID {bill_id}")
print(f"  Subtotal: ¥{bill['amount_untaxed']:,.0f}")
print(f"  Tax:      ¥{bill['amount_tax']:,.0f}")
print(f"  Total:    ¥{bill['amount_total']:,.0f}")
print(f"  Target:   ¥548,300")
if round(bill["amount_total"]) == 548300:
    print("  ✓ matches invoice total")
else:
    print("  ✗ mismatch — investigate")
