"""Orders + order items."""
from flask import Blueprint, request
from database.db import db
from models import Order, OrderItem, Customer, Product
from utils import ok, fail, admin_required

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@orders_bp.post("")
def create_order():
    """Public endpoint — used by the checkout/cart page."""
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    if not items:
        return fail("Your cart is empty")

    # find or create the customer
    customer = _find_or_create_customer(data)

    order = Order(
        customer_id=customer.id,
        note=data.get("note", ""),
        status="new",
    )
    db.session.add(order)
    db.session.flush()   # gives us order.id

    total = 0
    for item in items:
        product = db.session.get(Product, int(item.get("product_id")))
        if not product:
            continue
        qty = int(item.get("quantity") or 1)
        price = product.final_price or 0
        total += price * qty
        db.session.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=qty,
            price=price,
        ))

    order.total = total
    db.session.commit()
    return ok(order.to_dict(), message="Order received. We will contact you shortly.")


def _find_or_create_customer(data):
    phone = (data.get("phone") or "").strip()
    customer = None
    if phone:
        customer = Customer.query.filter_by(phone=phone).first()
    if customer:
        return customer

    customer = Customer(
        name=(data.get("name") or "Guest").strip(),
        phone=phone,
        whatsapp=data.get("whatsapp") or phone,
        email=data.get("email"),
        address=data.get("address"),
    )
    db.session.add(customer)
    db.session.flush()
    return customer


@orders_bp.get("")
@admin_required
def list_orders():
    status = request.args.get("status")
    q = Order.query
    if status:
        q = q.filter_by(status=status)
    orders = q.order_by(Order.created_at.desc()).all()
    return ok([o.to_dict() for o in orders])


@orders_bp.get("/<int:oid>")
@admin_required
def get_order(oid):
    order = db.session.get(Order, oid)
    if not order:
        return fail("Order not found", 404)
    return ok(order.to_dict())


@orders_bp.put("/<int:oid>")
@admin_required
def update_order(oid):
    order = db.session.get(Order, oid)
    if not order:
        return fail("Order not found", 404)
    data = request.get_json(silent=True) or {}
    if "status" in data:
        order.status = data["status"]
    if "note" in data:
        order.note = data["note"]
    db.session.commit()
    return ok(order.to_dict(), message="Order updated")