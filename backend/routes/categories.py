"""Category & subcategory CRUD."""
from flask import Blueprint, request
from database.db import db
from models import Category, Product
from utils import ok, fail, slugify, admin_required, to_int

categories_bp = Blueprint("categories", __name__, url_prefix="/api/categories")


def _unique_slug(name, ignore_id=None):
    base = slugify(name) or "category"
    slug = base
    i = 2
    while True:
        q = Category.query.filter_by(slug=slug)
        if ignore_id:
            q = q.filter(Category.id != ignore_id)
        if not q.first():
            return slug
        slug = f"{base}-{i}"
        i += 1


# ---------------- PUBLIC ----------------

@categories_bp.get("")
def list_categories():
    """?tree=1 returns nested structure, otherwise a flat list."""
    tree = request.args.get("tree") in ("1", "true")

    if tree:
        roots = Category.query.filter_by(parent_id=None, is_active=True)\
                               .order_by(Category.sort_order, Category.name).all()
        return ok([c.to_dict(with_children=True) for c in roots])

    cats = Category.query.order_by(Category.sort_order, Category.name).all()
    return ok([c.to_dict(with_children=True) for c in cats])


@categories_bp.get("/<ident>")
def get_category(ident):
    cat = _find(ident)
    if not cat:
        return fail("Category not found", 404)
    data = cat.to_dict(with_children=True)
    data["products"] = [p.to_dict() for p in cat.products]
    return ok(data)


@categories_bp.get("/<ident>/products")
def category_products(ident):
    cat = _find(ident)
    if not cat:
        return fail("Category not found", 404)
    ids = [cat.id] + [c.id for c in cat.children]
    products = Product.query.filter(Product.category_id.in_(ids)).all()
    return ok([p.to_dict() for p in products])


def _find(ident):
    if str(ident).isdigit():
        return db.session.get(Category, int(ident))
    return Category.query.filter_by(slug=ident).first()


# ---------------- ADMIN ----------------

@categories_bp.post("")
@admin_required
def create_category():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return fail("Category name is required")

    cat = Category(
        name=name,
        slug=_unique_slug(name),
        description=data.get("description"),
        image=data.get("image"),
        parent_id=data.get("parent_id") or None,
        sort_order=to_int(data.get("sort_order"), 0),
        is_active=bool(data.get("is_active", True)),
        featured=bool(data.get("featured", False)),
    )
    db.session.add(cat)
    db.session.commit()
    return ok(cat.to_dict(), message="Category created")


@categories_bp.put("/<int:cid>")
@admin_required
def update_category(cid):
    cat = db.session.get(Category, cid)
    if not cat:
        return fail("Category not found", 404)

    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"].strip():
        cat.name = data["name"].strip()
        cat.slug = _unique_slug(cat.name, ignore_id=cid)
    if "description" in data:
        cat.description = data["description"]
    if "image" in data:
        cat.image = data["image"]
    if "parent_id" in data:
        # prevent a category from becoming its own parent
        pid = to_int(data["parent_id"])
        cat.parent_id = None if (not pid or pid == cid) else pid
    if "sort_order" in data:
        cat.sort_order = to_int(data["sort_order"], 0)
    if "is_active" in data:
        cat.is_active = bool(data["is_active"])
    if "featured" in data:
        cat.featured = bool(data["featured"])

    db.session.commit()
    return ok(cat.to_dict(), message="Category updated")


@categories_bp.delete("/<int:cid>")
@admin_required
def delete_category(cid):
    cat = db.session.get(Category, cid)
    if not cat:
        return fail("Category not found", 404)

    # detach children and products instead of destroying them
    Category.query.filter_by(parent_id=cid).update({"parent_id": None})
    Product.query.filter_by(category_id=cid).update({"category_id": None})

    db.session.delete(cat)
    db.session.commit()
    return ok(message="Category deleted")


@categories_bp.post("/<int:cid>/generate-image")
@admin_required
def generate_category_image(cid):
    """AI image via the configured providers; otherwise reuse the best real product photo."""
    from services.category_image import generate
    cat = db.session.get(Category, cid)
    if not cat:
        return fail("Category not found", 404)
    path, source, error = generate(cat)
    if not path:
        return fail(error or "Could not create a category image", 422)
    cat.image = path
    db.session.commit()
    return ok(cat.to_dict(), message=f"Category image updated ({source})")