"""
Import every model here so that:
    from models import *
gives you all of them, and SQLAlchemy knows about every table.
"""
from models.user import User
from models.category import Category
from models.product import Product
from models.customer import Customer
from models.order import Order, OrderItem
from models.inquiry import Inquiry, ContactMessage
from models.settings import Setting
from models.gallery import GalleryImage
from models.ai import AIConversation, AIMessage

__all__ = [
    "User", "Category", "Product", "Customer",
    "Order", "OrderItem", "Inquiry", "ContactMessage",
    "Setting", "GalleryImage", "AIConversation", "AIMessage",
]