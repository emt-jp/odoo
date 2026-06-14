# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    invoice_hanko = fields.Image(
        string="Invoice Seal (Hanko)",
        max_width=512,
        max_height=512,
        help="Company seal (hanko / 角印) stamped on invoice and quotation PDFs. "
             "Use a transparent PNG so only the seal impression shows.",
    )
    invoice_hanko_show = fields.Boolean(
        string="Stamp Seal on PDFs",
        default=True,
        help="Uncheck to keep the seal on file but hide it from generated PDFs.",
    )
    invoice_hanko_width = fields.Integer(
        string="Seal Width (px)",
        default=95,
        help="Rendered width of the seal on the PDF, in pixels. Height scales "
             "to keep the aspect ratio.",
    )
    invoice_hanko_opacity = fields.Integer(
        string="Seal Opacity (%)",
        default=85,
        help="0-100. Slightly below 100 reads as an ink impression over the text.",
    )
