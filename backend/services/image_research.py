"""
image_research.py
-----------------
Builds a short text description of what a product physically looks like.

Google Images / web search is used for RESEARCH ONLY: we read result titles
(text) to improve the prompt. No image is ever downloaded or hot-linked.
If no search key is configured we use the curated dictionary below.
"""
import os
import requests

# keyword in product name/category -> visual attributes (first match wins)
VISUALS = [
    ("elbow", {"shape": "90-degree elbow bend fitting", "typical_view": "three-quarter front", "notes": "small plumbing fitting"}),
    ("tee", {"shape": "T-shaped three-way pipe fitting", "typical_view": "three-quarter front", "notes": "small plumbing fitting"}),
    ("coupler", {"shape": "short straight socket coupler", "typical_view": "three-quarter front", "notes": "small plumbing fitting"}),
    ("union", {"shape": "two-part union with central nut", "typical_view": "side view", "notes": "small plumbing fitting"}),
    ("valve", {"shape": "ball valve body with lever handle", "typical_view": "three-quarter front", "notes": "brass fitting"}),
    ("pipe", {"shape": "straight hollow tube, cut ends visible", "typical_view": "slight diagonal", "notes": "plumbing pipe"}),
    ("basin", {"shape": "rounded washbasin bowl", "typical_view": "three-quarter front", "notes": "ceramic sanitaryware"}),
    ("toilet", {"shape": "toilet pan with cistern", "typical_view": "three-quarter front", "notes": "ceramic sanitaryware"}),
    ("cistern", {"shape": "rectangular flush tank with button", "typical_view": "front", "notes": "bathroom fixture"}),
    ("urinal", {"shape": "wall-mounted urinal bowl", "typical_view": "front", "notes": "ceramic sanitaryware"}),
    ("mirror", {"shape": "rectangular bathroom mirror with thin frame", "typical_view": "front", "notes": "bathroom accessory"}),
    ("shower", {"shape": "round shower head with nozzles", "typical_view": "three-quarter front", "notes": "bathroom fixture"}),
    ("mixer", {"shape": "single-lever mixer tap with spout", "typical_view": "three-quarter front", "notes": "faucet"}),
    ("tap", {"shape": "faucet with handle and spout", "typical_view": "three-quarter front", "notes": "faucet"}),
    ("cock", {"shape": "faucet with handle and spout", "typical_view": "three-quarter front", "notes": "faucet"}),
    ("tile", {"shape": "flat square or rectangular tile", "typical_view": "front-facing flat", "notes": "ceramic or vitrified tile sample"}),
    ("hammer", {"shape": "claw hammer with head and handle", "typical_view": "side profile", "notes": "hand tool"}),
    ("wrench", {"shape": "open-end wrench", "typical_view": "side profile", "notes": "hand tool"}),
    ("spanner", {"shape": "set of open-end spanners", "typical_view": "top-down fan", "notes": "hand tool"}),
    ("plier", {"shape": "combination pliers with insulated handles", "typical_view": "top-down", "notes": "hand tool"}),
    ("screwdriver", {"shape": "screwdrivers with coloured handles", "typical_view": "side profile", "notes": "hand tool"}),
    ("tape", {"shape": "retractable measuring tape case", "typical_view": "three-quarter front", "notes": "measuring tool"}),
    ("hinge", {"shape": "butt hinge with screw holes", "typical_view": "front, opened flat", "notes": "door hardware"}),
    ("lock", {"shape": "door lock body with keys", "typical_view": "three-quarter front", "notes": "door hardware"}),
    ("screw", {"shape": "wood screws with threaded shank", "typical_view": "side, small group", "notes": "fasteners"}),
    ("nail", {"shape": "steel nails", "typical_view": "side, small group", "notes": "fasteners"}),
    ("drill", {"shape": "electric drill machine with chuck", "typical_view": "three-quarter front", "notes": "power tool"}),
    ("grinder", {"shape": "angle grinder with disc guard", "typical_view": "three-quarter front", "notes": "power tool"}),
    ("pump", {"shape": "monoblock water pump", "typical_view": "three-quarter front", "notes": "water machine"}),
    ("cement", {"shape": "paper cement bag", "typical_view": "front", "notes": "construction material"}),
]

# fallback by root category
CATEGORY_VISUALS = {
    "pipes": {"shape": "plumbing pipe", "typical_view": "slight diagonal", "notes": "plumbing product"},
    "fittings": {"shape": "small plumbing fitting", "typical_view": "three-quarter front", "notes": "plumbing product"},
    "sanitary": {"shape": "bathroom fixture", "typical_view": "three-quarter front", "notes": "sanitaryware"},
    "tiles": {"shape": "flat tile", "typical_view": "front-facing flat", "notes": "tile sample"},
    "hardware": {"shape": "metal hardware item", "typical_view": "three-quarter front", "notes": "hardware"},
    "tools": {"shape": "hand tool", "typical_view": "side profile", "notes": "tool"},
    "machines": {"shape": "power machine", "typical_view": "three-quarter front", "notes": "machine"},
}


def _root_category(product):
    cat = product.category
    while cat is not None and cat.parent is not None:
        cat = cat.parent
    return (cat.name if cat else "").lower()


def _web_notes(query):
    """Optional: titles of image search results (TEXT only). Returns '' if no key."""
    key = os.getenv("SERPAPI_KEY")
    if not key:
        return ""
    try:
        r = requests.get("https://serpapi.com/search.json",
                         params={"engine": "google_images", "q": query, "api_key": key}, timeout=15)
        titles = [i.get("title", "") for i in r.json().get("images_results", [])[:5]]
        return "; ".join(t for t in titles if t)[:200]
    except Exception:
        return ""


def research(product):
    """Return {shape, colour, material, typical_view, typical_background, notes}."""
    name = product.name.lower()
    info = next((v for k, v in VISUALS if k in name), None) \
        or CATEGORY_VISUALS.get(_root_category(product),
                                {"shape": "single product", "typical_view": "three-quarter front", "notes": ""})
    result = {
        "shape": info["shape"],
        "colour": (product.color or "").lower(),
        "material": (product.material or "").lower(),
        "typical_view": info["typical_view"],
        "typical_background": "light grey",
        "notes": info["notes"],
    }
    web = _web_notes(f"{product.name} product photo")
    if web:
        result["web_titles"] = web
    return result
