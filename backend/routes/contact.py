"""General contact form messages."""
from flask import Blueprint, request
from database.db import db
from models import ContactMessage
from utils import ok, fail, admin_required

contact_bp = Blueprint("contact", __name__, url_prefix="/api/contact")


@contact_bp.post("")
def send_message():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    message = (data.get("message") or "").strip()
    if not name or not message:
        return fail("Name and message are required")

    row = ContactMessage(
        name=name,
        phone=data.get("phone"),
        email=data.get("email"),
        message=message,
    )
    db.session.add(row)
    db.session.commit()
    return ok(row.to_dict(), message="Thank you! We will get back to you soon.")


@contact_bp.get("")
@admin_required
def list_messages():
    rows = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return ok([r.to_dict() for r in rows])


@contact_bp.delete("/<int:mid>")
@admin_required
def delete_message(mid):
    row = db.session.get(ContactMessage, mid)
    if not row:
        return fail("Message not found", 404)
    db.session.delete(row)
    db.session.commit()
    return ok(message="Message deleted")