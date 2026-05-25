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


def _cors_headers(origin):
    headers = {
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "3600",
    }
    if origin in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
    return headers


def _json_response(data, status=200, origin=""):
    body = json.dumps(data)
    headers = _cors_headers(origin)
    headers["Content-Type"] = "application/json"
    return Response(body, status=status, headers=headers)


def _check_rate_limit(ip):
    now = time.time()
    # Clean old entries
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
        "/api/lead",
        type="http",
        auth="none",
        methods=["POST", "OPTIONS"],
        csrf=False,
        cors=False,
    )
    def submit_lead(self, **kwargs):
        origin = request.httprequest.headers.get("Origin", "")

        # CORS preflight
        if request.httprequest.method == "OPTIONS":
            return Response("", status=204, headers=_cors_headers(origin))

        ip = request.httprequest.headers.get(
            "X-Forwarded-For", request.httprequest.remote_addr or ""
        ).split(",")[0].strip()

        if not _check_rate_limit(ip):
            return _json_response({"error": "Too many requests"}, 429, origin)

        try:
            data = json.loads(request.httprequest.data or "{}")
        except (json.JSONDecodeError, TypeError):
            return _json_response({"error": "Invalid JSON"}, 400, origin)

        # Honeypot
        if data.get("website"):
            return _json_response({"ok": True}, 200, origin)

        name = (data.get("name") or "").strip()[:200]
        email = (data.get("email") or "").strip()[:200]

        if not name or not email:
            return _json_response(
                {"error": "Name and email are required"}, 400, origin
            )
        if not _validate_email(email):
            return _json_response({"error": "Invalid email"}, 400, origin)

        phone = (data.get("phone") or "").strip()[:50] or False
        date_from = (data.get("dateFrom") or "").strip() or False
        date_to = (data.get("dateTo") or "").strip() or False
        group_size = (data.get("groupSize") or "").strip() or False
        interest_key = (data.get("interest") or "").strip()
        interest = INTEREST_MAP.get(interest_key, interest_key) or False
        message = (data.get("message") or "").strip()[:2000] or False
        lang = (data.get("lang") or "en").strip()[:5]
        source_type = (data.get("source") or "contact-form").strip()

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

        lines.append(f"\nLanguage: {lang} | Source: {source_type}")

        description = "\n".join(lines)

        try:
            lead_vals = {
                "name": f"HelloJapan.jp — {name}",
                "contact_name": name,
                "email_from": email,
                "phone": phone,
                "description": description,
                "type": "lead",
                "source_id": False,
                "medium_id": False,
            }

            # Try to find/create UTM source & medium
            env = request.env
            sudo_env = env(su=True)

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

            return _json_response({"ok": True, "id": lead.id}, 200, origin)

        except Exception:
            _logger.exception("Failed to create lead from HelloJapan.jp")
            return _json_response({"error": "Internal error"}, 500, origin)

    @http.route(
        "/api/lead/email",
        type="http",
        auth="none",
        methods=["POST", "OPTIONS"],
        csrf=False,
        cors=False,
    )
    def submit_email(self, **kwargs):
        """Lightweight endpoint for exit-intent popup (email only)."""
        origin = request.httprequest.headers.get("Origin", "")

        if request.httprequest.method == "OPTIONS":
            return Response("", status=204, headers=_cors_headers(origin))

        ip = request.httprequest.headers.get(
            "X-Forwarded-For", request.httprequest.remote_addr or ""
        ).split(",")[0].strip()

        if not _check_rate_limit(ip):
            return _json_response({"error": "Too many requests"}, 429, origin)

        try:
            data = json.loads(request.httprequest.data or "{}")
        except (json.JSONDecodeError, TypeError):
            return _json_response({"error": "Invalid JSON"}, 400, origin)

        email = (data.get("email") or "").strip()[:200]
        lang = (data.get("lang") or "en").strip()[:5]

        if not _validate_email(email):
            return _json_response({"error": "Valid email required"}, 400, origin)

        try:
            sudo_env = request.env(su=True)

            source = sudo_env["utm.source"].search(
                [("name", "=", "hellojapan.jp")], limit=1
            )
            if not source:
                source = sudo_env["utm.source"].create({"name": "hellojapan.jp"})

            lead = sudo_env["crm.lead"].create({
                "name": f"HelloJapan.jp — Free itinerary request",
                "email_from": email,
                "description": f"Exit-popup email capture\nLanguage: {lang}",
                "type": "lead",
                "source_id": source.id,
            })

            _logger.info(
                "HelloJapan exit-popup lead: id=%s email=%s", lead.id, email
            )
            return _json_response({"ok": True}, 200, origin)

        except Exception:
            _logger.exception("Failed to create email lead from HelloJapan.jp")
            return _json_response({"error": "Internal error"}, 500, origin)
