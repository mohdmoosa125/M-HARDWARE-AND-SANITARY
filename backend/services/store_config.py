"""
store_config.py
---------------
Single source of business configuration (name, contact, tax, delivery,
invoice, payment). Values live in the `settings` table and are edited from
Admin -> Settings; DEFAULTS fills anything not saved yet.

The contact defaults are DEMO placeholders (demo_mode = "1" shows a notice
on the site and on invoices until the owner enters real details).
"""
from models import Setting

DEFAULTS = {
    # ---- business ----
    "business_name": "M Hardware & Sanitary",
    "tagline": "Quality Hardware, Sanitary & Construction Products",
    "phone": "+919876543210",
    "whatsapp": "919876543210",
    "email": "info@mhardware.com",
    "address": "Main Road, Bhopal, Madhya Pradesh",
    "city": "Bhopal",
    "state": "Madhya Pradesh",
    "opening_hours": "Mon – Sat: 9:00 AM – 8:00 PM",
    "google_maps": "",
    "footer_text": "Quality hardware and sanitary products for homes, businesses and construction projects.",
    "developer_name": "Moosa",
    "logo": "",
    "demo_mode": "1",            # "1" = contact details above are placeholders
    # ---- social (empty = hidden) ----
    "facebook": "",
    "instagram": "",
    "youtube": "",
    "twitter": "",
    # ---- money ----
    "currency": "INR",
    "currency_symbol": "₹",
    # ---- tax ----
    "tax_enabled": "0",
    "tax_label": "GST",
    "tax_rate": "18",
    "tax_inclusive": "1",        # "1" = prices already include tax
    "gstin": "",
    # ---- delivery ----
    "delivery_enabled": "1",
    "pickup_enabled": "1",
    "delivery_fee": "0",
    "free_delivery_above": "0",  # 0 = no free-delivery threshold
    "delivery_note": "Delivery available in Bhopal. Charges, if any, are confirmed before dispatch.",
    # ---- payment ----
    "payment_cod_enabled": "1",
    "upi_id": "",                # shown to customers for manual UPI payment when set
    # ---- invoice / orders ----
    "invoice_prefix": "MHS",
    "order_prefix": "ORD",
    "invoice_footer": "Thank you for shopping with M Hardware & Sanitary.",
    "invoice_terms": "Goods once sold will be exchanged only as per store policy.",
    # ---- AI ----
    "ai_assistant_enabled": "1",
}

# Never sent to the public /api/settings endpoint.
PRIVATE_KEYS = {"ai_api_key"}


def all_settings():
    stored = Setting.all_as_dict()
    merged = {**DEFAULTS, **{k: v for k, v in stored.items() if v is not None}}
    for legacy_social in ("facebook", "instagram", "youtube", "twitter"):
        if merged.get(legacy_social) == "#":       # old placeholder links -> hidden
            merged[legacy_social] = ""
    return merged


def public_settings():
    return {k: v for k, v in all_settings().items() if k not in PRIVATE_KEYS}


def flag(settings, key):
    return str(settings.get(key, "")).strip().lower() in ("1", "true", "yes", "on")


def number(settings, key, default=0.0):
    try:
        return max(0.0, float(settings.get(key) or default))
    except (TypeError, ValueError):
        return default


def business_snapshot(settings=None):
    """Business block printed on invoices (frozen into each invoice)."""
    s = settings or all_settings()
    return {
        "name": s.get("business_name", ""),
        "address": s.get("address", ""),
        "phone": s.get("phone", ""),
        "email": s.get("email", ""),
        "gstin": s.get("gstin", ""),
        "footer": s.get("invoice_footer", ""),
        "terms": s.get("invoice_terms", ""),
        "currency_symbol": s.get("currency_symbol", "₹"),
        "demo": flag(s, "demo_mode"),
    }
