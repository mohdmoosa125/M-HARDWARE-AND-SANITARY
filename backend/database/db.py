"""
db.py
-----
Creates the single SQLAlchemy object that every model imports.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()