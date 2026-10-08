"""Orders: server-priced checkout, tracking, admin management."""
import secrets

from flask import Blueprint, request
from sqlalchemy import or_

from database.db import db
from models import Order, Customer
from services import order_service
from services.order_service import OrderError
from services.product_service import paginate
from utils import ok, fail, admin_required, is_admin, current_customer, clean

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


def can_view(order, token=None):
    """Admin, the owning logged-in customer, or anyone holding the order's secret token."""
    if is_admin():
        return True
    customer = current_customer()
    if customer and order.customer_id == customer.id:
        return True
    return bool(token and order.access_token and secrets.compare_digest(str(token), order.access_token))


def find_order(ident):
    if str(ident).isdigit():
        return db.session.get(Order, int(ident))
    return Order.query.filter_by(order_number=str(ident)).first()


# ---------------- PUBLIC ----------------

@orders_bp.post("/quote")
def quote_cart():
    """Cart/checkout summary priced by the server."""
    data = request.get_json(silent=True) or {}
    try:
        return ok(order_service.quote(data.get("items"), data.get("order_type") or "delivery"))
    except OrderError as e:
        return fail(str(e))


@orders_bp.post("")
def create_order():
    """Checkout. Accepts product IDs + quantities only; all money is computed server-side."""
    data = request.get_json(silent=True) or {}
    try:
        order = order_service.create_order(data, customer=current_customer())
    except OrderError as e:
        return fail(str(e))
    out = order.to_dict()
    out["access_token"] = order.access_token
    return ok(out, message="Order placed successfully.")


@orders_bp.post("/track")
def track_order():
    """Guest tracking: order number + (token or the phone used at checkout)."""
    data = request.get_json(silent=True) or {}
    order = Order.query.filter_by(order_number=clean(data.get("order_number"), 40).upper()).first()
    token = clean(data.get("token"), 64)
    phone = order_service.normalize_phone(data.get("phone"))
    if order and (can_view(order, token) or
                  (phone and order.shipping_phone and phone[-10:] == order.shipping_phone[-10:])):
        out = order.to_dict()
        out["access_token"] = order.access_token
        return ok(out)
    return fail("No order found with those details.", 404)


@orders_bp.get("/view/<ident>")
def view_order(ident):
    order = find_order(ident)
    if not order or not can_view(order, request.args.get("t")):
        return fail("Order not found", 404)
    return ok(order.to_dict(admin=is_admin()))


@orders_bp.post("/<ident>/cancel")
def cancel_order(ident):
    """Customer self-cancel while the order is still pending."""
    data = request.get_json(silent=True) or {}
    order = find_order(ident)
    if not order or not can_view(order, data.get("token") or request.args.get("t")):
        return fail("Order not found", 404)
    if order.status_key != "pending":
        return fail("This order is already being processed. Please contact the store to cancel it.")
    try:
        order_service.set_status(order, "cancelled", "Cancelled by customer")
    except OrderError as e:
        return fail(str(e))
    return ok(order.to_dict(), message="Order cancelled")


# ---------------- ADMIN ----------------

@orders_bp.get("")
@admin_required
def list_orders():
    q = Order.query.outerjoin(Customer)
    status = request.args.get("status")
    if status:
        q = q.filter(Order.status == status)
    pay = request.args.get("payment_status")
    if pay:
        q = q.filter(Order.payment_status == pay)
    term = clean(request.args.get("q"), 80)
    if term:
        like = f"%{term}%"
        q = q.filter(or_(Order.order_number.ilike(like), Order.shipping_name.ilike(like),
                         Order.shipping_phone.ilike(like), Customer.name.ilike(like)))
    q = q.order_by(Order.created_at.desc())
    items, meta = paginate(q, request.args.get("page", 1), request.args.get("limit", 50))
    return ok([o.to_dict(admin=True) for o in items], meta=meta)


@orders_bp.get("/<int:oid>")
@admin_required
def get_order(oid):
    order = db.session.get(Order, oid)
    if not order:
        return fail("Order not found", 404)
    return ok(order.to_dict(admin=True))


@orders_bp.put("/<int:oid>")
@admin_required
def update_order(oid):
    order = db.session.get(Order, oid)
    if not order:
        return fail("Order not found", 404)
    data = request.get_json(silent=True) or {}
    try:
        if "admin_note" in data:
            order.admin_note = clean(data["admin_note"], 2000)
            db.session.commit()
        if data.get("payment_status"):
            order_service.set_payment_status(order, data["payment_status"])
        if data.get("status"):
            order_service.set_status(order, data["status"], data.get("status_note"))
    except OrderError as e:
        return fail(str(e))
    return ok(order.to_dict(admin=True), message="Order updated")
