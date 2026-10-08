"""Customer accounts: register/login, profile, orders, addresses, wishlist, password reset."""
import hashlib
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, request, session
from sqlalchemy import func, or_

from database.db import db
from models import Address, Customer, Order, Product, WishlistItem
from services.order_service import EMAIL_RE, PHONE_RE, normalize_phone
from utils import (ok, fail, customer_required, current_customer, clean, to_int,
                   too_many_attempts, record_failure, clear_failures)

account_bp = Blueprint("account", __name__, url_prefix="/api/account")

RESET_HOURS = 24


def _hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _registered(**filters):
    return Customer.query.filter_by(**filters).filter(Customer.password_hash.isnot(None))


def _validate_profile(data, customer=None):
    name = clean(data.get("name"), 150)
    phone = normalize_phone(data.get("phone"))
    email = clean(data.get("email"), 150).lower()
    if len(name) < 2:
        return None, "Please enter your full name."
    if not PHONE_RE.match(phone):
        return None, "Please enter a valid 10-digit mobile number."
    if email and not EMAIL_RE.match(email):
        return None, "Please enter a valid email address."
    me = customer.id if customer else -1
    if _registered(phone=phone).filter(Customer.id != me).first():
        return None, "An account with this mobile number already exists. Please log in."
    if email and _registered().filter(func.lower(Customer.email) == email, Customer.id != me).first():
        return None, "An account with this email already exists. Please log in."
    return {"name": name, "phone": phone, "email": email or None}, None


# ---------------- auth ----------------

@account_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    fields, error = _validate_profile(data)
    if error:
        return fail(error)
    password = data.get("password") or ""
    if len(password) < 8:
        return fail("Password must be at least 8 characters.")
    customer = Customer(name=fields["name"], phone=fields["phone"], whatsapp=fields["phone"],
                        email=fields["email"], is_active=True)
    customer.set_password(password)
    customer.last_login_at = datetime.utcnow()
    db.session.add(customer)
    db.session.commit()
    session["customer_id"] = customer.id
    return ok(customer.to_dict(), message="Account created. Welcome!")


@account_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    login_id = clean(data.get("login"), 150).lower()
    password = data.get("password") or ""
    if not login_id or not password:
        return fail("Enter your mobile number or email and password.")
    guard = f"customer:{request.remote_addr}:{login_id}"
    if too_many_attempts(guard):
        return fail("Too many failed attempts. Please wait 15 minutes and try again.", 429)

    phone = normalize_phone(login_id)
    customer = _registered().filter(or_(func.lower(Customer.email) == login_id,
                                        Customer.phone == phone)).first()
    if not customer or not customer.check_password(password):
        record_failure(guard)
        return fail("Incorrect login details.", 401)
    if customer.is_active is False:
        return fail("This account is disabled. Please contact the store.", 403)
    clear_failures(guard)
    customer.last_login_at = datetime.utcnow()
    db.session.commit()
    session["customer_id"] = customer.id
    return ok(customer.to_dict(), message="Logged in")


@account_bp.post("/logout")
def logout():
    session.pop("customer_id", None)
    return ok(message="Logged out")


@account_bp.get("/me")
def me():
    customer = current_customer()
    return ok(customer.to_dict() if customer else None)


@account_bp.put("/profile")
@customer_required
def update_profile(customer):
    data = request.get_json(silent=True) or {}
    fields, error = _validate_profile(data, customer)
    if error:
        return fail(error)
    customer.name, customer.phone, customer.email = fields["name"], fields["phone"], fields["email"]
    db.session.commit()
    return ok(customer.to_dict(), message="Profile updated")


@account_bp.post("/password")
@customer_required
def change_password(customer):
    data = request.get_json(silent=True) or {}
    if not customer.check_password(data.get("current_password") or ""):
        return fail("Current password is incorrect.")
    new = data.get("new_password") or ""
    if len(new) < 8:
        return fail("New password must be at least 8 characters.")
    customer.set_password(new)
    db.session.commit()
    return ok(message="Password changed")


@account_bp.post("/forgot")
def forgot_password():
    # No email/SMS service is configured, so the store sends reset links manually
    # (Admin -> Customers -> Reset link). Same answer whether or not the account exists.
    return ok(message=("Password reset by email is not set up yet. Please contact the store "
                       "by phone or WhatsApp and we will send you a secure reset link."))


@account_bp.post("/reset")
def reset_password():
    data = request.get_json(silent=True) or {}
    token = clean(data.get("token"), 128)
    password = data.get("password") or ""
    if len(password) < 8:
        return fail("Password must be at least 8 characters.")
    customer = Customer.query.filter_by(reset_token_hash=_hash_token(token)).first() if token else None
    if not customer or not customer.reset_expires_at or customer.reset_expires_at < datetime.utcnow():
        return fail("This reset link is invalid or has expired.")
    customer.set_password(password)
    customer.reset_token_hash = None
    customer.reset_expires_at = None
    db.session.commit()
    session["customer_id"] = customer.id
    return ok(customer.to_dict(), message="Password updated. You are now logged in.")


def issue_reset_token(customer):
    """Used by the admin customers page. Returns the raw token (stored hashed)."""
    token = secrets.token_urlsafe(32)
    customer.reset_token_hash = _hash_token(token)
    customer.reset_expires_at = datetime.utcnow() + timedelta(hours=RESET_HOURS)
    db.session.commit()
    return token


# ---------------- orders ----------------

@account_bp.get("/orders")
@customer_required
def my_orders(customer):
    orders = Order.query.filter_by(customer_id=customer.id).order_by(Order.created_at.desc()).all()
    out = []
    for o in orders:
        d = o.to_dict()
        d.pop("history", None)
        d["access_token"] = o.access_token
        out.append(d)
    return ok(out)


# ---------------- addresses ----------------

def _address_fields(data):
    f = {
        "label": clean(data.get("label"), 40) or "Home",
        "name": clean(data.get("name"), 150),
        "phone": normalize_phone(data.get("phone")),
        "address": clean(data.get("address"), 1000),
        "city": clean(data.get("city"), 80),
        "state": clean(data.get("state"), 80),
        "pincode": clean(data.get("pincode"), 12),
    }
    if len(f["address"]) < 5 or not f["city"]:
        return None, "Please enter the full address and city."
    if f["pincode"] and not (f["pincode"].isdigit() and len(f["pincode"]) == 6):
        return None, "Please enter a valid 6-digit PIN code."
    if f["phone"] and not PHONE_RE.match(f["phone"]):
        return None, "Please enter a valid mobile number."
    return f, None


@account_bp.get("/addresses")
@customer_required
def list_addresses(customer):
    rows = Address.query.filter_by(customer_id=customer.id).order_by(Address.is_default.desc(), Address.id).all()
    return ok([a.to_dict() for a in rows])


@account_bp.post("/addresses")
@customer_required
def add_address(customer):
    data = request.get_json(silent=True) or {}
    fields, error = _address_fields(data)
    if error:
        return fail(error)
    if Address.query.filter_by(customer_id=customer.id).count() >= 10:
        return fail("You can save up to 10 addresses.")
    addr = Address(customer_id=customer.id, **fields)
    first = not Address.query.filter_by(customer_id=customer.id).first()
    if data.get("is_default") or first:
        Address.query.filter_by(customer_id=customer.id).update({"is_default": False})
        addr.is_default = True
    db.session.add(addr)
    db.session.commit()
    return ok(addr.to_dict(), message="Address saved")


@account_bp.put("/addresses/<int:aid>")
@customer_required
def update_address(customer, aid):
    addr = Address.query.filter_by(id=aid, customer_id=customer.id).first()
    if not addr:
        return fail("Address not found", 404)
    data = request.get_json(silent=True) or {}
    fields, error = _address_fields(data)
    if error:
        return fail(error)
    for k, v in fields.items():
        setattr(addr, k, v)
    if data.get("is_default"):
        Address.query.filter_by(customer_id=customer.id).update({"is_default": False})
        addr.is_default = True
    db.session.commit()
    return ok(addr.to_dict(), message="Address updated")


@account_bp.delete("/addresses/<int:aid>")
@customer_required
def delete_address(customer, aid):
    addr = Address.query.filter_by(id=aid, customer_id=customer.id).first()
    if not addr:
        return fail("Address not found", 404)
    db.session.delete(addr)
    db.session.commit()
    return ok(message="Address removed")


# ---------------- wishlist ----------------

@account_bp.get("/wishlist")
@customer_required
def get_wishlist(customer):
    rows = WishlistItem.query.filter_by(customer_id=customer.id).order_by(WishlistItem.created_at.desc()).all()
    return ok([r.product.to_dict() for r in rows if r.product])


@account_bp.post("/wishlist")
@customer_required
def add_wishlist(customer):
    pid = to_int((request.get_json(silent=True) or {}).get("product_id"))
    if not pid or not db.session.get(Product, pid):
        return fail("Product not found", 404)
    if not WishlistItem.query.filter_by(customer_id=customer.id, product_id=pid).first():
        db.session.add(WishlistItem(customer_id=customer.id, product_id=pid))
        db.session.commit()
    return ok({"product_id": pid}, message="Saved to wishlist")


@account_bp.delete("/wishlist/<int:pid>")
@customer_required
def remove_wishlist(customer, pid):
    WishlistItem.query.filter_by(customer_id=customer.id, product_id=pid).delete()
    db.session.commit()
    return ok({"product_id": pid}, message="Removed from wishlist")
