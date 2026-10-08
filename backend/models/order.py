"""Orders and their line items."""
from datetime import datetime
from database.db import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"))
    status = db.Column(db.String(40), default="new")   # new / quoted / confirmed / done / cancelled
    note = db.Column(db.Text)
    total = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship(
        "OrderItem", backref="order", lazy="select", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "customer": self.customer.to_dict() if self.customer else None,
            "status": self.status,
            "note": self.note,
            "total": self.total,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "items": [i.to_dict() for i in self.items],
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    product_name = db.Column(db.String(200))
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, default=0)

    product = db.relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "price": self.price,
            "subtotal": (self.price or 0) * (self.quantity or 0),
        }