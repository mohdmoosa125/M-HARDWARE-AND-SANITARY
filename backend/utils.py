"""
utils.py
--------
Small helper functions used all over the project:
  * slugify      -> turns "Floor Tiles" into "floor-tiles"
  * ok / fail    -> standard JSON responses
  * admin_required -> route protection decorator
"""
import re
import time
import functools
import unicodedata
from flask import session, jsonify


def slugify(text):
    """Create a URL-safe slug from any text."""
    text = unicodedata.normalize("NFKD", str(text))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def ok(data=None, **extra):
    """Standard success response."""
    payload = {"success": True, "data": data}
    payload.update(extra)
    return jsonify(payload)


def fail(message, code=400):
    """Standard error response."""
    return jsonify({"success": False, "message": message}), code


def admin_required(fn):
    """Protect a route so only logged-in admins can use it."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return fail("Admin authentication required", 401)
        return fn(*args, **kwargs)
    return wrapper


def is_admin():
    return bool(session.get("admin_id"))


def current_customer():
    """The logged-in, active customer account (or None)."""
    cid = session.get("customer_id")
    if not cid:
        return None
    from database.db import db
    from models import Customer
    customer = db.session.get(Customer, cid)
    if not customer or customer.is_active is False or not customer.is_registered:
        session.pop("customer_id", None)
        return None
    return customer


def customer_required(fn):
    """Protect a route so only a logged-in customer can use it. Passes `customer`."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        customer = current_customer()
        if not customer:
            return fail("Please log in to continue", 401)
        return fn(customer, *args, **kwargs)
    return wrapper


_FAILS = {}


def too_many_attempts(key, limit=5, window=900):
    """Simple in-memory brute-force guard (per process). True = block."""
    now = time.time()
    hits = [t for t in _FAILS.get(key, []) if now - t < window]
    _FAILS[key] = hits
    return len(hits) >= limit


def record_failure(key):
    _FAILS.setdefault(key, []).append(time.time())


def clear_failures(key):
    _FAILS.pop(key, None)


def to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clean(value, max_len=255):
    """Trimmed string, capped in length ('' for None)."""
    return ("" if value is None else str(value)).strip()[:max_len]