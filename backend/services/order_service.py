"""
order_service.py
----------------
Server-side pricing, stock reservation and order lifecycle.

The browser only ever sends product IDs + quantities. Every price, discount,
tax, delivery charge and total is recalculated here from the database, so a
modified request can never change what the customer is charged.
"""
import re
import secrets
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from database.db import db
from models import Customer, Order, OrderItem, OrderStatusHistory, Product
from models.order import ORDER_STATUSES, PAYMENT_STATUSES, STATUS_LABELS
from services import store_config
from utils import clean, to_int

MAX_LINES = 100
MAX_QTY = 10000
CENT = Decimal("0.01")


class OrderError(Exception):
    """A problem the customer/admin can fix (shown to them as-is)."""


def _d(value):
    return Decimal(str(value or 0))


def _money(value):
    return float(_d(value).quantize(CENT, rounding=ROUND_HALF_UP))


# ----------------------------------------------------------------- items

def normalize_items(raw_items):
    """[{product_id, quantity}, ...] -> {product_id: qty}, merging duplicates."""
    if not isinstance(raw_items, list) or not raw_items:
        raise OrderError("Your cart is empty")
    if len(raw_items) > MAX_LINES:
        raise OrderError(f"Too many different items (max {MAX_LINES})")
    merged = {}
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise OrderError("Invalid cart item")
        pid = to_int(raw.get("product_id"))
        qty = to_int(raw.get("quantity"))
        if not pid or pid < 1:
            raise OrderError("Invalid product in cart")
        if qty is None or qty < 1:
            raise OrderError("Quantity must be at least 1")
        merged[pid] = merged.get(pid, 0) + qty
        if merged[pid] > MAX_QTY:
            raise OrderError(f"Quantity is too large (max {MAX_QTY})")
    return merged


# ----------------------------------------------------------------- pricing

def delivery_options(settings):
    opts = []
    if store_config.flag(settings, "delivery_enabled"):
        opts.append("delivery")
    if store_config.flag(settings, "pickup_enabled"):
        opts.append("pickup")
    return opts


def payment_options(settings):
    """Only methods that can really be honoured. There is no online gateway yet,
    so 'online' is never offered (see services/payment_service.py)."""
    from services import payment_service
    opts = []
    if store_config.flag(settings, "payment_cod_enabled"):
        opts.append("cod")
    if (settings.get("upi_id") or "").strip():
        opts.append("upi")
    if payment_service.gateway_configured():
        opts.append("online")
    return opts


def quote(raw_items, order_type="delivery", settings=None):
    """Price a cart from the database. Never trusts client prices.
    Returns a dict; `problems` lists anything that would block checkout."""
    settings = settings or store_config.all_settings()
    wanted = normalize_items(raw_items)
    products = {p.id: p for p in Product.query.filter(Product.id.in_(list(wanted))).all()}

    lines, problems = [], []
    subtotal = discount = taxable = Decimal(0)
    for pid, qty in wanted.items():
        p = products.get(pid)
        if not p:
            problems.append({"product_id": pid, "message": "This product is no longer available."})
            continue
        mrp = _d(p.price)
        price = _d(p.final_price)
        if price <= 0:
            problems.append({"product_id": pid, "message": f"{p.name} has no price yet. Please contact the store."})
        if not p.availability or (p.stock or 0) <= 0:
            problems.append({"product_id": pid, "message": f"{p.name} is out of stock."})
        elif qty > (p.stock or 0):
            problems.append({"product_id": pid,
                             "message": f"Only {p.stock} {p.unit or 'piece'}(s) of {p.name} available."})
        line_mrp = mrp * qty
        line_total = price * qty
        subtotal += line_mrp
        discount += max(Decimal(0), line_mrp - line_total)
        taxable += line_total
        lines.append({
            "product_id": p.id, "name": p.name, "slug": p.slug, "sku": p.sku,
            "unit": p.unit or "piece", "image": p.image, "quantity": qty,
            "stock": p.stock or 0, "in_stock": p.in_stock,
            "mrp": _money(mrp), "price": _money(price),
            "discount": _money(max(Decimal(0), line_mrp - line_total)),
            "subtotal": _money(line_total),
        })

    order_type = order_type if order_type in ("delivery", "pickup") else "delivery"
    delivery_fee = Decimal(0)
    if order_type == "delivery":
        fee = _d(store_config.number(settings, "delivery_fee"))
        free_above = _d(store_config.number(settings, "free_delivery_above"))
        delivery_fee = Decimal(0) if (free_above > 0 and taxable >= free_above) else fee

    tax = Decimal(0)
    tax_inclusive = store_config.flag(settings, "tax_inclusive")
    if store_config.flag(settings, "tax_enabled"):
        rate = _d(store_config.number(settings, "tax_rate"))
        tax = taxable * rate / (Decimal(100) + rate) if tax_inclusive else taxable * rate / Decimal(100)
    grand = taxable + delivery_fee + (Decimal(0) if tax_inclusive else tax)

    return {
        "lines": lines,
        "problems": problems,
        "ok": not problems and bool(lines),
        "order_type": order_type,
        "subtotal": _money(subtotal),
        "discount": _money(discount),
        "tax": _money(tax),
        "tax_label": settings.get("tax_label") or "Tax",
        "tax_enabled": store_config.flag(settings, "tax_enabled"),
        "tax_inclusive": tax_inclusive,
        "delivery_fee": _money(delivery_fee),
        "grand_total": _money(grand),
        "item_count": sum(l["quantity"] for l in lines),
        "delivery_options": delivery_options(settings),
        "payment_options": payment_options(settings),
    }


# ----------------------------------------------------------------- numbering

def next_number(column, prefix):
    """Next PREFIX-000001 style number. Uniqueness is enforced by a DB constraint;
    create_order() retries on a clash."""
    last = (db.session.query(column).filter(column.like(f"{prefix}-%"))
            .order_by(column.desc()).first())
    seq = 0
    if last and last[0]:
        tail = last[0].rsplit("-", 1)[-1]
        seq = int(tail) if tail.isdigit() else 0
    return f"{prefix}-{seq + 1:06d}"


# ----------------------------------------------------------------- validation

PHONE_RE = re.compile(r"^\+?\d{10,13}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PIN_RE = re.compile(r"^\d{6}$")


def normalize_phone(value):
    return re.sub(r"[\s\-()]", "", clean(value, 30))


def validate_checkout(data, settings):
    order_type = clean(data.get("order_type"), 20) or "delivery"
    if order_type not in delivery_options(settings):
        raise OrderError("This delivery option is not available.")
    method = clean(data.get("payment_method"), 20) or "cod"
    if method not in payment_options(settings):
        raise OrderError("This payment option is not available yet. Please choose Cash on Delivery / Pay at Store.")

    ship = {
        "name": clean(data.get("name"), 150),
        "phone": normalize_phone(data.get("phone")),
        "email": clean(data.get("email"), 150).lower(),
        "address": clean(data.get("address"), 1000),
        "city": clean(data.get("city"), 80),
        "state": clean(data.get("state"), 80),
        "pincode": clean(data.get("pincode"), 12),
    }
    if len(ship["name"]) < 2:
        raise OrderError("Please enter your full name.")
    if not PHONE_RE.match(ship["phone"]):
        raise OrderError("Please enter a valid 10-digit mobile number.")
    if ship["email"] and not EMAIL_RE.match(ship["email"]):
        raise OrderError("Please enter a valid email address.")
    if order_type == "delivery":
        if len(ship["address"]) < 5:
            raise OrderError("Please enter your delivery address.")
        if not ship["city"]:
            raise OrderError("Please enter your city.")
        if not PIN_RE.match(ship["pincode"]):
            raise OrderError("Please enter a valid 6-digit PIN code.")
    return order_type, method, ship


def _guest_customer(ship):
    """Reuse a guest record with the same phone; never attach to a registered account."""
    customer = (Customer.query.filter_by(phone=ship["phone"])
                .filter(Customer.password_hash.is_(None)).first())
    if customer:
        customer.name = ship["name"] or customer.name
        customer.email = ship["email"] or customer.email
        return customer
    customer = Customer(name=ship["name"], phone=ship["phone"], whatsapp=ship["phone"],
                        email=ship["email"] or None,
                        address=", ".join(x for x in (ship["address"], ship["city"], ship["pincode"]) if x))
    db.session.add(customer)
    db.session.flush()
    return customer


# ----------------------------------------------------------------- create

def create_order(data, customer=None):
    """Validate, price, reserve stock and save an order + its invoice atomically."""
    from services import invoice_service

    settings = store_config.all_settings()
    order_type, method, ship = validate_checkout(data, settings)
    q = quote(data.get("items"), order_type, settings)
    if q["problems"]:
        raise OrderError(q["problems"][0]["message"])
    if not q["lines"]:
        raise OrderError("Your cart is empty")

    year = datetime.utcnow().year
    order_prefix = f"{clean(settings.get('order_prefix'), 10) or 'ORD'}-{year}"

    for attempt in range(3):
        try:
            # reserve stock: one atomic conditional UPDATE per line
            for line in q["lines"]:
                res = db.session.execute(
                    update(Product)
                    .where(Product.id == line["product_id"],
                           Product.stock >= line["quantity"],
                           Product.availability.is_(True))
                    .values(stock=Product.stock - line["quantity"])
                    .execution_options(synchronize_session=False)
                )
                if res.rowcount != 1:
                    raise OrderError(f"Sorry, {line['name']} just went out of stock for that quantity.")

            buyer = customer or _guest_customer(ship)
            order = Order(
                order_number=next_number(Order.order_number, order_prefix),
                access_token=secrets.token_urlsafe(24),
                customer_id=buyer.id,
                status="pending",
                order_type=order_type,
                payment_method=method,
                payment_status="pending",
                note=clean(data.get("note"), 1000),
                subtotal=q["subtotal"], discount=q["discount"], tax=q["tax"],
                delivery_fee=q["delivery_fee"], grand_total=q["grand_total"], total=q["grand_total"],
                shipping_name=ship["name"], shipping_phone=ship["phone"],
                shipping_email=ship["email"] or None,
                shipping_address=ship["address"] or None, shipping_city=ship["city"] or None,
                shipping_state=ship["state"] or None, shipping_pincode=ship["pincode"] or None,
            )
            db.session.add(order)
            db.session.flush()
            for line in q["lines"]:
                db.session.add(OrderItem(
                    order_id=order.id, product_id=line["product_id"],
                    product_name=line["name"], sku=line["sku"], unit=line["unit"],
                    image=line["image"], quantity=line["quantity"], mrp=line["mrp"],
                    price=line["price"], discount=line["discount"], subtotal=line["subtotal"],
                ))
            db.session.add(OrderStatusHistory(order_id=order.id, status="pending", note="Order placed"))
            invoice_service.create_invoice(order, settings, year)
            db.session.commit()
            return order
        except IntegrityError:
            db.session.rollback()          # number clash with a concurrent order -> retry
            if attempt == 2:
                raise OrderError("Order could not be created. Please try again.")
        except Exception:
            db.session.rollback()
            raise


# ----------------------------------------------------------------- lifecycle

def _restock(order):
    for item in order.items:
        if item.product_id and item.quantity:
            db.session.execute(
                update(Product).where(Product.id == item.product_id)
                .values(stock=Product.stock + item.quantity)
                .execution_options(synchronize_session=False)
            )


def set_status(order, status, note=None):
    status = clean(status, 40)
    if status not in ORDER_STATUSES:
        raise OrderError("Unknown order status")
    current = order.status_key
    if status == current:
        return order
    if current == "cancelled":
        raise OrderError("A cancelled order cannot be reopened.")
    if status == "ready_for_pickup" and order.order_type != "pickup":
        raise OrderError("'Ready for Pickup' is only for store-pickup orders.")
    if status == "out_for_delivery" and order.order_type == "pickup":
        raise OrderError("'Out for Delivery' is only for home-delivery orders.")
    if status == "cancelled":
        _restock(order)
    order.status = status
    db.session.add(OrderStatusHistory(order_id=order.id, status=status,
                                      note=clean(note, 255) or STATUS_LABELS.get(status)))
    db.session.commit()
    return order


def set_payment_status(order, payment_status):
    payment_status = clean(payment_status, 20)
    if payment_status not in PAYMENT_STATUSES:
        raise OrderError("Unknown payment status")
    order.payment_status = payment_status
    db.session.commit()
    return order
