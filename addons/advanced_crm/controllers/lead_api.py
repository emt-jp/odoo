# -*- coding: utf-8 -*-

import json
import logging
import re
import time

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = [
    "https://hellojapan.jp",
    "https://www.hellojapan.jp",
    "https://hellojapan-jp.web.app",
    "https://hellojapan-jp.firebaseapp.com",
    "http://localhost:5173",
]

# Simple in-memory rate limit: max 10 requests per IP per minute
_rate_limit = {}
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 60


def _check_rate_limit(ip):
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW
    _rate_limit[ip] = [t for t in _rate_limit.get(ip, []) if t > cutoff]
    if len(_rate_limit[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit[ip].append(now)
    return True


def _validate_email(email):
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email or ""))


INTEREST_MAP = {
    "tour-package": "Tour Package",
    "camping-car": "Camping Car Rental",
    "visa": "Visa Assistance",
    "honeymoon": "Honeymoon Package",
    "corporate": "Corporate Event / MICE",
    "restaurant": "Restaurant Reservations",
    "adventure": "Adventure / Outdoor",
    "medical": "Medical Tourism",
    "other": "Other",
}


class LeadAPIController(http.Controller):

    @http.route(
        "/hellojapan/lead",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    def submit_lead(self, **kwargs):
        ip = request.httprequest.headers.get(
            "X-Forwarded-For", request.httprequest.remote_addr or ""
        ).split(",")[0].strip()

        if not _check_rate_limit(ip):
            return {"error": "Too many requests"}

        data = kwargs

        # Honeypot
        if data.get("website"):
            return {"ok": True}

        name = (data.get("name") or "").strip()[:200]
        email = (data.get("email") or "").strip()[:200]

        if not name or not email:
            return {"error": "Name and email are required"}
        if not _validate_email(email):
            return {"error": "Invalid email"}

        phone = (data.get("phone") or "").strip()[:50] or False
        date_from = (data.get("dateFrom") or "").strip() or False
        date_to = (data.get("dateTo") or "").strip() or False
        group_size = (data.get("groupSize") or "").strip() or False
        interest_key = (data.get("interest") or "").strip()
        interest = INTEREST_MAP.get(interest_key, interest_key) or False
        message = (data.get("message") or "").strip()[:2000] or False
        lang = (data.get("lang") or "en").strip()[:5]

        # Build description
        lines = []
        if date_from:
            lines.append(f"Travel dates: {date_from} → {date_to or 'flexible'}")
        if group_size:
            lines.append(f"Group size: {group_size}")
        if interest:
            lines.append(f"Interest: {interest}")
        if message:
            lines.append(f"\n{message}")

        # UTM params
        utm_source = (data.get("utm_source") or "").strip() or False
        utm_medium = (data.get("utm_medium") or "").strip() or False
        utm_campaign = (data.get("utm_campaign") or "").strip() or False

        utm_lines = []
        if utm_source:
            utm_lines.append(f"Source: {utm_source}")
        if utm_medium:
            utm_lines.append(f"Medium: {utm_medium}")
        if utm_campaign:
            utm_lines.append(f"Campaign: {utm_campaign}")
        if utm_lines:
            lines.append(f"\n--- Ad Tracking ---\n" + "\n".join(utm_lines))

        lines.append(f"\nLanguage: {lang} | Source: contact-form")

        description = "\n".join(lines)

        try:
            lead_vals = {
                "name": f"HelloJapan.jp — {name}",
                "contact_name": name,
                "email_from": email,
                "phone": phone,
                "description": description,
                "type": "lead",
            }

            sudo_env = request.env.sudo()

            # UTM source
            source_name = utm_source or "hellojapan.jp"
            source = sudo_env["utm.source"].search(
                [("name", "=", source_name)], limit=1
            )
            if not source:
                source = sudo_env["utm.source"].create({"name": source_name})
            lead_vals["source_id"] = source.id

            # UTM medium
            if utm_medium:
                medium = sudo_env["utm.medium"].search(
                    [("name", "=", utm_medium)], limit=1
                )
                if not medium:
                    medium = sudo_env["utm.medium"].create({"name": utm_medium})
                lead_vals["medium_id"] = medium.id

            # UTM campaign
            if utm_campaign:
                campaign = sudo_env["utm.campaign"].search(
                    [("name", "=", utm_campaign)], limit=1
                )
                if not campaign:
                    campaign = sudo_env["utm.campaign"].create(
                        {"name": utm_campaign}
                    )
                lead_vals["campaign_id"] = campaign.id

            # Tag with interest
            if interest:
                tag = sudo_env["crm.tag"].search(
                    [("name", "=", interest)], limit=1
                )
                if not tag:
                    tag = sudo_env["crm.tag"].create({"name": interest})
                lead_vals["tag_ids"] = [(4, tag.id)]

            lead = sudo_env["crm.lead"].create(lead_vals)

            _logger.info(
                "HelloJapan lead created: id=%s name=%s email=%s",
                lead.id,
                name,
                email,
            )

            return {"ok": True, "id": lead.id}

        except Exception:
            _logger.exception("Failed to create lead from HelloJapan.jp")
            return {"error": "Internal error"}

    @http.route(
        "/hellojapan/lead/email",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    def submit_email(self, **kwargs):
        """Lightweight endpoint for exit-intent popup (email only)."""
        ip = request.httprequest.headers.get(
            "X-Forwarded-For", request.httprequest.remote_addr or ""
        ).split(",")[0].strip()

        if not _check_rate_limit(ip):
            return {"error": "Too many requests"}

        data = kwargs
        email = (data.get("email") or "").strip()[:200]
        lang = (data.get("lang") or "en").strip()[:5]

        if not _validate_email(email):
            return {"error": "Valid email required"}

        try:
            sudo_env = request.env.sudo()

            source = sudo_env["utm.source"].search(
                [("name", "=", "hellojapan.jp")], limit=1
            )
            if not source:
                source = sudo_env["utm.source"].create({"name": "hellojapan.jp"})

            lead = sudo_env["crm.lead"].create({
                "name": "HelloJapan.jp — Free itinerary request",
                "email_from": email,
                "description": f"Exit-popup email capture\nLanguage: {lang}",
                "type": "lead",
                "source_id": source.id,
            })

            _logger.info(
                "HelloJapan exit-popup lead: id=%s email=%s", lead.id, email
            )
            return {"ok": True}

        except Exception:
            _logger.exception("Failed to create email lead from HelloJapan.jp")
            return {"error": "Internal error"}
