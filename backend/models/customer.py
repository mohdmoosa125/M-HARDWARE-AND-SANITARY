"""Customer records (created automatically when an order/enquiry comes in)."""
from datetime import datetime
from database.db import db


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30))
    whatsapp = db.Column(db.String(30))
    email = db.Column(db.String(150))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship("Order", backref="customer", lazy="select")
    inquiries = db.relationship("Inquiry", backref="customer", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "whatsapp": self.whatsapp,
            "email": self.email,
            "address": self.address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }