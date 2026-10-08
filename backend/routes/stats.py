"""Dashboard statistics + analytics for the admin panel (real data only)."""
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, request
from sqlalchemy import func, or_

from database.db import db
from models import (Product, Category, Order, OrderItem, Customer, Inquiry, ContactMessage, Invoice)
from utils import ok, admin_required

stats_bp = Blueprint("stats", __name__, url_prefix="/api/admin")

IST = timedelta(hours=5, minutes=30)          # the store's business day is Indian time


def _ist_day(dt):
    return (dt + IST).date()


def _low_stock_q():
    return Product.query.filter(Product.availability.is_(True), Product.stock > 0,
                                Product.stock <= func.coalesce(Product.min_stock, 5))


def _out_of_stock_q():
    return Product.query.filter(or_(Product.availability.is_(False), Product.stock <= 0))


@stats_bp.get("/stats")
@admin_required
def dashboard_stats():
    days = min(90, max(7, request.args.get("days", 30, type=int)))
    now = datetime.utcnow()
    today = _ist_day(now)
    since = now - timedelta(days=days)

    live = Order.query.filter(Order.status != "cancelled")
    recent = live.filter(Order.created_at >= since).all()

    sales_by_day = defaultdict(float)
    orders_by_day = defaultdict(int)
    for o in recent:
        d = _ist_day(o.created_at)
        sales_by_day[d] += o.grand_total or o.total or 0
        orders_by_day[d] += 1
    series = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        series.append({"date": d.isoformat(), "sales": round(sales_by_day[d], 2), "orders": orders_by_day[d]})

    status_counts = dict(db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all())

    top = (db.session.query(OrderItem.product_name, func.sum(OrderItem.quantity),
                            func.sum(func.coalesce(OrderItem.subtotal, OrderItem.price * OrderItem.quantity)))
           .join(Order).filter(Order.status != "cancelled")
           .group_by(OrderItem.product_name)
           .order_by(func.sum(OrderItem.quantity).desc()).limit(5).all())

    # revenue per top-level category
    cats = {c.id: c for c in Category.query.all()}
    cat_rev = defaultdict(float)
    rows = (db.session.query(Product.category_id,
                             func.sum(func.coalesce(OrderItem.subtotal, OrderItem.price * OrderItem.quantity)))
            .join(OrderItem, OrderItem.product_id == Product.id).join(Order)
            .filter(Order.status != "cancelled").group_by(Product.category_id).all())
    for cid, amount in rows:
        c = cats.get(cid)
        root = (c.parent or c) if c else None
        cat_rev[root.name if root else "Uncategorised"] += amount or 0

    revenue = db.session.query(func.coalesce(func.sum(Order.grand_total), 0)).filter(Order.status != "cancelled").scalar()
    customers_with_orders = db.session.query(func.count(func.distinct(Order.customer_id))).scalar()

    return ok({
        # headline numbers
        "total_products": Product.query.count(),
        "total_categories": Category.query.count(),
        "total_orders": Order.query.count(),
        "pending_orders": status_counts.get("pending", 0),
        "today_sales": round(sales_by_day[today], 2),
        "today_orders": orders_by_day[today],
        "total_revenue": round(revenue or 0, 2),
        "total_customers": Customer.query.filter(or_(Customer.password_hash.isnot(None),
                                                     Customer.orders.any())).count(),
        "registered_customers": Customer.query.filter(Customer.password_hash.isnot(None)).count(),
        "customers_with_orders": customers_with_orders,
        "total_invoices": Invoice.query.count(),
        "total_inquiries": Inquiry.query.count(),
        "total_messages": ContactMessage.query.count(),
        "low_stock_count": _low_stock_q().count(),
        "out_of_stock_count": _out_of_stock_q().count(),
        "products_without_images": Product.query.filter(or_(
            Product.image.is_(None), Product.image == "",
            Product.image_status.in_(("missing", "failed")))).count(),
        "fallback_images": Product.query.filter(Product.image_status == "fallback").count(),
        # charts
        "series": series,
        "orders_by_status": status_counts,
        "top_products": [{"name": n, "quantity": int(q or 0), "revenue": round(r or 0, 2)} for n, q, r in top],
        "category_sales": sorted(({"name": k, "revenue": round(v, 2)} for k, v in cat_rev.items()),
                                 key=lambda x: -x["revenue"]),
        # lists
        "low_stock": [p.to_dict() for p in _low_stock_q().order_by(Product.stock).limit(10).all()],
        "featured": [p.to_dict() for p in Product.query.filter_by(featured=True).limit(10).all()],
        "recent_orders": [o.to_dict(admin=True) for o in
                          Order.query.order_by(Order.created_at.desc()).limit(6).all()],
        "recent_inquiries": [i.to_dict() for i in
                             Inquiry.query.order_by(Inquiry.created_at.desc()).limit(5).all()],
    })
