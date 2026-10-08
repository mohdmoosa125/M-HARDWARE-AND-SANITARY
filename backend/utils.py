"""
utils.py
--------
Small helper functions used all over the project:
  * slugify      -> turns "Floor Tiles" into "floor-tiles"
  * ok / fail    -> standard JSON responses
  * admin_required -> route protection decorator
"""
import re
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