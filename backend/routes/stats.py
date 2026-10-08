"""Dashboard statistics for the admin panel."""
from flask import Blueprint
from database.db import db
from models import Product, Category, Order, Customer, Inquiry, ContactMessage
from utils import ok, admin_required

stats_bp = Blueprint("stats", __name__, url_prefix="/api/admin")


@stats_bp.get("/stats")
@admin_required
def dashboard_stats():
    low_stock = Product.query.filter(Product.stock <= 3).limit(10).all()
    featured = Product.query.filter_by(featured=True).limit(10).all()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    recent_inquiries = Inquiry.query.order_by(Inquiry.created_at.desc()).limit(5).all()

    return ok({
        "total_products": Product.query.count(),
        "total_categories": Category.query.count(),
        "total_orders": Order.query.count(),
        "total_customers": Customer.query.count(),
        "total_inquiries": Inquiry.query.count(),
        "total_messages": ContactMessage.query.count(),
        "low_stock": [p.to_dict() for p in low_stock],
        "featured": [p.to_dict() for p in featured],
        "recent_orders": [o.to_dict() for o in recent_orders],
        "recent_inquiries": [i.to_dict() for i in recent_inquiries],
    })