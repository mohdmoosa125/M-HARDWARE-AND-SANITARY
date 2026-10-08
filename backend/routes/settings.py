"""
Settings
--------
Public GET returns the business configuration (never private keys).
PUT is admin-only. Defaults live in services/store_config.py.
"""
from flask import Blueprint, request
from models import Setting
from services.store_config import DEFAULTS, PRIVATE_KEYS, public_settings, all_settings  # noqa: F401
from utils import ok, fail, admin_required

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")


@settings_bp.get("")
def get_public_settings():
    """Return merged defaults + database values."""
    return ok(public_settings())


@settings_bp.get("/admin")
@admin_required
def get_admin_settings():
    return ok(all_settings())


@settings_bp.put("")
@admin_required
def update_settings():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return fail("Invalid settings payload")
    for key, value in data.items():
        key = str(key).strip()
        if not key or len(key) > 80:
            continue
        if isinstance(value, bool):
            value = "1" if value else "0"
        value = "" if value is None else str(value)
        if len(value) > 5000:
            return fail(f"Value for {key} is too long")
        Setting.set(key, value)
    return ok(all_settings(), message="Settings saved")
