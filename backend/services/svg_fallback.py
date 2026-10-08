"""
svg_fallback.py
---------------
Professional category-specific SVG used ONLY when no real/AI image is available.
Draws a simple product illustration (pipe, tap, tile, tool ...) on a clean background
with the product name. Also provides the drawings used by database/gen_images.py.
"""
import os
from xml.sax.saxutils import escape

UPLOADS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")

# category -> (main, dark, light)
PALETTE = {
    "Sanitary": ("#3b82c4", "#1e4f82", "#dbeafe"),
    "Hardware": ("#8a919b", "#4b5563", "#e5e7eb"),
    "Tiles": ("#d4b483", "#8a6d3b", "#f5ecd9"),
    "Tools": ("#ea8a2f", "#9a4f0c", "#fde8cf"),
    "Machines": ("#4b535e", "#1f2933", "#d9dde2"),
    "Pipes": ("#1f9a94", "#0f5f5b", "#d3f1ef"),
    "Fittings": ("#2bb0a8", "#0f5f5b", "#d3f1ef"),
    "Construction Materials": ("#a9794a", "#5f3f20", "#efe1d2"),
    "Accessories": ("#8b6fc4", "#4c3a85", "#e9e2f6"),
}

CAT_ICON = {
    "Sanitary": "basin", "Hardware": "hinge", "Tiles": "tile", "Pipes": "pipe",
    "Fittings": "elbow", "Machines": "drill", "Tools": "wrench",
    "Construction Materials": "bag", "Accessories": "roll",
}


def R(x, y, w, h, fill, rx=0, extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" {extra}/>'


def C(x, y, r, fill, extra=""):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" {extra}/>'


def E(x, y, rx, ry, fill, extra=""):
    return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{fill}" {extra}/>'


def P(d, stroke, w=22, fill="none", extra=""):
    return (f'<path d="{d}" stroke="{stroke}" stroke-width="{w}" fill="{fill}" '
            f'stroke-linecap="round" stroke-linejoin="round" {extra}/>')


def icon(key, c, d, l):
    """Return SVG body drawn inside a 400x400 box. c=main d=dark l=light."""
    i = {}
    i["pipe"] = R(40, 150, 320, 90, c, 8) + R(40, 150, 30, 90, d, 6) + R(330, 150, 30, 90, d, 6) + R(90, 165, 200, 14, l, 6, 'opacity=".6"')
    i["elbow"] = P("M70 120 H230 V290", c, 70) + P("M70 120 H110", d, 80) + P("M230 250 V290", d, 80)
    i["tee"] = P("M60 140 H340", c, 70) + P("M200 140 V300", c, 70) + R(40, 100, 30, 80, d, 6) + R(330, 100, 30, 80, d, 6) + R(160, 290, 80, 24, d, 6)
    i["coupler"] = R(70, 150, 260, 90, c, 10) + R(150, 130, 100, 130, d, 14) + R(40, 165, 40, 60, d, 6) + R(320, 165, 40, 60, d, 6)
    i["union"] = R(40, 160, 70, 80, c, 6) + R(110, 140, 60, 120, d, 8) + R(230, 140, 60, 120, d, 8) + R(290, 160, 70, 80, c, 6) + R(170, 175, 60, 50, l, 4)
    i["valve"] = R(60, 190, 280, 70, c, 8) + E(200, 190, 60, 50, d) + R(190, 90, 20, 80, d) + R(130, 70, 140, 24, c, 10)
    i["basin"] = P("M80 190 Q200 330 320 190 Z", c, 8, l) + E(200, 190, 120, 28, l, f'stroke="{c}" stroke-width="8"') + R(190, 90, 20, 70, d, 6) + P("M200 90 H250", d, 14) + R(180, 300, 40, 50, d, 6)
    i["basin_top"] = R(70, 190, 260, 140, d, 10) + E(200, 190, 130, 40, l, f'stroke="{c}" stroke-width="10"') + E(200, 190, 70, 18, c) + P("M300 190 V110 H260", d, 14)
    i["toilet"] = R(110, 70, 180, 90, c, 12) + E(200, 215, 100, 55, l, f'stroke="{c}" stroke-width="12"') + R(150, 255, 100, 90, c, 14) + R(180, 82, 40, 14, d, 6)
    i["squat"] = E(200, 220, 150, 80, l, f'stroke="{c}" stroke-width="14"') + E(200, 220, 90, 40, d) + E(200, 215, 40, 20, "#fff")
    i["seat"] = E(200, 200, 120, 130, l, f'stroke="{c}" stroke-width="16"') + E(200, 205, 70, 85, "#fff", f'stroke="{d}" stroke-width="6"') + R(150, 60, 100, 28, d, 8)
    i["cistern"] = R(90, 90, 220, 160, c, 14) + R(90, 90, 220, 28, d, 10) + C(200, 70, 18, d) + P("M140 280 V340", d, 24) + R(120, 250, 160, 18, l, 6)
    i["urinal"] = P("M130 80 Q110 260 200 320 Q290 260 270 80 Z", l, 14, l, f'stroke="{c}"') + E(200, 270, 40, 30, c) + R(170, 60, 60, 24, d, 6)
    i["mirror"] = R(100, 50, 200, 300, d, 20) + R(118, 68, 164, 264, l, 12) + P("M150 300 L250 100", "#fff", 14, "none", 'opacity=".8"')
    i["drain"] = R(100, 100, 200, 200, c, 14) + C(200, 200, 70, d) + "".join(R(160 + k * 30, 150, 10, 100, l, 3) for k in range(3))
    i["rod"] = R(60, 185, 280, 22, c, 11) + R(50, 150, 24, 100, d, 8) + R(326, 150, 24, 100, d, 8) + R(120, 207, 160, 110, l, 6, f'stroke="{c}" stroke-width="6" opacity=".7"')
    i["tap"] = P("M120 300 V150 Q120 100 180 100 H260", c, 36) + R(250, 90, 36, 90, d, 10) + R(60, 270, 120, 36, d, 10) + P("M180 100 V60", d, 26) + R(140, 44, 80, 22, d, 8)
    i["pillar"] = R(165, 190, 70, 130, c, 8) + R(150, 300, 100, 30, d, 8) + R(185, 100, 30, 100, c, 6) + P("M120 80 H280", d, 28) + R(210, 170, 70, 28, c, 10)
    i["bib"] = R(60, 160, 140, 56, c, 10) + R(190, 140, 80, 96, d, 10) + P("M270 190 H320 V280", c, 36) + P("M130 160 V110", d, 22) + R(90, 90, 80, 22, d, 8)
    i["angle"] = P("M100 120 V240 H290", c, 44) + R(70, 90, 60, 36, d, 8) + R(270, 215, 50, 50, d, 8) + P("M160 240 V320", d, 30) + R(120, 304, 80, 24, d, 8)
    i["swan"] = P("M150 320 V140 Q150 70 220 70 Q290 70 290 140 V170", c, 40) + R(265, 165, 50, 40, d, 8) + R(120, 300, 60, 40, d, 8) + P("M150 220 H100", d, 24)
    i["mixer"] = P("M110 300 V170 Q110 120 170 120 H260 V190", c, 40) + R(236, 185, 48, 36, d, 8) + P("M140 120 V60", d, 22) + R(90, 40, 100, 24, d, 10) + R(70, 290, 100, 36, d, 8)
    i["shower"] = P("M80 320 V100 Q80 70 120 70 H220", c, 24) + E(280, 110, 80, 28, d, f'transform="rotate(12 280 110)"') + "".join(P(f"M{240 + k * 25} 150 L{232 + k * 28} 230", l, 7, "none", 'stroke-dasharray="10 12"') for k in range(4))
    i["handshower"] = R(150, 210, 60, 150, c, 24) + E(180, 160, 70, 45, d) + E(180, 150, 50, 25, l) + P("M250 330 Q330 330 330 260 Q330 200 270 200", c, 12)
    i["tile"] = R(70, 70, 260, 260, l, 10, f'stroke="{c}" stroke-width="10"') + R(70, 195, 260, 10, c) + R(195, 70, 10, 260, c) + R(90, 90, 100, 100, c, 4, 'opacity=".5"') + R(215, 215, 100, 100, c, 4, 'opacity=".5"')
    i["tile_dots"] = R(70, 70, 260, 260, l, 10, f'stroke="{c}" stroke-width="10"') + "".join(C(105 + a * 48, 105 + b * 48, 9, c) for a in range(5) for b in range(5))
    i["tile_designer"] = R(70, 70, 260, 260, l, 10, f'stroke="{c}" stroke-width="10"') + P("M70 330 Q200 200 330 330", c, 14) + P("M70 250 Q200 120 330 250", d, 14) + P("M70 170 Q200 40 330 170", c, 14)
    i["tile_marble"] = R(70, 70, 260, 260, "#fff", 10, f'stroke="{c}" stroke-width="10"') + P("M90 90 Q170 180 140 250 T230 320", d, 5) + P("M200 80 Q260 160 230 210 T310 300", c, 8) + P("M110 200 L180 170 L250 190", d, 3)
    i["hammer"] = R(185, 130, 30, 220, d, 10) + R(100, 80, 190, 64, c, 10) + P("M100 90 Q50 100 40 160", c, 26)
    i["screwdriver"] = R(180, 70, 40, 100, c, 14) + R(192, 170, 16, 160, "#9aa1a9", 4) + R(190, 320, 20, 20, d, 3) + R(260, 120, 36, 90, d, 12, 'transform="rotate(25 278 165)"') + R(268, 205, 12, 120, "#9aa1a9", 4, 'transform="rotate(25 278 165)"')
    i["pliers"] = P("M130 80 L250 280", c, 36) + P("M270 80 L150 280", d, 36) + C(200, 180, 16, l) + P("M135 275 L110 345", d, 30) + P("M265 275 L290 345", c, 30)
    i["wrench"] = P("M130 330 L270 120", d, 44) + P("M270 120 Q230 50 160 90 L190 130 L160 160 L120 130 Q90 220 220 190", c, 28, c)
    i["pipewrench"] = P("M110 340 L250 110", d, 40) + R(230, 60, 90, 90, c, 12, 'transform="rotate(30 275 105)"') + R(268, 80, 40, 40, l, 4, 'transform="rotate(30 275 105)"')
    i["spanner"] = P("M110 330 L290 110", d, 40) + P("M290 110 Q320 50 250 60 L240 100 L270 120 Z", c, 22, c) + P("M70 280 L210 90", c, 30)
    i["tape"] = R(90, 110, 220, 190, c, 40) + C(200, 205, 55, l, f'stroke="{d}" stroke-width="10"') + R(280, 250, 80, 20, "#facc15", 4) + R(230, 100, 20, 14, d)
    i["toolbox"] = R(60, 150, 280, 170, c, 14) + R(60, 150, 280, 40, d, 10) + P("M150 150 V105 Q150 90 165 90 H235 Q250 90 250 105 V150", d, 18) + R(180, 185, 40, 36, l, 6)
    i["saw"] = P("M90 120 H320 V150 H110 V320", d, 20) + R(110, 280, 220, 14, "#9aa1a9", 3) + "".join(f'<path d="M{120 + k * 18} 280 l9 -12 l9 12z" fill="#6b7280"/>' for k in range(11)) + R(70, 70, 60, 70, c, 12)
    i["drill"] = R(80, 90, 210, 90, c, 28) + R(150, 170, 70, 140, d, 14) + R(290, 115, 70, 40, "#9aa1a9", 6) + R(350, 128, 30, 14, d) + R(100, 100, 50, 18, l, 8, 'opacity=".5"')
    i["grinder"] = R(60, 150, 200, 90, c, 40) + R(250, 120, 20, 150, d, 6) + E(310, 195, 70, 70, "#9aa1a9") + C(310, 195, 22, d) + R(110, 240, 40, 80, d, 10)
    i["cutter"] = R(80, 230, 230, 80, c, 14) + E(210, 190, 100, 100, "#9aa1a9", f'stroke="{d}" stroke-width="10"') + C(210, 190, 22, d) + R(280, 90, 40, 100, d, 10) + P("M140 230 L200 190", d, 14)
    i["welder"] = R(90, 90, 220, 200, c, 16) + C(150, 170, 34, l) + C(250, 170, 34, l) + R(120, 240, 160, 20, d, 6) + P("M310 220 Q370 220 350 300 Q340 340 300 340", d, 10) + R(100, 290, 40, 30, d, 6) + R(260, 290, 40, 30, d, 6)
    i["pump"] = R(80, 190, 170, 110, c, 20) + C(230, 245, 70, d) + C(230, 245, 30, l) + R(110, 140, 100, 60, d, 10) + R(290, 215, 80, 40, "#9aa1a9", 6) + R(60, 300, 240, 20, d, 6)
    i["bag"] = P("M110 90 Q200 60 290 90 L310 330 Q200 350 90 330 Z", c, 10, c) + R(130, 170, 140, 90, l, 10) + R(140, 190, 120, 12, d, 4) + R(140, 215, 80, 12, d, 4)
    i["sand"] = '<path d="M40 330 Q120 120 200 150 Q290 120 360 330 Z" fill="%s"/>' % c + "".join(C(100 + (k * 47) % 200, 250 + (k * 29) % 60, 5, d) for k in range(14))
    i["can"] = R(120, 100, 160, 230, c, 18) + R(120, 80, 160, 36, d, 12) + R(135, 160, 130, 100, l, 10) + R(150, 185, 100, 12, d, 4) + R(150, 210, 70, 12, d, 4)
    i["roll"] = C(200, 200, 110, c) + C(200, 200, 50, "#fff", f'stroke="{d}" stroke-width="10"') + P("M290 270 Q340 300 370 290", c, 28)
    i["hinge"] = R(80, 90, 90, 220, c, 8) + R(230, 90, 90, 220, c, 8) + R(170, 90, 60, 220, d, 14) + "".join(C(x, y, 9, l) for x in (125, 275) for y in (130, 200, 270))
    i["lock"] = R(90, 170, 220, 160, c, 20) + P("M135 170 V120 Q135 60 200 60 Q265 60 265 120 V170", d, 26) + C(200, 235, 24, d) + R(192, 245, 16, 50, d, 6)
    i["latch"] = R(60, 160, 280, 80, c, 14) + R(250, 130, 30, 140, d, 8) + R(100, 180, 130, 40, d, 8) + C(100, 200, 10, l)
    i["handle"] = R(60, 180, 280, 40, c, 20) + R(90, 130, 40, 100, d, 10) + R(270, 130, 40, 100, d, 10) + C(200, 300, 34, d)
    i["bracket"] = P("M100 80 V300 H320", c, 36) + P("M120 280 L300 120", d, 22) + C(100, 120, 8, l) + C(300, 300, 8, l)
    i["clamp"] = P("M110 300 V170 Q110 80 200 80 Q290 80 290 170 V300", c, 36) + R(70, 280, 90, 36, d, 6) + R(240, 280, 90, 36, d, 6) + C(115, 298, 8, l) + C(285, 298, 8, l)
    i["screw"] = P("M200 80 V310", c, 30) + R(150, 60, 100, 36, d, 18) + "".join(P(f"M180 {130 + k * 36} L220 {118 + k * 36}", d, 8) for k in range(5))
    i["nail"] = R(190, 90, 20, 240, c, 6) + R(150, 70, 100, 26, d, 10) + '<path d="M190 330 L200 370 L210 330Z" fill="%s"/>' % d
    i["bolt"] = R(110, 60, 180, 70, c, 10) + R(170, 130, 60, 210, "#9aa1a9", 4) + "".join(R(165, 160 + k * 30, 70, 8, d) for k in range(5))
    return i.get(key, i["pipe"])


def wrap(name, max_chars=26):
    words, lines, cur = name.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    return lines[:2]


def product_svg(name, cat, key):
    c, d, l = PALETTE.get(cat, PALETTE["Hardware"])
    text = "".join(
        f'<text x="400" y="{700 + n * 38}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="32" font-weight="600" fill="{d}">{escape(t)}</text>'
        for n, t in enumerate(wrap(name))
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" width="800" height="800">'
        '<rect width="800" height="800" fill="#f4f8fb"/>'
        f'<circle cx="400" cy="360" r="300" fill="{l}"/>'
        '<ellipse cx="400" cy="640" rx="200" ry="16" fill="#000" opacity=".08"/>'
        f'<g transform="translate(130 110) scale(1.35)">{icon(key, c, d, l)}</g>'
        f'{text}</svg>'
    )


# product-name keyword -> drawing key (first match wins); falls back to the category drawing
KEYWORD_ICONS = [
    ("elbow", "elbow"), ("tee", "tee"), ("coupler", "coupler"), ("reducer", "coupler"),
    ("nipple", "coupler"), ("union", "union"), ("valve", "valve"), ("clamp", "clamp"),
    ("pipe", "pipe"), ("basin", "basin"), ("toilet", "toilet"), ("cistern", "cistern"),
    ("urinal", "urinal"), ("mirror", "mirror"), ("drain", "drain"), ("seat", "seat"),
    ("hand shower", "handshower"), ("health faucet", "handshower"), ("shower", "shower"),
    ("mixer", "mixer"), ("swan", "swan"), ("angle cock", "angle"), ("bib", "bib"),
    ("tap", "tap"), ("cock", "pillar"), ("tile", "tile"), ("hammer", "hammer"),
    ("spanner", "spanner"), ("pipe wrench", "pipewrench"), ("wrench", "wrench"),
    ("plier", "pliers"), ("screwdriver", "screwdriver"), ("tape", "tape"),
    ("tool box", "toolbox"), ("hacksaw", "saw"), ("hinge", "hinge"), ("lock", "lock"),
    ("latch", "latch"), ("handle", "handle"), ("bracket", "bracket"), ("screw", "screw"),
    ("nail", "nail"), ("bolt", "bolt"), ("drill", "drill"), ("grinder", "grinder"),
    ("cutting", "cutter"), ("weld", "welder"), ("pump", "pump"), ("cement", "bag"),
    ("adhesive", "bag"), ("sand", "sand"), ("compound", "can"), ("cement", "can"),
    ("wire", "roll"),
]


def _root_category(product):
    cat = product.category
    while cat is not None and cat.parent is not None:
        cat = cat.parent
    return cat.name if cat else ""


def icon_key_for(product):
    name = product.name.lower()
    for word, key in KEYWORD_ICONS:
        if word in name:
            return key
    return CAT_ICON.get(_root_category(product), "bag")


def make_svg(product):
    """SVG markup (str) for a product."""
    cat = _root_category(product)
    if cat not in PALETTE:
        cat = "Hardware"
    return product_svg(product.name, cat, icon_key_for(product))


def save_svg(product, slug, overwrite=False):
    """Write uploads/products/<slug>.svg and return its URL path.

    An existing <slug>.svg (e.g. the seeded demo drawing) is kept as-is.
    """
    folder = os.path.join(UPLOADS, "products")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, slug + ".svg")
    if overwrite or not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(make_svg(product))
    return f"/uploads/products/{slug}.svg"
