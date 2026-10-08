"""
ai_service.py
-------------
A safe, rule-based assistant that answers ONLY using data from the
database. It never invents prices, stock or specifications.

If AI_API_KEY is set you could later swap `generate_reply` to call a
real LLM — but the database lookup step stays the same, and this
offline fallback always works.
"""
import re
from sqlalchemy import or_
from models import Product, Category, Setting

GREETINGS = ("hi", "hello", "hey", "namaste", "good morning", "good evening")
THANKS = ("thanks", "thank you", "ok thanks", "great")

STOPWORDS = {
    "i", "need", "want", "a", "an", "the", "for", "of", "to", "please",
    "can", "you", "show", "me", "some", "any", "is", "are", "do", "have",
    "what", "which", "best", "good", "in", "on", "my", "we", "with", "and",
    "price", "cost", "rate", "how", "much", "sell", "products", "product",
    "available", "stock", "your", "shop", "store", "got", "looking", "buy",
}

CONTACT_WORDS = ("contact", "phone", "call", "address", "location", "timing",
                 "opening hours", "where is", "whatsapp", "email")
SELL_PHRASES = ("what products", "what do you sell", "what you sell", "what all",
                "categories", "what can i buy", "what items")
CONTACT_HINT = "For anything not listed here, please contact the shop directly."


def _stem(w):
    """Very small singulariser: pipes -> pipe, tiles -> tile."""
    if len(w) > 3 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _keywords(text):
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [_stem(w) for w in words if w not in STOPWORDS and len(w) > 1]


def _cat_names(p):
    """Category name plus parent name, lower-cased."""
    names = []
    if p.category:
        names.append(p.category.name.lower())
        if p.category.parent:
            names.append(p.category.parent.name.lower())
    return " ".join(names)


def find_products(text, limit=6):
    """Products whose name/brand/category contain ALL words; fall back to ANY word."""
    words = _keywords(text)
    if not words:
        return []

    candidates = Product.query.all()

    def haystack(p):
        return " ".join(filter(None, [p.name, p.brand, p.material, p.color, p.size, p.sku,
                                      p.short_description, _cat_names(p)])).lower()

    scored = []
    for p in candidates:
        h = haystack(p)
        hits = sum(1 for w in words if w in h)
        if hits:
            name_hits = sum(1 for w in words if w in p.name.lower())
            scored.append((hits == len(words), hits, name_hits, p))
    scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)

    # keep only full matches when there are any
    if scored and scored[0][0]:
        scored = [t for t in scored if t[0]]
    return [t[3] for t in scored[:limit]]


def _top_categories():
    return Category.query.filter_by(parent_id=None, is_active=True).order_by(Category.sort_order).all()


def generate_reply(message):
    """
    Returns a dict:
        { "reply": str, "products": [product_dict, ...] }
    """
    text = (message or "").strip()
    low = text.lower()

    if not text:
        return {"reply": "Please type your question and I'll help you find the right product.",
                "products": []}

    # ---- greetings ----
    if any(low.startswith(g) for g in GREETINGS) and len(low) < 25:
        return {
            "reply": ("Hello! 👋 I'm the M Hardware assistant. "
                      "Tell me what you're looking for — for example "
                      "\"1 inch CPVC pipe\" or \"bathroom tiles\"."),
            "products": [],
        }

    # ---- thanks ----
    if any(t in low for t in THANKS):
        return {"reply": "Happy to help! 😊 Anything else you need?", "products": []}

    # ---- what do you sell ----
    if any(k in low for k in SELL_PHRASES):
        names = [c.name for c in _top_categories()]
        if names:
            return {"reply": "We sell: " + ", ".join(names) +
                             ". Ask me about any of them, e.g. \"show me tiles\".",
                    "products": []}

    # ---- shop contact info ----
    if any(k in low for k in CONTACT_WORDS):
        phone = Setting.get("phone", "")
        wa = Setting.get("whatsapp", "")
        addr = Setting.get("address", "")
        hours = Setting.get("opening_hours", "")
        return {
            "reply": (f"You can reach us at 📞 {phone} or on WhatsApp {wa}.\n"
                      f"Address: {addr}\nOpening hours: {hours}"),
            "products": [],
        }

    words = _keywords(text)
    is_price = any(k in low for k in ("price", "cost", "rate", "how much"))

    # ---- bathroom tiles etc: product name + category/word combos handled by find_products;
    #      if a "tile" request has no full match, fall back to all tiles ----
    products = find_products(text)
    if not products and "tile" in words:
        products = [p for p in Product.query.all()
                    if "tile" in p.name.lower() or "tile" in _cat_names(p)][:6]

    if products:
        if is_price:
            lines = []
            for p in products[:4]:
                price = f"₹{p.final_price:,.0f}" if p.final_price is not None else "not listed"
                lines.append(f"• {p.name}: {price} per {p.unit or 'piece'}")
            return {"reply": "Here are the prices in our store:\n" + "\n".join(lines),
                    "products": [p.to_dict() for p in products]}
        return {
            "reply": (f"I found {len(products)} matching product(s) in our store. "
                      "Tap a card to see full details."),
            "products": [p.to_dict() for p in products],
        }

    # ---- nothing found ----
    return {
        "reply": ("I couldn't find that in our store catalog. "
                  "Try a different word (for example \"tap\", \"pipe\", \"tile\"). "
                  + CONTACT_HINT),
        "products": [],
    }
