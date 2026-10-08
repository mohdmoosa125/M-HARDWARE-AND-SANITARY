"""
Orders, their line items and status history.
Line items keep a snapshot of name/SKU/unit/price so old orders and
invoices stay correct even when the product changes later.
"""
from datetime import datetime
from database.db import db

ORDER_STATUSES = [
    "pending", "confirmed", "processing", "ready_for_pickup",
    "out_for_delivery", "delivered", "cancelled",
]
PAYMENT_STATUSES = ["pending", "paid", "failed", "refunded", "cash"]

# Statuses used before the checkout upgrade -> current names
LEGACY_STATUS = {"new": "pending", "quoted": "pending", "done": "delivered"}

STATUS_LABELS = {
    "pending": "Pending", "confirmed": "Confirmed", "processing": "Processing",
    "ready_for_pickup": "Ready for Pickup", "out_for_delivery": "Out for Delivery",
    "delivered": "Delivered", "cancelled": "Cancelled",
}


def _iso(dt):
    return dt.isoformat() if dt else None


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(40), unique=True, index=True)
    access_token = db.Column(db.String(64))            # lets a guest open their own order
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"))
    status = db.Column(db.String(40), default="pending")
    note = db.Column(db.Text)                          # customer delivery instructions

    order_type = db.Column(db.String(20), default="delivery")    # delivery | pickup
    payment_method = db.Column(db.String(20), default="cod")     # cod | upi | online
    payment_status = db.Column(db.String(20), default="pending")

    subtotal = db.Column(db.Float, default=0)          # sum of MRP x qty
    discount = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    delivery_fee = db.Column(db.Float, default=0)
    grand_total = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)             # legacy column, kept = grand_total

    shipping_name = db.Column(db.String(150))
    shipping_phone = db.Column(db.String(30))
    shipping_email = db.Column(db.String(150))
    shipping_address = db.Column(db.Text)
    shipping_city = db.Column(db.String(80))
    shipping_state = db.Column(db.String(80))
    shipping_pincode = db.Column(db.String(12))
    admin_note = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship(
        "OrderItem", backref="order", lazy="select", cascade="all, delete-orphan"
    )
    history = db.relationship(
        "OrderStatusHistory", backref="order", lazy="select",
        cascade="all, delete-orphan", order_by="OrderStatusHistory.created_at",
    )
    invoice = db.relationship("Invoice", backref="order", uselist=False, lazy="select")

    @property
    def status_key(self):
        return LEGACY_STATUS.get(self.status, self.status or "pending")

    def to_dict(self, admin=False):
        status = self.status_key
        total = self.grand_total if self.grand_total else (self.total or 0)
        data = {
            "id": self.id,
            "order_number": self.order_number or f"#{self.id}",
            "status": status,
            "status_label": STATUS_LABELS.get(status, status),
            "order_type": self.order_type or "delivery",
            "payment_method": self.payment_method or "cod",
            "payment_status": self.payment_status or "pending",
            "note": self.note,
            "subtotal": self.subtotal or 0,
            "discount": self.discount or 0,
            "tax": self.tax or 0,
            "delivery_fee": self.delivery_fee or 0,
            "grand_total": total,
            "total": total,
            "shipping": {
                "name": self.shipping_name or (self.customer.name if self.customer else ""),
                "phone": self.shipping_phone or (self.customer.phone if self.customer else ""),
                "email": self.shipping_email,
                "address": self.shipping_address,
                "city": self.shipping_city,
                "state": self.shipping_state,
                "pincode": self.shipping_pincode,
            },
            "item_count": sum(i.quantity or 0 for i in self.items),
            "items": [i.to_dict() for i in self.items],
            "history": [h.to_dict() for h in self.history],
            "invoice_number": self.invoice.invoice_number if self.invoice else None,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }
        if admin:
            data["customer"] = self.customer.to_dict() if self.customer else None
            data["admin_note"] = self.admin_note
        return data


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    product_name = db.Column(db.String(200))           # snapshot
    sku = db.Column(db.String(80))                     # snapshot
    unit = db.Column(db.String(40))                    # snapshot
    image = db.Column(db.String(255))                  # snapshot
    quantity = db.Column(db.Integer, default=1)
    mrp = db.Column(db.Float)                          # list price per unit at order time
    price = db.Column(db.Float, default=0)             # price charged per unit
    discount = db.Column(db.Float, default=0)          # (mrp - price) x qty
    subtotal = db.Column(db.Float)                     # price x qty

    product = db.relationship("Product")

    def to_dict(self):
        price = self.price or 0
        qty = self.quantity or 0
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_slug": self.product.slug if self.product else None,
            "sku": self.sku,
            "unit": self.unit or "piece",
            "image": self.image or (self.product.image if self.product else None),
            "quantity": qty,
            "mrp": self.mrp if self.mrp is not None else price,
            "price": price,
            "discount": self.discount or 0,
            "subtotal": self.subtotal if self.subtotal is not None else price * qty,
        }


class OrderStatusHistory(db.Model):
    """One row per status change — drives the customer tracking timeline."""
    __tablename__ = "order_status_history"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), index=True)
    status = db.Column(db.String(40))
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "status": self.status,
            "label": STATUS_LABELS.get(self.status, self.status),
            "note": self.note,
            "created_at": _iso(self.created_at),
        }
