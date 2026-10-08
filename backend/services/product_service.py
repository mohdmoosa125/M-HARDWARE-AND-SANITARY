"""
product_service.py
------------------
All product query logic lives here so routes stay short.
"""
from sqlalchemy import or_, func
from database.db import db
from models import Product, Category


def build_product_query(args):
    """
    Build a SQLAlchemy query from the URL query string.
    Supported args:
        q, category, subcategory, brand, min_price, max_price,
        color, material, size, availability, featured, discount, sort
    """
    query = Product.query

    # ---- search box ----
    q = (args.get("q") or "").strip()[:100]
    if q:
        # every word must match somewhere (name, brand, SKU, text, material or category)
        query = query.outerjoin(Category)
        for word in q.split()[:6]:
            like = f"%{word}%"
            query = query.filter(
                or_(
                    Product.name.ilike(like),
                    Product.brand.ilike(like),
                    Product.sku.ilike(like),
                    Product.description.ilike(like),
                    Product.short_description.ilike(like),
                    Product.material.ilike(like),
                    Category.name.ilike(like),
                )
            )

    # ---- category (slug or id) ----
    category = args.get("category")
    if category:
        cat = Category.query.filter(
            or_(Category.slug == category, Category.id == _as_int(category))
        ).first()
        if cat:
            # include subcategory products too
            ids = [cat.id] + [c.id for c in cat.children]
            query = query.filter(Product.category_id.in_(ids))
        else:
            query = query.filter(db.false())

    # ---- subcategory ----
    sub = args.get("subcategory")
    if sub:
        sc = Category.query.filter(
            or_(Category.slug == sub, Category.id == _as_int(sub))
        ).first()
        query = query.filter(Product.category_id == sc.id) if sc else query.filter(db.false())

    # ---- simple equals filters ----
    if args.get("brand"):
        brands = [b for b in args["brand"].split(",") if b]
        query = query.filter(Product.brand.in_(brands))
    if args.get("color"):
        query = query.filter(Product.color == args["color"])
    if args.get("material"):
        query = query.filter(Product.material == args["material"])
    if args.get("size"):
        query = query.filter(Product.size == args["size"])

    # ---- price range (on the price the customer actually pays) ----
    final_price = func.coalesce(Product.discount_price, Product.price)
    min_price, max_price = _as_float(args.get("min_price")), _as_float(args.get("max_price"))
    if min_price is not None:
        query = query.filter(final_price >= min_price)
    if max_price is not None:
        query = query.filter(final_price <= max_price)

    # ---- availability / featured ----
    if args.get("availability") in ("1", "true", "in"):
        query = query.filter(Product.availability.is_(True), Product.stock > 0)
    if args.get("featured") in ("1", "true"):
        query = query.filter(Product.featured.is_(True))

    # ---- admin: image status ----
    if args.get("image_status"):
        query = query.filter(Product.image_status.in_(args["image_status"].split(",")))

    # ---- discounted only ----
    if args.get("discount") in ("1", "true"):
        query = query.filter(Product.discount_price.isnot(None),
                             Product.discount_price < Product.price)

    # ---- sorting ----
    sort = args.get("sort", "newest")
    if sort == "price_asc":
        query = query.order_by(final_price.asc())
    elif sort == "price_desc":
        query = query.order_by(final_price.desc())
    elif sort == "featured":
        query = query.order_by(Product.featured.desc(), Product.created_at.desc())
    elif sort == "discount":
        query = query.order_by(
            ((Product.price - func.coalesce(Product.discount_price, Product.price)) / Product.price).desc()
        )
    elif sort == "name_asc":
        query = query.order_by(Product.name.asc())
    else:
        query = query.order_by(Product.created_at.desc())

    return query


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def _as_float(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def paginate(query, page=1, limit=20):
    """Return (items, meta) with page clamping."""
    page = max(1, _as_int(page) if _as_int(page) > 0 else 1)
    limit = min(100, max(1, _as_int(limit) if _as_int(limit) > 0 else 20))
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    pages = (total + limit - 1) // limit
    return items, {
        "page": page,
        "limit": limit,
        "total": total,
        "pages": pages,
    }