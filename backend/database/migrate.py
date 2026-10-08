"""
migrate.py
----------
Safe, non-destructive schema upgrade for SQLite/PostgreSQL.
db.create_all() never adds columns to existing tables, so new columns are added
with ALTER TABLE ... ADD COLUMN (only when missing). A dated SQLite backup is
taken first. Nothing is ever dropped or rewritten.
Runs automatically on app start (see app.py) and from seed/generate scripts.
"""
import os
import shutil
from datetime import datetime

from sqlalchemy import inspect, text

from database.db import db

NEW_COLUMNS = {
    "products": (
        ("image_status", "VARCHAR(20) DEFAULT 'missing'"),
        ("image_updated_at", "TIMESTAMP"),
        ("image_provider", "VARCHAR(80)"),
        ("image_error", "VARCHAR(255)"),
        ("min_stock", "INTEGER DEFAULT 5"),
    ),
    "categories": (
        ("featured", "BOOLEAN DEFAULT FALSE"),
    ),
    "customers": (
        ("password_hash", "VARCHAR(255)"),
        ("is_active", "BOOLEAN DEFAULT TRUE"),
        ("last_login_at", "TIMESTAMP"),
        ("reset_token_hash", "VARCHAR(255)"),
        ("reset_expires_at", "TIMESTAMP"),
    ),
    "orders": (
        ("order_number", "VARCHAR(40)"),
        ("access_token", "VARCHAR(64)"),
        ("order_type", "VARCHAR(20) DEFAULT 'delivery'"),
        ("payment_method", "VARCHAR(20) DEFAULT 'cod'"),
        ("payment_status", "VARCHAR(20) DEFAULT 'pending'"),
        ("subtotal", "FLOAT DEFAULT 0"),
        ("discount", "FLOAT DEFAULT 0"),
        ("tax", "FLOAT DEFAULT 0"),
        ("delivery_fee", "FLOAT DEFAULT 0"),
        ("grand_total", "FLOAT DEFAULT 0"),
        ("shipping_name", "VARCHAR(150)"),
        ("shipping_phone", "VARCHAR(30)"),
        ("shipping_email", "VARCHAR(150)"),
        ("shipping_address", "TEXT"),
        ("shipping_city", "VARCHAR(80)"),
        ("shipping_state", "VARCHAR(80)"),
        ("shipping_pincode", "VARCHAR(12)"),
        ("admin_note", "TEXT"),
        ("updated_at", "TIMESTAMP"),
    ),
    "order_items": (
        ("sku", "VARCHAR(80)"),
        ("unit", "VARCHAR(40)"),
        ("image", "VARCHAR(255)"),
        ("mrp", "FLOAT"),
        ("discount", "FLOAT DEFAULT 0"),
        ("subtotal", "FLOAT"),
    ),
}

INDEXES = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_orders_order_number ON orders (order_number)",
)


def _backup_sqlite():
    url = db.engine.url
    if url.get_backend_name() != "sqlite" or not url.database or not os.path.isfile(url.database):
        return None
    dest = f"{url.database}.bak-{datetime.now():%Y%m%d-%H%M%S}"
    shutil.copy2(url.database, dest)
    return dest


def ensure_columns(log=print):
    """Add missing columns + indexes and repair known bad data. Returns the columns added."""
    insp = inspect(db.engine)
    tables = set(insp.get_table_names())
    missing = []
    for table, cols in NEW_COLUMNS.items():
        if table not in tables:
            continue          # brand-new table: db.create_all() already made it complete
        have = {c["name"] for c in insp.get_columns(table)}
        missing += [(table, c, ddl) for c, ddl in cols if c not in have]

    if missing:
        backup = _backup_sqlite()
        if backup:
            log(f"  database backup: {os.path.basename(backup)}")
        for table, col, ddl in missing:
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
            log(f"  + added column {table}.{col}")
        db.session.commit()

    for ddl in INDEXES:
        db.session.execute(text(ddl))
    _repair_data()
    db.session.commit()
    return [f"{t}.{c}" for t, c, _ in missing]


def _repair_data():
    """Idempotent fixes for data written by earlier versions."""
    # old order statuses -> new names
    for old, new in (("new", "pending"), ("quoted", "pending"), ("done", "delivered")):
        db.session.execute(text("UPDATE orders SET status = :n WHERE status = :o"), {"n": new, "o": old})
    db.session.execute(text("UPDATE orders SET grand_total = total "
                            "WHERE (grand_total IS NULL OR grand_total = 0) AND total > 0"))
    # a setting saved with a broken encoding (U+FFFD where an en dash was)
    db.session.execute(text("UPDATE settings SET value = REPLACE(value, :bad, :good) "
                            "WHERE value LIKE :pat"),
                       {"bad": "�", "good": "–", "pat": "%�%"})
