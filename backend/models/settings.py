"""
Setting
-------
A tiny key/value table. This is what makes phone numbers configurable
from the admin panel instead of being hard-coded in HTML.
"""
from database.db import db


class Setting(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text)

    @staticmethod
    def get(key, default=""):
        row = Setting.query.filter_by(key=key).first()
        return row.value if row and row.value is not None else default

    @staticmethod
    def set(key, value):
        row = Setting.query.filter_by(key=key).first()
        if row:
            row.value = value
        else:
            db.session.add(Setting(key=key, value=value))
        db.session.commit()

    @staticmethod
    def all_as_dict():
        return {s.key: s.value for s in Setting.query.all()}