# -*- coding: utf-8 -*-
import base64
import logging
import os

from . import models

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Seed the eMoment Japan KK company seal from the bundled PNG.

    Matches the company by name (the seal is eMoment Japan KK's) rather than a
    hardcoded id, because the entity is company id 4 in production but ids
    differ across databases. Only fills an empty seal, so re-running an upgrade
    never clobbers a seal set in the UI. If no eMoment Japan company exists,
    falls back to the main company.
    """
    Company = env["res.company"]
    companies = Company.search([("name", "ilike", "eMoment Japan")])
    if not companies:
        main = env.ref("base.main_company", raise_if_not_found=False)
        companies = main or Company.browse()
    if not companies:
        return
    path = os.path.join(os.path.dirname(__file__), "static", "src", "img", "hanko.png")
    try:
        with open(path, "rb") as fh:
            data = base64.b64encode(fh.read())
    except OSError as err:
        _logger.warning("emt_invoice_hanko: could not read seal image: %s", err)
        return
    for company in companies:
        if not company.invoice_hanko:
            company.invoice_hanko = data
            _logger.info("emt_invoice_hanko: seeded seal on company %s (id=%s)",
                         company.name, company.id)
