"""Admin login / logout / who-am-I / change password."""
from flask import Blueprint, request, session
from database.db import db
from models import User
from utils import ok, fail, admin_required, too_many_attempts, record_failure, clear_failures

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

DEV_DEFAULT_PASSWORD = "admin123"      # only ever set by database/seed.py for local development


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return fail("Username and password are required")

    guard = f"admin:{request.remote_addr}"
    if too_many_attempts(guard):
        return fail("Too many failed attempts. Please wait 15 minutes and try again.", 429)

    user = User.query.filter(
        (User.username == username) | (User.email == username)
    ).first()

    if not user or not user.is_admin or not user.check_password(password):
        record_failure(guard)
        return fail("Invalid username or password", 401)

    clear_failures(guard)
    session["admin_id"] = user.id
    session["admin_name"] = user.username
    return ok(user.to_dict(), message="Logged in")


@auth_bp.post("/logout")
def logout():
    # only end the admin session (a customer login in the same browser stays)
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    return ok(message="Logged out")


@auth_bp.get("/me")
def me():
    if not session.get("admin_id"):
        return fail("Not logged in", 401)
    user = db.session.get(User, session["admin_id"])
    if not user:
        return fail("Not logged in", 401)
    data = user.to_dict()
    data["default_password"] = user.check_password(DEV_DEFAULT_PASSWORD)
    return ok(data)


@auth_bp.post("/password")
@admin_required
def change_password():
    data = request.get_json(silent=True) or {}
    user = db.session.get(User, session["admin_id"])
    if not user or not user.check_password(data.get("current_password") or ""):
        return fail("Current password is incorrect", 400)
    new = data.get("new_password") or ""
    if len(new) < 8 or new == DEV_DEFAULT_PASSWORD:
        return fail("Choose a new password with at least 8 characters")
    user.set_password(new)
    db.session.commit()
    return ok(message="Password changed")
