"""Admin-only management APIs: customers, inventory, brands, AI overview."""
from flask import Blueprint, request
from sqlalchemy import func, or_

from database.db import db
from models import AIConversation, AIMessage, Customer, Order, Product
from routes.account import issue_reset_token
from routes.stats import _low_stock_q, _out_of_stock_q
from services import image_generation as gen
from services import image_service
from services.product_service import paginate
from utils import ok, fail, admin_required, clean, to_int

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ---------------- customers ----------------

@admin_bp.get("/customers")
@admin_required
def list_customers():
    spend = func.coalesce(func.sum(Order.grand_total), 0)
    q = (db.session.query(Customer, func.count(Order.id), spend, func.max(Order.created_at))
         .outerjoin(Order, (Order.customer_id == Customer.id) & (Order.status != "cancelled"))
         .group_by(Customer.id))
    term = clean(request.args.get("q"), 80)
    if term:
        like = f"%{term}%"
        q = q.filter(or_(Customer.name.ilike(like), Customer.phone.ilike(like), Customer.email.ilike(like)))
    kind = request.args.get("type")
    if kind == "registered":
        q = q.filter(Customer.password_hash.isnot(None))
    elif kind == "guest":
        q = q.filter(Customer.password_hash.is_(None))
    q = q.order_by(func.max(Order.created_at).desc().nullslast(), Customer.created_at.desc())
    rows, meta = paginate(q, request.args.get("page", 1), request.args.get("limit", 50))
    out = []
    for c, count, total, last in rows:
        d = c.to_dict()
        d.update(order_count=count, total_spent=round(total or 0, 2),
                 last_order_at=last.isoformat() if last else None)
        out.append(d)
    return ok(out, meta=meta)


@admin_bp.get("/customers/<int:cid>")
@admin_required
def get_customer(cid):
    c = db.session.get(Customer, cid)
    if not c:
        return fail("Customer not found", 404)
    d = c.to_dict()
    d["orders"] = [{k: v for k, v in o.to_dict().items() if k not in ("items", "history")}
                   for o in sorted(c.orders, key=lambda o: o.created_at or 0, reverse=True)]
    return ok(d)


@admin_bp.put("/customers/<int:cid>")
@admin_required
def update_customer(cid):
    c = db.session.get(Customer, cid)
    if not c:
        return fail("Customer not found", 404)
    data = request.get_json(silent=True) or {}
    if "is_active" in data:
        c.is_active = bool(data["is_active"])
    db.session.commit()
    return ok(c.to_dict(), message="Customer updated")


@admin_bp.post("/customers/<int:cid>/reset-link")
@admin_required
def customer_reset_link(cid):
    c = db.session.get(Customer, cid)
    if not c or not c.is_registered:
        return fail("Only registered customers can reset a password", 400)
    token = issue_reset_token(c)
    link = f"{request.host_url.rstrip('/')}/account.html?reset={token}"
    return ok({"link": link, "phone": c.phone, "name": c.name},
              message="Reset link created (valid 24 hours). Send it to the customer privately.")


# ---------------- inventory ----------------

@admin_bp.get("/inventory")
@admin_required
def inventory():
    status = request.args.get("status")
    if status == "low":
        q = _low_stock_q()
    elif status == "out":
        q = _out_of_stock_q()
    elif status == "in":
        q = Product.query.filter(Product.availability.is_(True),
                                 Product.stock > func.coalesce(Product.min_stock, 5))
    else:
        q = Product.query
    term = clean(request.args.get("q"), 80)
    if term:
        like = f"%{term}%"
        q = q.filter(or_(Product.name.ilike(like), Product.sku.ilike(like), Product.brand.ilike(like)))
    q = q.order_by(Product.stock.asc(), Product.name)
    items, meta = paginate(q, request.args.get("page", 1), request.args.get("limit", 50))
    summary = {
        "total": Product.query.count(),
        "low": _low_stock_q().count(),
        "out": _out_of_stock_q().count(),
    }
    summary["in"] = summary["total"] - summary["low"] - summary["out"]
    return ok([p.to_dict() for p in items], meta=meta, summary=summary)


@admin_bp.put("/inventory/<int:pid>")
@admin_required
def update_inventory(pid):
    p = db.session.get(Product, pid)
    if not p:
        return fail("Product not found", 404)
    data = request.get_json(silent=True) or {}
    if "stock" in data:
        stock = to_int(data["stock"])
        if stock is None or stock < 0:
            return fail("Stock must be 0 or more")
        p.stock = stock
    if "adjust" in data:
        delta = to_int(data["adjust"])
        if delta is None or (p.stock or 0) + delta < 0:
            return fail("Adjustment would make stock negative")
        p.stock = (p.stock or 0) + delta
    if "min_stock" in data:
        ms = to_int(data["min_stock"])
        if ms is None or ms < 0:
            return fail("Minimum stock must be 0 or more")
        p.min_stock = ms
    if "availability" in data:
        p.availability = bool(data["availability"])
    db.session.commit()
    return ok(p.to_dict(), message="Stock updated")


# ---------------- brands ----------------

@admin_bp.get("/brands")
@admin_required
def brands():
    rows = (db.session.query(Product.brand, func.count(Product.id))
            .filter(Product.brand.isnot(None), Product.brand != "")
            .group_by(Product.brand).order_by(Product.brand).all())
    return ok([{"brand": b, "count": n} for b, n in rows])


@admin_bp.put("/brands")
@admin_required
def rename_brand():
    data = request.get_json(silent=True) or {}
    old, new = clean(data.get("from"), 120), clean(data.get("to"), 120)
    if not old:
        return fail("Choose a brand")
    n = Product.query.filter_by(brand=old).update({"brand": new or None})
    db.session.commit()
    return ok({"count": n}, message=f"Updated {n} product(s)")


# ---------------- AI overview ----------------

@admin_bp.get("/ai/overview")
@admin_required
def ai_overview():
    convs = AIConversation.query.order_by(AIConversation.created_at.desc()).limit(25).all()
    report = image_service.report()
    counts = report["counts"]
    attempted = counts.get("ready", 0) + counts.get("failed", 0) + counts.get("fallback", 0)
    job = image_service.active_job()
    return ok({
        "assistant": {
            "mode": "rule-based (answers only from the product database)",
            "conversations": AIConversation.query.count(),
            "messages": AIMessage.query.count(),
            "customer_questions": AIMessage.query.filter_by(role="user").count(),
        },
        "images": {
            "counts": counts,
            "success_rate": round(100 * counts.get("ready", 0) / attempted) if attempted else None,
            "primary_provider": (report["providers_configured"] or [None])[0],
            "fallback_providers": report["providers_configured"][1:],
            "usable_providers": report["providers_usable"],
            "models": {p: gen.model_for(p) for p in report["providers_configured"]},
            "active_job": image_service.job_public(job) if job else None,
            "failed": [{"id": pid, "error": r.get("error") or r.get("reason")}
                       for pid, r in report["products"].items() if r["status"] == "failed"][:50],
        },
        "conversations": [{
            "id": c.id, "created_at": c.created_at.isoformat() if c.created_at else None,
            "messages": [{"role": m.role, "content": m.content} for m in
                         sorted(c.messages, key=lambda m: m.id)][:40],
        } for c in convs],
    })
