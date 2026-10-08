"""
Customer records.
Guests are created automatically when they order/enquire (no password).
Registered customers have a password_hash and can log in to see their orders.
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
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

    # ---- customer accounts ----
    password_hash = db.Column(db.String(255))          # NULL = guest (no login)
    is_active = db.Column(db.Boolean, default=True)
    last_login_at = db.Column(db.DateTime)
    reset_token_hash = db.Column(db.String(255))       # one-time password reset link
    reset_expires_at = db.Column(db.DateTime)

    orders = db.relationship("Order", backref="customer", lazy="select")
    inquiries = db.relationship("Inquiry", backref="customer", lazy="select")

    @property
    def is_registered(self):
        return bool(self.password_hash)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return bool(self.password_hash) and check_password_hash(self.password_hash, raw_password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "whatsapp": self.whatsapp,
            "email": self.email,
            "address": self.address,
            "is_registered": self.is_registered,
            "is_active": self.is_active is not False,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
