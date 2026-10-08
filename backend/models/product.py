"""Product model — supports hardware, sanitary and tile-specific fields."""
import json
from datetime import datetime
from database.db import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    brand = db.Column(db.String(120))
    sku = db.Column(db.String(80))

    description = db.Column(db.Text)
    short_description = db.Column(db.String(300))

    price = db.Column(db.Float, default=0)
    discount_price = db.Column(db.Float)
    unit = db.Column(db.String(40), default="piece")
    stock = db.Column(db.Integer, default=0)

    image = db.Column(db.String(255))
    additional_images = db.Column(db.Text)      # JSON list of paths
    # Image Agent bookkeeping: missing | processing | ready | fallback | failed
    image_status = db.Column(db.String(20), default="missing")
    image_updated_at = db.Column(db.DateTime)
    image_provider = db.Column(db.String(80))       # e.g. "gemini:model", "manual", "reference"
    image_error = db.Column(db.String(255))         # last problem, never a secret

    material = db.Column(db.String(120))
    size = db.Column(db.String(120))
    color = db.Column(db.String(80))
    weight = db.Column(db.String(60))

    # Tile-specific extras
    finish = db.Column(db.String(80))
    thickness = db.Column(db.String(60))
    pieces_per_box = db.Column(db.Integer)
    coverage = db.Column(db.String(80))

    availability = db.Column(db.Boolean, default=True)
    featured = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ---------- helpers ----------
    @property
    def final_price(self):
        return self.discount_price if self.discount_price else self.price

    def extra_images(self):
        if not self.additional_images:
            return []
        try:
            return json.loads(self.additional_images)
        except Exception:
            return []

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "",
            "category_slug": self.category.slug if self.category else "",
            "brand": self.brand,
            "sku": self.sku,
            "description": self.description,
            "short_description": self.short_description,
            "price": self.price,
            "discount_price": self.discount_price,
            "final_price": self.final_price,
            "unit": self.unit,
            "stock": self.stock,
            "image": self.image,
            "image_status": self.image_status,
            "additional_images": self.extra_images(),
            "material": self.material,
            "size": self.size,
            "color": self.color,
            "weight": self.weight,
            "finish": self.finish,
            "thickness": self.thickness,
            "pieces_per_box": self.pieces_per_box,
            "coverage": self.coverage,
            "availability": self.availability,
            "featured": self.featured,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }