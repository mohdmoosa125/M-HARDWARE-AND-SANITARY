"""
app.py
------
Main entry point. Creates the Flask app, registers all blueprints and
serves the frontend + admin static files.

Run with:  python app.py
"""
import html
import os
import re
from flask import Flask, send_from_directory, jsonify, request, Response

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
    from flask_cors import CORS
    CORS(app, supports_credentials=True)

    db.init_app(app)

    # ---- import models so tables are registered ----
    import models  # noqa: F401

    # ---- blueprints ----
    from routes.auth import auth_bp
    from routes.account import account_bp
    from routes.admin import admin_bp
    from routes.categories import categories_bp
    from routes.products import products_bp
    from routes.orders import orders_bp
    from routes.invoices import invoices_bp
    from routes.inquiries import inquiries_bp
    from routes.contact import contact_bp
    from routes.gallery import gallery_bp
    from routes.settings import settings_bp
    from routes.upload import upload_bp
    from routes.stats import stats_bp
    from routes.ai import ai_bp
    from routes.image_agent import image_agent_bp

    for bp in (auth_bp, account_bp, admin_bp, categories_bp, products_bp, orders_bp, invoices_bp,
               inquiries_bp, contact_bp, gallery_bp, settings_bp, upload_bp, stats_bp, ai_bp,
               image_agent_bp):
        app.register_blueprint(bp)

    # create upload folders + database tables on first run, then upgrade old schemas safely
    for sub in ("products", "categories", "gallery", "references"):
        os.makedirs(os.path.join(UPLOAD_DIR, sub), exist_ok=True)

    with app.app_context():
        db.create_all()
        from database.migrate import ensure_columns
        ensure_columns(log=lambda msg: app.logger.info(msg))

    # ================================================================
    # STATIC FILE SERVING
    # ----------------------------------------------------------------
    #   /admin/...          -> admin/ folder
    #   /uploads/...        -> backend/uploads/
    #   /products/<slug>    -> product page with SEO tags for that product
    #   everything else     -> frontend/ folder
    # ================================================================

    @app.get("/")
    def home():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/admin")
    @app.get("/admin/")
    def admin_index():
        return send_from_directory(ADMIN_DIR, "login.html")

    @app.get("/admin/<path:path>")
    def admin_files(path):
        full = os.path.join(ADMIN_DIR, path)
        if not os.path.isfile(full):
            return jsonify({"success": False, "message": "File not found"}), 404
        return send_from_directory(ADMIN_DIR, path)

    @app.get("/uploads/<path:path>")
    def uploaded_file(path):
        return send_from_directory(UPLOAD_DIR, path, max_age=86400)

    @app.get("/products/<slug>")
    def product_page(slug):
        """Product detail page; title/description/Open Graph filled in server-side for SEO."""
        from models import Product
        with open(os.path.join(FRONTEND_DIR, "product-details.html"), encoding="utf-8") as f:
            page = f.read()
        p = Product.query.filter_by(slug=slug).first()
        if not p:
            return Response(page, status=404, mimetype="text/html")
        from services.store_config import all_settings
        biz = all_settings().get("business_name", "")
        title = html.escape(f"{p.name} | {biz}")
        desc = html.escape(re.sub(r"\s+", " ", p.short_description or p.description or
                                  f"{p.name} — {p.category.name if p.category else 'product'} at {biz}, Bhopal.")[:160])
        url = html.escape(request.base_url)
        img = html.escape(request.host_url.rstrip("/") + p.image) if p.image else ""
        meta = (f'<meta name="description" content="{desc}">'
                f'<link rel="canonical" href="{url}">'
                f'<meta property="og:type" content="product"><meta property="og:title" content="{title}">'
                f'<meta property="og:description" content="{desc}"><meta property="og:url" content="{url}">'
                + (f'<meta property="og:image" content="{img}">' if img else ""))
        page = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", page, count=1, flags=re.S)
        page = re.sub(r'<meta name="description"[^>]*>', "", page, count=1)
        page = re.sub(r'<meta property="og:[^"]*"[^>]*>\s*', "", page)
        page = page.replace("</head>", meta + "</head>", 1)
        return Response(page, mimetype="text/html")

    @app.get("/sitemap.xml")
    def sitemap():
        from models import Product
        base = request.host_url.rstrip("/")
        pages = ["/", "/products.html", "/categories.html", "/gallery.html", "/about.html", "/contact.html"]
        urls = [base + p for p in pages] + [f"{base}/products/{s}" for (s,) in
                                             Product.query.with_entities(Product.slug).all() if s]
        body = "".join(f"<url><loc>{html.escape(u)}</loc></url>" for u in urls)
        return Response('<?xml version="1.0" encoding="UTF-8"?>'
                        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>',
                        mimetype="application/xml")

    @app.get("/robots.txt")
    def robots():
        return Response(f"User-agent: *\nDisallow: /admin/\nDisallow: /api/\nDisallow: /invoice/\n"
                        f"Sitemap: {request.host_url}sitemap.xml\n", mimetype="text/plain")

    @app.get("/<path:path>")
    def frontend_files(path):
        full = os.path.join(FRONTEND_DIR, path)
        if not os.path.isfile(full):
            if path.endswith(".html") or "." not in path.rsplit("/", 1)[-1]:
                return send_from_directory(FRONTEND_DIR, "404.html"), 404
            return jsonify({"success": False, "message": "File not found"}), 404
        return send_from_directory(FRONTEND_DIR, path)

    # ================================================================
    # ERROR HANDLERS — never leak stack traces
    # ================================================================

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Not found"}), 404

    @app.errorhandler(405)
    def not_allowed(e):
        return jsonify({"success": False, "message": "Method not allowed"}), 405

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"success": False, "message": "File is too large (max 5 MB)"}), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "message": "Something went wrong. Please try again."}), 500

    if app.config["SECRET_KEY"] == "dev-secret-key-change-me":
        app.logger.warning("SECRET_KEY is not set in backend/.env — using an insecure development key.")

    return app


app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    print("\n  M Hardware & Sanitary is running")
    print("  Website : http://127.0.0.1:5000/")
    print("  Admin   : http://127.0.0.1:5000/admin/\n")
    app.run(debug=debug, port=int(os.getenv("PORT", "5000")))
