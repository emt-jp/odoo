# EMT Invoice Hanko (Company Seal)

Stamps a per-company seal (hanko / 角印) on Odoo 19 invoice PDFs.

## What it adds
- A **per-company** seal image field (`res.company.invoice_hanko`) + display
  controls (show on/off, width, opacity) under **Settings → Companies →
  *company* → "Invoice Seal"** tab.
- A QWeb override (`account.report_invoice_document`) that stamps the seal over
  the totals block of the invoice PDF — the customary place for a 角印.
- A `post_init_hook` that, on first install, seeds the bundled eMoment Japan KK
  seal onto the company **matched by name** (`name ilike 'eMoment Japan'`),
  falling back to the main company. Name-matching (not a hardcoded id) is used
  because eMoment Japan KK is **company id 4** in production but ids differ
  across databases. Only an empty seal is filled, so it never clobbers a seal
  set in the UI.

Multi-company safe: each company carries its own seal. TDC invoices are issued
in Odoo under **company id 4 (eMoment Japan KK)** by the api-adapter
(`createAndSendInvoice`), and the QWeb override reads the seal from the
invoice's own company — so once installed, TDC's emailed invoice PDFs are
stamped automatically with no change to the TDC codebase.

## Install / deploy (GCP Cloud Run)
This Odoo runs on Cloud Run (`odoo-erp-prod`, build from Artifact Registry via
GitHub Actions on push to `main`). To ship:

1. Commit this module under `addons/` (PK pushes — see workspace git policy).
2. CI builds + deploys the image (the module is baked into `addons_path`).
3. In Odoo: **Apps → Update Apps List → install "EMT Invoice Hanko"**
   (or `-u emt_invoice_hanko` on the instance).
4. Verify: open any posted invoice → **Print → Invoice**. The seal sits over the
   totals. Tune width/opacity per company on the "Invoice Seal" tab.

To also stamp **quotations/sale orders**, add a sibling template inheriting
`sale.report_saleorder_document` (same xpath pattern) and add `sale` to depends.

## Note on Japanese invoices
A hanko is **customary, not legally required**. Under the qualified-invoice
system (インボイス制度) what is mandatory is the registration number
(適格請求書発行事業者登録番号, "T" + 13 digits) on the invoice — make sure that is
present (Company → Tax ID / company registry), seal or no seal.
