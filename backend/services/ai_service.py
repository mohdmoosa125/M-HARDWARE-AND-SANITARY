"""
ai_service.py
-------------
A safe, rule-based shopping assistant + agent that answers ONLY using data
from the database. It never invents products, prices, stock or specs.

Abilities: product search, budget filtering, comparison, tile quantity
estimates, general installation guidance (clearly labelled), and "agent"
cart proposals. The agent never changes anything itself: it returns an
`action` the customer must confirm in the chat before the browser adds it
to the cart. It never places orders or takes payment.

If AI_API_KEY is set you could later swap the wording step to a real LLM —
the database lookup + confirmation steps stay the same.
"""
import math
import re

from models import Product, Category, Setting

GREETINGS = ("hi", "hello", "hey", "namaste", "good morning", "good evening")
THANKS = ("thanks", "thank you", "ok thanks", "great")

STOPWORDS = {
    "i", "need", "want", "a", "an", "the", "for", "of", "to", "please",
    "can", "you", "show", "me", "some", "any", "is", "are", "do", "have",
    "what", "which", "best", "good", "in", "on", "my", "we", "with", "and",
    "price", "cost", "rate", "how", "much", "sell", "products", "product",
    "available", "stock", "your", "shop", "store", "got", "looking", "buy",
    "under", "below", "less", "than", "within", "upto", "up", "rs", "inr", "budget",
    "above", "over", "more", "between", "add", "cart", "one", "it", "that", "this",
    "should", "find", "get", "suggest", "recommend", "cheap", "cheapest", "affordable",
    "around", "about", "max", "maximum", "minimum", "min", "least", "also", "them",
    "compare", "vs", "versus", "difference", "between", "or", "bathroom's", "would", "like",
    "order", "purchase", "item", "items", "quantity", "qty", "nos", "pcs", "pieces", "piece",
}

# a request word -> words that count as a match in product text
SYNONYMS = {
    "fitting": ("fitting", "tap", "mixer", "shower", "cock", "faucet", "valve"),
    "faucet": ("faucet", "tap", "mixer", "cock"),
    "bathroom": ("bathroom", "sanitary", "shower", "basin", "toilet", "tap", "mixer"),
    "toilet": ("toilet", "commode", "wc", "closet"),
    "commode": ("toilet", "commode", "closet"),
    "wc": ("toilet", "commode", "closet"),
    "sink": ("sink", "basin"),
    "washbasin": ("basin",),
    "drill": ("drill",),
    "plumbing": ("pipe", "elbow", "tee", "coupler", "fitting", "valve", "socket"),
}

CONTACT_WORDS = ("contact", "phone", "call", "address", "location", "timing",
                 "opening hours", "where is", "whatsapp", "email")
SELL_PHRASES = ("what products", "what do you sell", "what you sell", "what all",
                "categories", "what can i buy", "what items")
CONTACT_HINT = "For anything not listed here, please contact the shop directly."
SIZE_UNITS = ("inch", "in", "mm", "cm", "ft", "feet", "foot", "kg", "m", "meter", "metre",
              "litre", "liter", "l", "ml", "hp", "w", "watt", "sq", "x", '"')
QTY_UNITS = r"(?:bags?|pcs|pieces?|boxes?|nos?|units?|sets?|lengths?|packets?|packs?|rolls?|bottles?)"


# ================================================================ helpers

def _stem(w):
    """Very small singulariser: pipes -> pipe, tiles -> tile."""
    if len(w) > 3 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("es") and w[-3] in "sxz":
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _keywords(text):
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [_stem(w) for w in words if w not in STOPWORDS and len(w) > 1 and not w.isdigit()]


def _cat_names(p):
    """Category name plus parent name, lower-cased."""
    names = []
    if p.category:
        names.append(p.category.name.lower())
        if p.category.parent:
            names.append(p.category.parent.name.lower())
    return " ".join(names)


def _haystack(p):
    return " ".join(filter(None, [p.name, p.brand, p.material, p.color, p.size, p.sku, p.unit,
                                  p.short_description, _cat_names(p)])).lower()


def _hit(word, hay):
    return any(s in hay for s in SYNONYMS.get(word, (word,)))


def _price(p):
    return p.final_price or 0


def money(v):
    return f"₹{v:,.0f}" if float(v).is_integer() else f"₹{v:,.2f}"


def find_products(text, limit=6, max_price=None, min_price=None):
    """Products whose text matches ALL request words (with synonyms); fall back to ANY word.
    Optional budget filter on the price the customer pays."""
    words = _keywords(text)
    if not words:
        return []
    scored = []
    for p in Product.query.all():
        price = _price(p)
        if max_price is not None and price > max_price:
            continue
        if min_price is not None and price < min_price:
            continue
        h = _haystack(p)
        hits = sum(1 for w in words if _hit(w, h))
        if hits:
            name_hits = sum(1 for w in words if _hit(w, p.name.lower()))
            scored.append((hits == len(words), hits, name_hits, p))
    scored.sort(key=lambda t: (t[0], t[1], t[2], t[3].in_stock, bool(t[3].featured)), reverse=True)
    if scored and scored[0][0]:
        scored = [t for t in scored if t[0]]       # keep only full matches when there are any
    return [t[3] for t in scored[:limit]]


def rank(products, budget=None):
    """Best pick first: in stock, featured, discounted, and closest to (but within) budget."""
    def score(p):
        s = 0.0
        s += 10 if p.in_stock else -20
        s += 2 if p.featured else 0
        s += min(p.discount_percent, 40) / 10
        if budget:
            s += 3 * (_price(p) / budget)          # spend the budget on the better item
        return s
    return sorted(products, key=score, reverse=True)


def _num(s):
    return float(s.replace(",", ""))


def parse_budget(low):
    """-> (min_price, max_price) from phrases like 'under ₹5000', 'between 500 and 2000', 'below 5k'."""
    n = r"(?:rs\.?|₹|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|thousand)?(?![\d])"
    def val(m, i=1):
        v = _num(m.group(i))
        return v * 1000 if m.group(i + 1) else v
    def not_size(m):
        rest = low[m.end():].lstrip()
        return not re.match(r"(?:%s)\b" % "|".join(map(re.escape, SIZE_UNITS)), rest)

    m = re.search(r"\bbetween\s*" + n + r"\s*(?:and|-|to)\s*" + n, low)
    if m:
        a, b = val(m, 1), val(m, 3)
        return min(a, b), max(a, b)
    lo = hi = None
    m = re.search(r"(?:\b(?:under|below|less than|within|upto|up to|max(?:imum)?|not more than|budget(?: of| is)?)|[<≤])\s*" + n, low)
    if m and not_size(m):
        hi = val(m)
    m = re.search(r"\b(?:above|over|more than|min(?:imum)?|at least)\s*" + n, low)
    if m and not_size(m):
        lo = val(m)
    return lo, hi


def parse_quantity(low):
    m = re.search(r"\b(\d{1,4})\s*" + QTY_UNITS + r"\b", low)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(?:need|want|buy|add|order|get)\s+(\d{1,4})\s+(?!(?:%s)\b)[a-z]" %
                  "|".join(map(re.escape, SIZE_UNITS)), low)
    return int(m.group(1)) if m else None


def _line(p):
    stock = "in stock" if p.in_stock else "out of stock"
    return f"• {p.name} — {money(_price(p))} per {p.unit or 'piece'} ({stock})"


def _cart_action(p, qty):
    qty = max(1, qty or 1)
    if not p.in_stock:
        return None
    qty = min(qty, p.stock or 0)
    total = _price(p) * qty
    return {
        "type": "add_to_cart", "product_id": p.id, "quantity": qty, "name": p.name,
        "unit": p.unit or "piece", "unit_price": _price(p), "total": round(total, 2),
        "stock": p.stock,
        "label": f"Add {qty} × {p.name} to cart ({money(total)})",
    }


def _result(reply, products=(), action=None, **extra):
    out = {"reply": reply, "products": [p.to_dict() for p in products]}
    if action:
        out["action"] = action
    out.update(extra)
    return out


# ================================================================ guidance

GUIDES = [
    (("pipe",), ("bathroom", "hot", "which", "best", "type", "difference", "plumbing"),
     "General guidance (please confirm with your plumber):\n"
     "• CPVC — hot and cold water supply lines (geysers, bathrooms, kitchens).\n"
     "• UPVC — cold water supply, including outdoor/overhead lines.\n"
     "• PVC / SWR — drainage and waste lines.\n"
     "Here are the matching pipes we stock:", "cpvc upvc pvc pipe"),
    (("basin",), ("fitting", "need", "install", "accessor", "required", "what"),
     "To install a wash basin you usually need (general guidance):\n"
     "• a pillar tap or basin mixer\n• angle valve(s) and connection pipe(s)\n"
     "• a waste coupling and bottle trap\n• wall plugs/screws or a basin bracket\n"
     "Here is what we have in stock for that:", "tap mixer angle cock connection waste trap"),
    (("toilet", "commode", "wc"), ("fitting", "need", "install", "accessor", "required", "what"),
     "A western toilet installation typically needs (general guidance):\n"
     "• the toilet + seat cover, and a cistern if it is not a one-piece model\n"
     "• an angle cock and connection pipe\n• a health faucet\n"
     "Matching items in our store:", "toilet cistern angle cock connection health faucet"),
    (("drill",), ("which", "best", "should", "buy", "suggest", "choose"),
     "Choosing a drill (general guidance):\n"
     "• Wood/metal and light household work: a standard 10–13 mm drill.\n"
     "• Brick or concrete: an impact/hammer drill with masonry bits.\n"
     "• Frequent heavy concrete work: a rotary hammer.\n"
     "Drills we currently stock:", "drill"),
]


def _guidance(low, words):
    for subjects, triggers, text, search in GUIDES:
        if any(s in words for s in subjects) and any(t in low for t in triggers):
            found = []
            for term in search.split():
                for p in find_products(term, limit=3):
                    if p not in found:
                        found.append(p)
            found = rank(found)[:6]
            reply = text if found else text.rsplit("\n", 1)[0] + "\nWe don't have matching items listed right now. " + CONTACT_HINT
            return _result(reply, found)
    return None


# ================================================================ tiles

def _area_sqft(low):
    """Room area from '10x12 ft', '10 by 12 feet', '120 sq ft', '3x4 m', '12 sqm'."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*ft|sqft|square\s*feet|sft)", low)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*m|sqm|square\s*met(?:er|re)s?)", low)
    if m:
        return float(m.group(1)) * 10.7639
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:x|\*|by)\s*(\d+(?:\.\d+)?)\s*(ft|feet|foot|m|meter|metre|mtr)?\b(?!\s*mm)", low)
    if m and not re.match(r"\s*(?:mm|cm)", low[m.end():]):
        a, b = float(m.group(1)), float(m.group(2))
        unit = m.group(3) or "ft"
        area = a * b
        return area * 10.7639 if unit.startswith("m") else area
    return None


def _tile_sqft(size):
    """'600x600 mm' -> 3.875 sq ft per tile."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(mm|cm|in|inch|ft)?", size or "", re.I)
    if not m:
        return None
    a, b, unit = float(m.group(1)), float(m.group(2)), (m.group(3) or "mm").lower()
    to_ft = {"mm": 1 / 304.8, "cm": 1 / 30.48, "in": 1 / 12, "inch": 1 / 12, "ft": 1}[unit]
    return a * to_ft * b * to_ft


def _tiles(low, words):
    if "tile" not in words:
        return None
    area = _area_sqft(low)
    if not area:
        if any(k in low for k in ("how many", "calculate", "quantity", "estimate")):
            return _result("Tell me the room size and I'll estimate the tiles — for example "
                           "\"how many tiles for a 10x12 ft floor\" or \"tiles for 120 sq ft\".")
        return None
    need = area * 1.10           # 10% for cutting and breakage
    kind = [w for w in words if w in ("floor", "wall", "bathroom", "kitchen", "designer")]
    candidates = rank(find_products(" ".join(kind + ["tile"]), limit=6) or find_products("tile", limit=6))
    lines, best, best_boxes = [], None, None
    for p in candidates:
        per_tile = _tile_sqft(p.size)
        if not per_tile:
            continue
        tiles = math.ceil(need / per_tile)
        if p.pieces_per_box:
            boxes = math.ceil(tiles / p.pieces_per_box)
            lines.append(f"• {p.name} ({p.size}): about {tiles} tiles = {boxes} box(es) × "
                         f"{money(_price(p))} ≈ {money(boxes * _price(p))}")
            if best is None and p.in_stock:
                best, best_boxes = p, boxes
        else:
            lines.append(f"• {p.name} ({p.size}): about {tiles} tiles "
                         f"(pieces per box not listed — the store will confirm the box count)")
    reply = (f"Area ≈ {area:,.0f} sq ft. Adding 10% for cutting and breakage, plan for about "
             f"{need:,.0f} sq ft of tiles.")
    if lines:
        reply += "\n" + "\n".join(lines)
    else:
        reply += " I couldn't find tiles with a listed size to calculate exact counts. " + CONTACT_HINT
    action = _cart_action(best, best_boxes) if best else None
    return _result(reply, candidates[:4], action)


# ================================================================ compare

def _compare(text, low):
    if not re.search(r"\b(compare|vs|versus|difference between)\b", low):
        return None
    body = re.sub(r"\b(compare|difference between|please|the|these|two)\b", " ", low)
    parts = [x.strip() for x in re.split(r"\bvs\.?\b|\bversus\b|\band\b|\bwith\b|,", body) if x.strip()]
    picks = []
    for part in parts:
        for p in find_products(part, limit=3):
            if p not in picks:
                picks.append(p)
                break
    if len(picks) < 2:      # e.g. "compare basin mixers" -> the top two matches
        for p in find_products(body, limit=4):
            if p not in picks:
                picks.append(p)
    picks = picks[:3]
    if len(picks) < 2:
        return _result("I need two products to compare. Try \"compare basin mixer vs pillar tap\" "
                       "or use the Compare button on product cards.")
    fields = [("Price", lambda p: money(_price(p))), ("Brand", lambda p: p.brand),
              ("Material", lambda p: p.material), ("Size", lambda p: p.size),
              ("Finish", lambda p: p.finish), ("Weight", lambda p: p.weight),
              ("Availability", lambda p: "In stock" if p.in_stock else "Out of stock")]
    rows = [{"label": lbl, "values": [f(p) or "—" for p in picks]} for lbl, f in fields
            if any(f(p) for p in picks)]
    cheapest = min(picks, key=_price)
    notes = [f"{cheapest.name} is the most affordable at {money(_price(cheapest))}."]
    discounted = [p for p in picks if p.discount_percent]
    if discounted:
        d = max(discounted, key=lambda p: p.discount_percent)
        notes.append(f"{d.name} has the biggest discount ({d.discount_percent}% off).")
    out_of_stock = [p.name for p in picks if not p.in_stock]
    if out_of_stock:
        notes.append("Currently out of stock: " + ", ".join(out_of_stock) + ".")
    return _result("Here's a side-by-side comparison from our catalog:\n" + "\n".join(notes), picks,
                   comparison={"products": [p.name for p in picks], "rows": rows},
                   compare_ids=[p.id for p in picks])


# ================================================================ main entry

def generate_reply(message, context=None):
    """
    Returns a dict:
        { "reply": str, "products": [product_dict, ...],
          optional "action": {...add_to_cart proposal...}, "comparison": {...} }
    """
    text = (message or "").strip()[:500]
    low = text.lower()
    context = context or {}

    if not text:
        return _result("Please type your question and I'll help you find the right product.")

    # ---- greetings ----
    if any(low.startswith(g) for g in GREETINGS) and len(low) < 25:
        return _result("Hello! 👋 I'm the M Hardware assistant. Tell me what you need — for example "
                       "\"a tap under ₹1000\", \"20 bags of cement\" or \"how many tiles for a 10x12 ft room\".")

    # ---- thanks ----
    if any(t in low for t in THANKS) and len(low) < 40:
        return _result("Happy to help! 😊 Anything else you need?")

    # ---- orders & payment are never done by the assistant ----
    if re.search(r"\b(place|confirm|complete)\b.{0,20}\border\b|\b(pay|payment)\b", low):
        return _result("I can't place orders or take payments — that's always done by you. "
                       "Open your cart and choose Proceed to Checkout when you're ready. "
                       "I can help you pick products and add them to your cart.",
                       action={"type": "navigate", "url": "/cart.html", "label": "Go to cart"})

    # ---- what do you sell ----
    if any(k in low for k in SELL_PHRASES):
        names = [c.name for c in _top_categories()]
        if names:
            return _result("We sell: " + ", ".join(names) + ". Ask me about any of them, e.g. \"show me tiles\".")

    # ---- shop contact info ----
    if any(k in low for k in CONTACT_WORDS):
        phone = Setting.get("phone", "")
        wa = Setting.get("whatsapp", "")
        addr = Setting.get("address", "")
        hours = Setting.get("opening_hours", "")
        return _result(f"You can reach us at 📞 {phone} or on WhatsApp {wa}.\n"
                       f"Address: {addr}\nOpening hours: {hours}")

    words = _keywords(text)

    for handler in (lambda: _tiles(low, words), lambda: _compare(text, low), lambda: _guidance(low, words)):
        res = handler()
        if res:
            return res

    lo, hi = parse_budget(low)
    qty = parse_quantity(low)
    wants_cart = bool(re.search(r"\b(add|put)\b.*\b(cart|basket)\b|\badd (it|this|that|the best|them)\b", low)) \
        or (qty is not None and bool(re.search(r"\b(need|want|buy|order|add|get)\b", low)))

    # "add the best one to my cart" with no product words -> use the products shown last
    if wants_cart and not words and context.get("product_ids"):
        ids = [int(i) for i in context["product_ids"] if str(i).isdigit()][:12]
        shown = rank(Product.query.filter(Product.id.in_(ids)).all(), hi)
        if shown:
            action = _cart_action(shown[0], qty)
            if action:
                return _result(f"From the products I just showed, I'd pick {shown[0].name} "
                               f"({money(_price(shown[0]))}) — it's in stock. Confirm below to add it.",
                               [shown[0]], action)

    products = find_products(text, limit=8, max_price=hi, min_price=lo)
    if not products and "tile" in words:
        products = [p for p in Product.query.all() if "tile" in _haystack(p)][:6]

    if not products:
        if (hi or lo) and find_products(text, limit=1):
            cheapest = min(find_products(text, limit=20), key=_price)
            return _result(f"Nothing matches within that budget. The lowest-priced match is "
                           f"{cheapest.name} at {money(_price(cheapest))}.", [cheapest])
        return _result("I couldn't find that in our store catalog. Try a different word "
                       "(for example \"tap\", \"pipe\", \"tile\"). " + CONTACT_HINT)

    ranked = rank(products, hi)
    budget_txt = ""
    if hi and lo:
        budget_txt = f" between {money(lo)} and {money(hi)}"
    elif hi:
        budget_txt = f" under {money(hi)}"
    elif lo:
        budget_txt = f" above {money(lo)}"

    if wants_cart or qty:
        best = ranked[0]
        if not best.in_stock:
            return _result(f"{best.name} is out of stock right now. Here are the closest options:",
                           ranked[:4])
        want = qty or 1
        note = ""
        if want > (best.stock or 0):
            note = f" Only {best.stock} {best.unit or 'piece'}(s) are in stock, so I've set the quantity to that."
        action = _cart_action(best, want)
        total = action["total"]
        return _result(f"Best match{budget_txt}: {best.name} at {money(_price(best))} per {best.unit or 'piece'} "
                       f"({best.stock} in stock). {action['quantity']} × = {money(total)}.{note}\n"
                       "Shall I add it to your cart? Confirm below.", ranked[:4], action)

    is_price = any(k in low for k in ("price", "cost", "rate", "how much"))
    if is_price:
        return _result("Here are the prices in our store:\n" + "\n".join(_line(p) for p in ranked[:5]),
                       ranked[:6])
    intro = f"I found {len(ranked)} matching product(s){budget_txt}."
    if hi or "best" in low or "recommend" in low or "suggest" in low:
        top = ranked[0]
        intro += f" My top pick is {top.name} at {money(_price(top))}" + \
                 (" — in stock." if top.in_stock else " (currently out of stock).")
        intro += "\n" + "\n".join(_line(p) for p in ranked[:4])
        return _result(intro, ranked[:6], _cart_action(top, 1) if top.in_stock else None)
    return _result(intro + " Tap a card to see full details.", ranked[:6])


def _top_categories():
    return Category.query.filter_by(parent_id=None, is_active=True).order_by(Category.sort_order).all()
