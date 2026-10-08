"""
gen_images.py
-------------
Generates offline demo SVG images (no external dependencies):
    uploads/products/<slug>.svg    one per DEMO_PRODUCTS row
    uploads/categories/<slug>.svg  one per top-level category
    uploads/gallery/<name>.svg     demo shop photos
Existing files are never overwritten unless --force is passed.

    python database/gen_images.py
"""
import os
import sys
from xml.sax.saxutils import escape

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.seed import DEMO_PRODUCTS, GALLERY_DEMO, CATEGORY_TREE, UPLOADS  # noqa: E402
from utils import slugify  # noqa: E402

from services.svg_fallback import PALETTE, CAT_ICON, icon, product_svg  # noqa: E402


def scene_svg(title, cat, keys):
    """Gallery scene: a shelf row of icons with a title strip."""
    c, d, l = PALETTE.get(cat, PALETTE["Hardware"])
    items = "".join(
        f'<g transform="translate({40 + n * 250} 150) scale(.55)">{icon(k, c, d, l)}</g>'
        for n, k in enumerate(keys[:3])
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="800" height="600">'
        f'<rect width="800" height="600" fill="{l}"/>'
        '<rect y="420" width="800" height="180" fill="#e5e7eb"/>'
        '<rect x="30" y="360" width="740" height="18" rx="4" fill="#9a8c7a"/>'
        '<rect x="30" y="150" width="740" height="12" rx="4" fill="#9a8c7a"/>'
        f'{items}'
        f'<rect y="40" width="800" height="70" fill="{d}"/>'
        f'<text x="400" y="86" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="34" font-weight="700" fill="#fff">{escape(title)}</text></svg>'
    )


def category_svg(name):
    c, d, l = PALETTE[name]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" width="600" height="400">'
        f'<rect width="600" height="400" fill="{l}"/>'
        f'<g transform="translate(100 0)">{icon(CAT_ICON[name], c, d, l)}</g></svg>'
    )


SCENES = {
    "showroom-front.svg": ("Showroom", "Sanitary", ["toilet", "basin", "tap"]),
    "shop-interior.svg": ("Shop Interior", "Hardware", ["hinge", "lock", "handle"]),
    "sanitary-display.svg": ("Sanitary Display", "Sanitary", ["basin_top", "toilet", "mirror"]),
    "taps-display.svg": ("Taps and Showers", "Sanitary", ["mixer", "shower", "swan"]),
    "tiles-display.svg": ("Tiles Display", "Tiles", ["tile", "tile_marble", "tile_designer"]),
    "hardware-shelves.svg": ("Hardware Shelves", "Hardware", ["screw", "bolt", "bracket"]),
    "tools-display.svg": ("Tools Display", "Tools", ["hammer", "pliers", "tape"]),
    "machine-corner.svg": ("Machine Corner", "Machines", ["drill", "grinder", "pump"]),
    "packaging-delivery.svg": ("Packing and Delivery", "Construction Materials", ["bag", "can", "roll"]),
    "pipes-rack.svg": ("Pipes and Fittings", "Pipes", ["pipe", "elbow", "tee"]),
}


def save(folder, filename, svg, force):
    path = os.path.join(UPLOADS, folder, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and not force:
        return 0
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return 1


def main():
    force = "--force" in sys.argv
    n = 0
    for name, cat, _sub, *_rest, icon_key in DEMO_PRODUCTS:
        n += save("products", slugify(name) + ".svg", product_svg(name, cat, icon_key), force)
    for cat in CATEGORY_TREE:
        n += save("categories", slugify(cat) + ".svg", category_svg(cat), force)
    for fn, (title, cat, keys) in SCENES.items():
        n += save("gallery", fn, scene_svg(title, cat, keys), force)
    print(f"✔ {n} image(s) written")


if __name__ == "__main__":
    main()
