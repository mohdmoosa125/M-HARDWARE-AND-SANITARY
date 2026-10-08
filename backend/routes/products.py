"""Product CRUD, search, filters, related products."""
from flask import Blueprint, request, current_app
from database.db import db
from models import Product, Category, Setting, OrderItem, WishlistItem
from services import image_service
from services.product_service import build_product_query, paginate
from utils import ok, fail, slugify, admin_required

products_bp = Blueprint("products", __name__, url_prefix="/api/products")


def _unique_slug(name, ignore_id=None):
    base = slugify(name) or "product"
    slug = base
    i = 2
    while True:
        q = Product.query.filter_by(slug=slug)
        if ignore_id:
            q = q.filter(Product.id != ignore_id)
        if not q.first():
            return slug
        slug = f"{base}-{i}"
        i += 1


# ---------------- PUBLIC ----------------

@products_bp.get("")
def list_products():
    """Supports search, filters, sorting and pagination."""
    query = build_product_query(request.args)
    items, meta = paginate(query, request.args.get("page", 1), request.args.get("limit", 20))
    return ok([p.to_dict() for p in items], meta=meta)


@products_bp.get("/search")
def search_products():
    query = build_product_query(request.args)
    items, meta = paginate(query, request.args.get("page", 1), request.args.get("limit", 20))
    return ok([p.to_dict() for p in items], meta=meta, query=request.args.get("q", ""))


@products_bp.get("/brands")
def list_brands():
    rows = db.session.query(Product.brand).filter(Product.brand.isnot(None)).distinct().all()
    return ok(sorted({r[0] for r in rows if r[0]}))


@products_bp.get("/filters")
def filter_options():
    """Everything the products page needs to build its filter sidebar."""
    def distinct(col):
        rows = db.session.query(col).filter(col.isnot(None)).distinct().all()
        return sorted({r[0] for r in rows if r[0]})

    return ok({
        "brands": distinct(Product.brand),
        "colors": distinct(Product.color),
        "materials": distinct(Product.material),
        "sizes": distinct(Product.size),
        "categories": [c.to_dict() for c in Category.query.order_by(Category.name).all()],
    })


@products_bp.get("/<int:pid>")
def get_product(pid):
    product = db.session.get(Product, pid)
    if not product:
        return fail("Product not found", 404)
    return ok(product.to_dict())


@products_bp.get("/slug/<slug>")
def get_product_by_slug(slug):
    product = Product.query.filter_by(slug=slug).first()
    if not product:
        return fail("Product not found", 404)
    return ok(product.to_dict())


@products_bp.get("/compare")
def compare_products():
    """?ids=1,2,3 (max 4) — same order as requested."""
    ids = [int(x) for x in (request.args.get("ids") or "").split(",") if x.strip().isdigit()][:4]
    if len(ids) < 2:
        return fail("Choose at least two products to compare")
    found = {p.id: p for p in Product.query.filter(Product.id.in_(ids)).all()}
    return ok([found[i].to_dict() for i in ids if i in found])


@products_bp.get("/<int:pid>/related")
def related_products(pid):
    """Same category first, then sibling subcategories, then same brand; nearest price wins."""
    product = db.session.get(Product, pid)
    if not product:
        return fail("Product not found", 404)
    limit = min(12, max(1, request.args.get("limit", 8, type=int)))
    price = product.final_price or 0

    def nearest(q, n):
        rows = q.filter(Product.id != pid).limit(60).all()
        return sorted(rows, key=lambda p: (not p.in_stock, abs((p.final_price or 0) - price)))[:n]

    picked = []
    cat = product.category
    pools = []
    if cat:
        pools.append(Product.query.filter(Product.category_id == cat.id))
        family = cat.parent or cat
        ids = [family.id] + [c.id for c in family.children]
        pools.append(Product.query.filter(Product.category_id.in_(ids)))
    if product.brand:
        pools.append(Product.query.filter(Product.brand == product.brand))
    for q in pools:
        for p in nearest(q, limit):
            if p not in picked:
                picked.append(p)
        if len(picked) >= limit:
            break
    return ok([p.to_dict() for p in picked[:limit]])


# ---------------- ADMIN ----------------

def _apply_product_fields(product, data):
    """Copy JSON fields onto a Product object (used by POST and PUT)."""
    simple = [
        "name", "brand", "sku", "description", "short_description",
        "unit", "material", "size", "color", "weight",
        "finish", "thickness", "coverage", "image",
    ]
    for field in simple:
        if field in data:
            setattr(product, field, data[field])

    if "price" in data:
        product.price = float(data["price"] or 0)
        if product.price < 0:
            raise ValueError("Price cannot be negative")
    if "discount_price" in data:
        product.discount_price = (
            float(data["discount_price"]) if data["discount_price"] not in (None, "", 0, "0") else None
        )
    if product.discount_price is not None and not (0 < product.discount_price < (product.price or 0)):
        raise ValueError("Discount price must be more than 0 and lower than the price")
    if "stock" in data:
        product.stock = int(data["stock"] or 0)
        if product.stock < 0:
            raise ValueError("Stock cannot be negative")
    if "min_stock" in data:
        product.min_stock = max(0, int(data["min_stock"] or 0))
    if "pieces_per_box" in data:
        product.pieces_per_box = (
            int(data["pieces_per_box"]) if data["pieces_per_box"] not in (None, "") else None
        )
    if "category_id" in data:
        product.category_id = int(data["category_id"]) if data["category_id"] else None
    if "availability" in data:
        product.availability = bool(data["availability"])
    if "featured" in data:
        product.featured = bool(data["featured"])

    if "additional_images" in data:
        import json
        imgs = data["additional_images"] or []
        product.additional_images = json.dumps(imgs) if imgs else None


@products_bp.post("")
@admin_required
def create_product():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return fail("Product name is required")

    product = Product(name=name, slug=_unique_slug(data.get("slug") or name))
    try:
        _apply_product_fields(product, data)
    except (TypeError, ValueError) as e:
        return fail(_field_error(e))

    db.session.add(product)
    db.session.flush()
    image_service.on_product_created(current_app._get_current_object(), product)
    db.session.commit()
    return ok(product.to_dict(), message="Product created")


@products_bp.put("/<int:pid>")
@admin_required
def update_product(pid):
    product = db.session.get(Product, pid)
    if not product:
        return fail("Product not found", 404)

    data = request.get_json(silent=True) or {}
    old_image = product.image
    if "name" in data and str(data["name"]).strip():
        product.name = str(data["name"]).strip()
    if str(data.get("slug") or "").strip():
        product.slug = _unique_slug(data["slug"], ignore_id=pid)
    elif "name" in data:
        product.slug = _unique_slug(product.name, ignore_id=pid)

    try:
        _apply_product_fields(product, data)
    except (TypeError, ValueError) as e:
        db.session.rollback()
        return fail(_field_error(e))
    if product.image != old_image:                 # manual upload always overrides generated images
        image_service.mark_manual_image(product)

    db.session.commit()
    return ok(product.to_dict(), message="Product updated")


@products_bp.delete("/<int:pid>")
@admin_required
def delete_product(pid):
    product = db.session.get(Product, pid)
    if not product:
        return fail("Product not found", 404)
    _delete(product)
    db.session.commit()
    return ok(message="Product deleted")


def _field_error(e):
    msg = str(e)
    return msg if msg and not msg.startswith(("could not convert", "invalid literal")) \
        else "Please enter valid numbers for price, stock and quantities"


def _delete(product):
    """Order lines keep their name/price snapshot; only the link is cleared."""
    OrderItem.query.filter_by(product_id=product.id).update({"product_id": None})
    WishlistItem.query.filter_by(product_id=product.id).delete()
    db.session.delete(product)


@products_bp.post("/<int:pid>/duplicate")
@admin_required
def duplicate_product(pid):
    src = db.session.get(Product, pid)
    if not src:
        return fail("Product not found", 404)
    skip = {"id", "slug", "sku", "created_at", "updated_at", "image_updated_at"}
    copy = Product(**{c.name: getattr(src, c.name) for c in Product.__table__.columns if c.name not in skip})
    copy.name = f"{src.name} (Copy)"
    copy.slug = _unique_slug(copy.name)
    copy.featured = False
    db.session.add(copy)
    db.session.commit()
    return ok(copy.to_dict(), message="Product duplicated")


BULK_FIELDS = {"category_id", "brand", "availability", "featured", "unit", "min_stock"}


@products_bp.post("/bulk")
@admin_required
def bulk_products():
    """{ids: [...], action: "delete" | "update", fields: {...}}"""
    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in (data.get("ids") or []) if str(i).isdigit()][:500]
    if not ids:
        return fail("Select at least one product")
    products = Product.query.filter(Product.id.in_(ids)).all()
    action = data.get("action")
    if action == "delete":
        for p in products:
            _delete(p)
        db.session.commit()
        return ok({"count": len(products)}, message=f"{len(products)} product(s) deleted")
    if action == "update":
        fields = {k: v for k, v in (data.get("fields") or {}).items() if k in BULK_FIELDS}
        if not fields:
            return fail("Nothing to update")
        try:
            for p in products:
                _apply_product_fields(p, fields)
        except (TypeError, ValueError) as e:
            db.session.rollback()
            return fail(_field_error(e))
        db.session.commit()
        return ok({"count": len(products)}, message=f"{len(products)} product(s) updated")
    return fail("Unknown bulk action")