"""Gallery images."""
from flask import Blueprint, request
from database.db import db
from models import GalleryImage
from utils import ok, fail, admin_required

gallery_bp = Blueprint("gallery", __name__, url_prefix="/api/gallery")


@gallery_bp.get("")
def list_images():
    category = request.args.get("category")
    q = GalleryImage.query
    if category:
        q = q.filter_by(category=category)
    rows = q.order_by(GalleryImage.sort_order, GalleryImage.id.desc()).all()
    return ok([r.to_dict() for r in rows])


@gallery_bp.get("/categories")
def gallery_categories():
    rows = db.session.query(GalleryImage.category).distinct().all()
    return ok(sorted({r[0] for r in rows if r[0]}))


@gallery_bp.post("")
@admin_required
def add_image():
    data = request.get_json(silent=True) or {}
    if not data.get("image"):
        return fail("Image path is required")
    row = GalleryImage(
        title=data.get("title"),
        category=data.get("category") or "Shop",
        image=data["image"],
        sort_order=int(data.get("sort_order") or 0),
    )
    db.session.add(row)
    db.session.commit()
    return ok(row.to_dict(), message="Image added")


@gallery_bp.delete("/<int:gid>")
@admin_required
def delete_image(gid):
    row = db.session.get(GalleryImage, gid)
    if not row:
        return fail("Image not found", 404)
    db.session.delete(row)
    db.session.commit()
    return ok(message="Image deleted")