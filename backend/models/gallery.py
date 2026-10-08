"""Gallery images managed from the admin panel."""
from datetime import datetime
from database.db import db


class GalleryImage(db.Model):
    __tablename__ = "gallery"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    category = db.Column(db.String(80), default="Shop")   # Shop / Sanitary / Tiles / Hardware …
    image = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "image": self.image,
        }