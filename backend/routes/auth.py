"""Admin login / logout / who-am-I."""
from flask import Blueprint, request, session
from database.db import db
from models import User
from utils import ok, fail

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return fail("Username and password are required")

    user = User.query.filter(
        (User.username == username) | (User.email == username)
    ).first()

    if not user or not user.check_password(password):
        return fail("Invalid username or password", 401)

    session["admin_id"] = user.id
    session["admin_name"] = user.username
    return ok(user.to_dict(), message="Logged in")


@auth_bp.post("/logout")
def logout():
    session.clear()
    return ok(message="Logged out")


@auth_bp.get("/me")
def me():
    if not session.get("admin_id"):
        return fail("Not logged in", 401)
    user = db.session.get(User, session["admin_id"])
    if not user:
        return fail("Not logged in", 401)
    return ok(user.to_dict())