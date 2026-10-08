"""
Invoice — one per order, created automatically when the order is placed.
Business details are snapshotted so an old invoice never changes when
settings are edited later. Totals live on the (immutable) order.
"""
import json
from datetime import datetime
from database.db import db


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), unique=True, nullable=False)
    business_snapshot = db.Column(db.Text)             # JSON
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)

    def business(self):
        try:
            return json.loads(self.business_snapshot or "{}")
        except ValueError:
            return {}

    def to_dict(self, admin=False):
        order = self.order
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "business": self.business(),
            "order": order.to_dict(admin=admin) if order else None,
        }
