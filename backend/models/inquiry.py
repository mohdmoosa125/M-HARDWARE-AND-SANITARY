"""Product inquiries (Request-a-Quote) and general contact messages."""
from datetime import datetime
from database.db import db


class Inquiry(db.Model):
    __tablename__ = "inquiries"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)

    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30))
    whatsapp = db.Column(db.String(30))
    email = db.Column(db.String(150))
    address = db.Column(db.Text)

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    product_name = db.Column(db.String(200))
    quantity = db.Column(db.String(60))
    message = db.Column(db.Text)

    status = db.Column(db.String(40), default="new")   # new / contacted / closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "whatsapp": self.whatsapp,
            "email": self.email,
            "address": self.address,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(150))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }