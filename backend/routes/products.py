"""Product CRUD, search, filters, related products."""
from flask import Blueprint, request, current_app
from database.db import db
from models import Product, Category, Setting
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


@products_bp.get("/<int:pid>/related")
def related_products(pid):
    product = db.session.get(Product, pid)
    if not product:
        return fail("Product not found", 404)

    q = Product.query.filter(Product.id != pid)
    if product.category_id:
        q = q.filter(Product.category_id == product.category_id)
    elif product.brand:
        q = q.filter(Product.brand == product.brand)
    return ok([p.to_dict() for p in q.limit(4).all()])


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
    if "discount_price" in data:
        product.discount_price = (
            float(data["discount_price"]) if data["discount_price"] not in (None, "", 0) else None
        )
    if "stock" in data:
        product.stock = int(data["stock"] or 0)
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

    product = Product(name=name, slug=_unique_slug(name))
    _apply_product_fields(product, data)

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
    if "name" in data and data["name"].strip():
        product.name = data["name"].strip()
        product.slug = _unique_slug(product.name, ignore_id=pid)

    _apply_product_fields(product, data)
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
    db.session.delete(product)
    db.session.commit()
    return ok(message="Product deleted")