"""
Category
--------
Self-referencing table.
A row with parent_id = NULL  -> top-level category (e.g. "Tiles")
A row with parent_id = 5     -> subcategory of category 5 (e.g. "Floor Tiles")

This gives unlimited nesting with ONE table — easier than two tables.
"""
from datetime import datetime
from database.db import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Self-referencing relationship: children <-> parent
    children = db.relationship(
        "Category",
        backref=db.backref("parent", remote_side=[id]),
        lazy="select",
        cascade="all",
    )

    products = db.relationship("Product", backref="category", lazy="select")

    def to_dict(self, with_children=False):
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "image": self.image,
            "parent_id": self.parent_id,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "featured": bool(self.featured),
        }
        if with_children:
            data["children"] = [
                c.to_dict() for c in sorted(self.children, key=lambda x: x.sort_order or 0)
            ]
            # count products in this category and its direct subcategories
            data["product_count"] = len(self.products) + sum(len(c.products) for c in self.children)
        return data