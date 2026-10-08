"""
migrate.py
----------
Safe, non-destructive schema upgrade for SQLite/PostgreSQL.
db.create_all() never adds columns to existing tables, so new columns are added
with ALTER TABLE ... ADD COLUMN (only when missing). A dated SQLite backup is
taken first. Nothing is ever dropped or rewritten.
"""
import os
import shutil
from datetime import datetime

from sqlalchemy import inspect, text

from database.db import db

NEW_PRODUCT_COLUMNS = (
    ("image_status", "VARCHAR(20) DEFAULT 'missing'"),
    ("image_updated_at", "DATETIME"),
    ("image_provider", "VARCHAR(80)"),
    ("image_error", "VARCHAR(255)"),
)


def _backup_sqlite():
    url = db.engine.url
    if url.get_backend_name() != "sqlite" or not url.database or not os.path.isfile(url.database):
        return None
    dest = f"{url.database}.bak-{datetime.now():%Y%m%d-%H%M%S}"
    shutil.copy2(url.database, dest)
    return dest


def ensure_columns(log=print):
    """Add missing Image Agent columns. Returns the list of columns added."""
    have = {c["name"] for c in inspect(db.engine).get_columns("products")}
    missing = [(c, ddl) for c, ddl in NEW_PRODUCT_COLUMNS if c not in have]
    if not missing:
        return []
    backup = _backup_sqlite()
    if backup:
        log(f"  database backup: {os.path.basename(backup)}")
    for col, ddl in missing:
        db.session.execute(text(f"ALTER TABLE products ADD COLUMN {col} {ddl}"))
        log(f"  + added column products.{col}")
    db.session.commit()
    return [c for c, _ in missing]
