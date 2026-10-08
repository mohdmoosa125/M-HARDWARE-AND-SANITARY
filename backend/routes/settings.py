"""
Settings
--------
Public GET returns only the "safe" keys (phone, address, etc).
PUT is admin-only and can change anything.
"""
from flask import Blueprint, request
from models import Setting
from utils import ok, admin_required

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")

# Default values used the first time the site runs
DEFAULTS = {
    "business_name": "M Hardware & Sanitary",
    "tagline": "Quality Hardware, Sanitary & Construction Products",
    "phone": "+919876543210",
    "whatsapp": "919876543210",
    "email": "info@mhardware.com",
    "address": "Main Road, Bhopal, Madhya Pradesh",
    "opening_hours": "Mon – Sat: 9:00 AM – 8:00 PM",
    "google_maps": "",
    "facebook": "#",
    "instagram": "#",
    "youtube": "#",
    "twitter": "#",
    "footer_text": "M Hardware & Sanitary is a trusted store providing quality hardware and sanitary products for homes and businesses.",
    "developer_name": "Moosa",
    "logo": "",
}


@settings_bp.get("")
def public_settings():
    """Return merged defaults + database values."""
    stored = Setting.all_as_dict()
    merged = {**DEFAULTS, **stored}
    # never expose internal keys publicly (none currently, but keep the habit)
    merged.pop("ai_api_key", None)
    return ok(merged)


@settings_bp.put("")
@admin_required
def update_settings():
    data = request.get_json(silent=True) or {}
    for key, value in data.items():
        Setting.set(key, value)
    stored = Setting.all_as_dict()
    return ok({**DEFAULTS, **stored}, message="Settings saved")