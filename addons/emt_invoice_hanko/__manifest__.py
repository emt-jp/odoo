# -*- coding: utf-8 -*-
{
    'name': 'EMT Invoice Hanko (Company Seal)',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Stamp a company seal (hanko / 角印) on invoice and quotation PDFs',
    'description': """
EMT Invoice Hanko
=================
Adds a per-company seal image (hanko / 角印) that is stamped on the
invoice PDF (and, optionally, the quotation/sale order PDF).

Each company gets its own seal, so multi-company setups (e.g. eMoment
Japan KK vs Tokyo Driving Club KK) each stamp the correct seal.

Configure under Settings -> Companies -> <company> -> "Invoice Seal".
The seal is positioned over the totals block, the customary place for a
角印 on a Japanese invoice. A hanko is not legally required on Japanese
invoices (the qualified-invoice registration number is) but is customary
for trust.
    """,
    'author': 'eMoment Japan KK',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/res_company_views.xml',
        'report/report_invoice_hanko.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
