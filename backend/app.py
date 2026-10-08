"""
app.py
------
Main entry point. Creates the Flask app, registers all blueprints and
serves the frontend + admin static files.

Run with:  python app.py
"""
import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

from config import Config, BASE_DIR
from database.db import db

# -------- paths --------
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
ADMIN_DIR = os.path.join(PROJECT_ROOT, "admin")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    # Allow the frontend to call the API (with credentials, so session cookies work)
    CORS(app, supports_credentials=True)

    db.init_app(app)

    # ---- import models so tables are registered ----
    from models import (  # noqa: F401
        User, Category, Product, Customer, Order, OrderItem,
        Inquiry, ContactMessage, Setting, GalleryImage,
        AIConversation, AIMessage,
    )

    # ---- blueprints ----
    from routes.auth import auth_bp
    from routes.categories import categories_bp
    from routes.products import products_bp
    from routes.orders import orders_bp
    from routes.inquiries import inquiries_bp
    from routes.contact import contact_bp
    from routes.gallery import gallery_bp
    from routes.settings import settings_bp
    from routes.upload import upload_bp
    from routes.stats import stats_bp
    from routes.ai import ai_bp
    from routes.image_agent import image_agent_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(inquiries_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(image_agent_bp)

    # create upload folders + database tables on first run
    for sub in ("products", "categories", "gallery"):
        os.makedirs(os.path.join(UPLOAD_DIR, sub), exist_ok=True)

    with app.app_context():
        db.create_all()

    # ================================================================
    # STATIC FILE SERVING
    # ----------------------------------------------------------------
    # The rule:
    #   /admin/...   -> served from the admin/ folder
    #   /uploads/... -> served from backend/uploads/
    #   everything else -> served from the frontend/ folder
    #
    # This prevents admin pages like "products.html" from shadowing
    # the frontend "products.html" file.
    # ================================================================

    # Home page
    @app.get("/")
    def home():
        return send_from_directory(FRONTEND_DIR, "index.html")

    # Admin root -> login page
    @app.get("/admin")
    @app.get("/admin/")
    def admin_index():
        return send_from_directory(ADMIN_DIR, "login.html")

    # Any file inside admin/ (login.html, dashboard.html, css/admin.css, js/admin.js ...)
    @app.get("/admin/<path:path>")
    def admin_files(path):
        full = os.path.join(ADMIN_DIR, path)
        if not os.path.isfile(full):
            return jsonify({"success": False, "message": "File not found"}), 404
        return send_from_directory(ADMIN_DIR, path)

    # Uploaded images (products, categories, gallery)
    @app.get("/uploads/<path:path>")
    def uploaded_file(path):
        return send_from_directory(UPLOAD_DIR, path)

    # Everything else -> frontend folder
    @app.get("/<path:path>")
    def frontend_files(path):
        full = os.path.join(FRONTEND_DIR, path)
        if not os.path.isfile(full):
            return jsonify({"success": False, "message": "File not found"}), 404
        return send_from_directory(FRONTEND_DIR, path)

    # ================================================================
    # ERROR HANDLERS
    # ================================================================

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Not found"}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"success": False, "message": "File is too large (max 5 MB)"}), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "message": "Server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    print("\n  M Hardware & Sanitary is running")
    print("  Website : http://127.0.0.1:5000/")
    print("  Admin   : http://127.0.0.1:5000/admin/")
    print("  Login   : admin / admin123\n")
    app.run(debug=True, port=5000)