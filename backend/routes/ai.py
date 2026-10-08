"""AI assistant endpoint."""
from flask import Blueprint, request, session
from database.db import db
from models import AIConversation, AIMessage
from services.ai_service import generate_reply
from utils import ok, fail
import uuid

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@ai_bp.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()[:500]
    if not message:
        return fail("Message is required")

    # keep a session key so we can group messages into a conversation
    key = data.get("session_key") or session.get("ai_session")
    if not key:
        key = uuid.uuid4().hex
        session["ai_session"] = key

    conversation = AIConversation.query.filter_by(session_key=key).first()
    if not conversation:
        conversation = AIConversation(session_key=key)
        db.session.add(conversation)
        db.session.flush()

    # store the customer's message
    db.session.add(AIMessage(conversation_id=conversation.id, role="user", content=message))

    # build the answer from the database
    context = data.get("context") if isinstance(data.get("context"), dict) else {}
    result = generate_reply(message, context)

    db.session.add(AIMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=result["reply"],
    ))
    db.session.commit()

    result["session_key"] = key
    return ok(result)