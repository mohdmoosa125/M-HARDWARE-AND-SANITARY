"""Product enquiries (Request a Quote)."""
from flask import Blueprint, request
from database.db import db
from models import Inquiry, Customer
from utils import ok, fail, admin_required

inquiries_bp = Blueprint("inquiries", __name__, url_prefix="/api/inquiries")


@inquiries_bp.post("")
def create_inquiry():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return fail("Your name is required")

    phone = (data.get("phone") or "").strip()
    customer = Customer.query.filter_by(phone=phone).first() if phone else None
    if not customer:
        customer = Customer(
            name=name,
            phone=phone,
            whatsapp=data.get("whatsapp") or phone,
            email=data.get("email"),
            address=data.get("address"),
        )
        db.session.add(customer)
        db.session.flush()

    inquiry = Inquiry(
        customer_id=customer.id,
        name=name,
        phone=phone,
        whatsapp=data.get("whatsapp") or phone,
        email=data.get("email"),
        address=data.get("address"),
        product_id=data.get("product_id") or None,
        product_name=data.get("product_name"),
        quantity=data.get("quantity"),
        message=data.get("message"),
    )
    db.session.add(inquiry)
    db.session.commit()
    return ok(inquiry.to_dict(), message="Enquiry sent. We'll contact you soon.")


@inquiries_bp.get("")
@admin_required
def list_inquiries():
    status = request.args.get("status")
    q = Inquiry.query
    if status:
        q = q.filter_by(status=status)
    rows = q.order_by(Inquiry.created_at.desc()).all()
    return ok([i.to_dict() for i in rows])


@inquiries_bp.put("/<int:iid>")
@admin_required
def update_inquiry(iid):
    inquiry = db.session.get(Inquiry, iid)
    if not inquiry:
        return fail("Inquiry not found", 404)
    data = request.get_json(silent=True) or {}
    if "status" in data:
        inquiry.status = data["status"]
    db.session.commit()
    return ok(inquiry.to_dict(), message="Inquiry updated")


@inquiries_bp.delete("/<int:iid>")
@admin_required
def delete_inquiry(iid):
    inquiry = db.session.get(Inquiry, iid)
    if not inquiry:
        return fail("Inquiry not found", 404)
    db.session.delete(inquiry)
    db.session.commit()
    return ok(message="Inquiry deleted")