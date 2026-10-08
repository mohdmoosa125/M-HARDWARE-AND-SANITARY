"""Stores AI chat history so the admin can review what customers ask."""
from datetime import datetime
from database.db import db


class AIConversation(db.Model):
    __tablename__ = "ai_conversations"

    id = db.Column(db.Integer, primary_key=True)
    session_key = db.Column(db.String(80), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    messages = db.relationship(
        "AIMessage", backref="conversation", lazy="select", cascade="all, delete-orphan"
    )


class AIMessage(db.Model):
    __tablename__ = "ai_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("ai_conversations.id"))
    role = db.Column(db.String(20))          # "user" or "assistant"
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)