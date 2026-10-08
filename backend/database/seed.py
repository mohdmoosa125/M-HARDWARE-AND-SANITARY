"""
seed.py
-------
Fills the database with the default admin account, settings,
categories, subcategories, demo products and demo gallery.
Idempotent: safe to re-run, never deletes data.

Run with:
    python database/seed.py
Demo images are generated offline first (optional, already committed):
    python database/gen_images.py
"""
import os
import sys
import zlib

# Make sure the backend folder is importable when running this file directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app                    # noqa: E402
from database.db import db                    # noqa: E402
from models import (                          # noqa: E402
    User, Category, Product, Setting, GalleryImage
)
from routes.settings import DEFAULTS          # noqa: E402
from utils import slugify                     # noqa: E402
from database.migrate import ensure_columns   # noqa: E402


# ---------- categories & subcategories ----------
CATEGORY_TREE = {
    "Sanitary": ["Wash Basin", "Toilet", "Bathroom Accessories", "Shower", "Taps",
                 "Cistern & Urinal", "Mirrors", "Drains"],
    "Hardware": ["Nails", "Screws", "Hinges", "Locks", "Tools",
                 "Bolts & Nuts", "Handles & Latches", "Brackets & Clamps"],
    "Tiles": ["Floor Tiles", "Wall Tiles", "Bathroom Tiles", "Kitchen Tiles", "Designer Tiles",
              "Marble Finish", "Granite Finish"],
    "Pipes": ["PVC Pipes", "CPVC Pipes", "UPVC Pipes", "Water Pipes", "Drainage Pipes"],
    "Fittings": ["Elbow", "Tee", "Coupler", "Socket", "Reducer", "Joint",
                 "Union", "Brass Fittings", "GI Fittings"],
    "Machines": ["Cutting Machines", "Drilling Machines", "Grinding Machines", "Welding Machines",
                 "Pumps"],
    "Tools": [],
    "Construction Materials": [],
    "Accessories": [],
}


# ---------- demo products ----------
# DEMO / SAMPLE DATA ONLY. Brand names on the first 24 rows (Astral, Cera, Jaquar, Bosch ...)
# are sample labels for demonstration; newer rows use neutral names.
# (name, category, subcategory, price, unit, brand, material, size, color, featured, icon)
# `icon` picks the drawing used by database/gen_images.py for the offline demo image.
DEMO_PRODUCTS = [
    ("Premium PVC Pipe 1 inch", "Pipes", "PVC Pipes", 120, "piece", "Astral", "PVC", "1 inch", "White", True, "pipe"),
    ("CPVC Hot Water Pipe 3/4 inch", "Pipes", "CPVC Pipes", 210, "piece", "Astral", "CPVC", "3/4 inch", "Cream", False, "pipe"),
    ("UPVC Drainage Pipe 4 inch", "Pipes", "UPVC Pipes", 480, "piece", "Supreme", "UPVC", "4 inch", "Grey", False, "pipe"),
    ("Wall Mounted Wash Basin", "Sanitary", "Wash Basin", 2450, "piece", "Cera", "Ceramic", "Medium", "White", True, "basin"),
    ("One Piece Western Toilet", "Sanitary", "Toilet", 8900, "piece", "Hindware", "Ceramic", "Standard", "White", True, "toilet"),
    ("Chrome Bathroom Shower Set", "Sanitary", "Shower", 1750, "set", "Jaquar", "Brass", "Standard", "Chrome", False, "shower"),
    ("Brass Water Tap", "Sanitary", "Taps", 640, "piece", "Jaquar", "Brass", "1/2 inch", "Chrome", True, "tap"),
    ("Pillar Cock Tap", "Sanitary", "Taps", 520, "piece", "Cera", "Brass", "1/2 inch", "Chrome", False, "pillar"),
    ("Designer Floor Tile 600x600", "Tiles", "Floor Tiles", 780, "box", "Kajaria", "Vitrified", "600x600 mm", "Grey", True, "tile"),
    ("Glossy Wall Tile 300x600", "Tiles", "Wall Tiles", 520, "box", "Somany", "Ceramic", "300x600 mm", "White", False, "tile"),
    ("Anti Skid Bathroom Tile", "Tiles", "Bathroom Tiles", 610, "box", "Nitco", "Ceramic", "300x300 mm", "Beige", False, "tile_dots"),
    ("PVC Elbow 1 inch", "Fittings", "Elbow", 18, "piece", "Astral", "PVC", "1 inch", "White", False, "elbow"),
    ("PVC Tee 1 inch", "Fittings", "Tee", 24, "piece", "Astral", "PVC", "1 inch", "White", False, "tee"),
    ("Pipe Coupler 3/4 inch", "Fittings", "Coupler", 15, "piece", "Supreme", "PVC", "3/4 inch", "White", False, "coupler"),
    ("Drilling Machine 13mm", "Machines", "Drilling Machines", 3200, "piece", "Bosch", "Metal", "13 mm", "Blue", True, "drill"),
    ("Angle Grinder 4 inch", "Machines", "Grinding Machines", 2750, "piece", "Makita", "Metal", "4 inch", "Green", False, "grinder"),
    ("Cutting Machine 14 inch", "Machines", "Cutting Machines", 5600, "piece", "Bosch", "Metal", "14 inch", "Blue", False, "cutter"),
    ("Steel Claw Hammer", "Tools", None, 320, "piece", "Taparia", "Steel", "500 g", "Silver", False, "hammer"),
    ("Adjustable Wrench 10 inch", "Tools", None, 450, "piece", "Taparia", "Steel", "10 inch", "Silver", True, "wrench"),
    ("Screwdriver Set (6 pcs)", "Tools", None, 390, "set", "Taparia", "Steel", "Standard", "Multicolor", False, "screwdriver"),
    ("Cement Bag 50 kg", "Construction Materials", None, 410, "bag", "UltraTech", "Cement", "50 kg", "Grey", False, "bag"),
    ("River Sand (per cubic ft)", "Construction Materials", None, 55, "cubic ft", "Local", "Sand", "-", "Brown", False, "sand"),
    ("Stainless Steel Door Hinge", "Hardware", "Hinges", 85, "piece", "Godrej", "Stainless Steel", "4 inch", "Silver", False, "hinge"),
    ("Brass Door Lock", "Hardware", "Locks", 1250, "piece", "Godrej", "Brass", "Standard", "Gold", True, "lock"),
    ("Wood Screw 1 inch (100 pcs)", "Hardware", "Screws", 110, "pack", "Local", "Steel", "1 inch", "Silver", False, "screw"),

    # ---- Sanitary ----
    ("Table Top Wash Basin", "Sanitary", "Wash Basin", 2850, "piece", "Store Brand", "Ceramic", "Medium", "White", False, "basin_top"),
    ("Corner Wash Basin", "Sanitary", "Wash Basin", 1950, "piece", "Standard", "Ceramic", "Small", "Ivory", False, "basin"),
    ("Wall Hung Western Toilet", "Sanitary", "Toilet", 7400, "piece", "Premium", "Ceramic", "Standard", "White", False, "toilet"),
    ("Indian Toilet Pan 22 inch", "Sanitary", "Toilet", 1150, "piece", "Standard", "Ceramic", "22 inch", "White", False, "squat"),
    ("Toilet Seat Cover", "Sanitary", "Toilet", 480, "piece", "Store Brand", "Plastic", "Standard", "White", False, "seat"),
    ("Flush Cistern 10 Litre", "Sanitary", "Cistern & Urinal", 1850, "piece", "Standard", "Plastic", "10 L", "White", False, "cistern"),
    ("Wall Mounted Urinal", "Sanitary", "Cistern & Urinal", 1350, "piece", "Standard", "Ceramic", "Standard", "White", False, "urinal"),
    ("Health Faucet with Hose", "Sanitary", "Bathroom Accessories", 520, "set", "Store Brand", "Brass", "1 m hose", "Chrome", False, "handshower"),
    ("Bathroom Mirror 18x24 inch", "Sanitary", "Mirrors", 950, "piece", "Standard", "Glass", "18x24 inch", "Silver", False, "mirror"),
    ("Stainless Steel Floor Drain", "Sanitary", "Drains", 260, "piece", "Heavy Duty", "Stainless Steel", "4 inch", "Silver", False, "drain"),
    ("Towel Rod 24 inch", "Sanitary", "Bathroom Accessories", 420, "piece", "Standard", "Stainless Steel", "24 inch", "Silver", False, "rod"),

    # ---- Taps & Fittings ----
    ("Bib Cock Tap", "Sanitary", "Taps", 340, "piece", "Store Brand", "Brass", "1/2 inch", "Chrome", False, "bib"),
    ("Angle Cock Chrome", "Sanitary", "Taps", 290, "piece", "Standard", "Brass", "1/2 inch", "Chrome", False, "angle"),
    ("Swan Neck Tap", "Sanitary", "Taps", 980, "piece", "Premium", "Brass", "1/2 inch", "Chrome", True, "swan"),
    ("Basin Mixer Tap", "Sanitary", "Taps", 1450, "piece", "Premium", "Brass", "Standard", "Chrome", False, "mixer"),
    ("Wall Mixer with Spout", "Sanitary", "Taps", 2350, "set", "Premium", "Brass", "Standard", "Chrome", False, "mixer"),
    ("Shower Mixer Single Lever", "Sanitary", "Shower", 2100, "piece", "Premium", "Brass", "Standard", "Chrome", False, "mixer"),
    ("Hand Shower with Hose", "Sanitary", "Shower", 680, "set", "Store Brand", "ABS", "1.5 m hose", "Chrome", False, "handshower"),
    ("Overhead Shower 8 inch", "Sanitary", "Shower", 1250, "piece", "Standard", "Stainless Steel", "8 inch", "Chrome", False, "shower"),
    ("Kitchen Sink Tap", "Sanitary", "Taps", 760, "piece", "Heavy Duty", "Brass", "1/2 inch", "Chrome", False, "swan"),

    # ---- Plumbing: pipes & fittings ----
    ("PVC Pipe 1.5 inch", "Pipes", "PVC Pipes", 190, "piece", "Standard", "PVC", "1.5 inch", "White", False, "pipe"),
    ("PVC Pipe 2 inch", "Pipes", "PVC Pipes", 260, "piece", "Standard", "PVC", "2 inch", "White", False, "pipe"),
    ("PVC Pipe 4 inch", "Pipes", "PVC Pipes", 520, "piece", "Heavy Duty", "PVC", "4 inch", "White", False, "pipe"),
    ("CPVC Pipe 1 inch", "Pipes", "CPVC Pipes", 340, "piece", "Standard", "CPVC", "1 inch", "Cream", False, "pipe"),
    ("SWR Drainage Pipe 3 inch", "Pipes", "Drainage Pipes", 390, "piece", "Heavy Duty", "PVC", "3 inch", "Grey", False, "pipe"),
    ("Water Tank Pipe 1.25 inch", "Pipes", "Water Pipes", 230, "piece", "Standard", "HDPE", "1.25 inch", "Black", False, "pipe"),
    ("PVC Union 1 inch", "Fittings", "Union", 65, "piece", "Standard", "PVC", "1 inch", "White", False, "union"),
    ("PVC Reducer 2 to 1 inch", "Fittings", "Reducer", 38, "piece", "Standard", "PVC", "2x1 inch", "White", False, "coupler"),
    ("Brass Nipple 1/2 inch", "Fittings", "Brass Fittings", 75, "piece", "Heavy Duty", "Brass", "1/2 inch", "Gold", False, "coupler"),
    ("Brass Ball Valve 3/4 inch", "Fittings", "Brass Fittings", 310, "piece", "Heavy Duty", "Brass", "3/4 inch", "Gold", False, "valve"),
    ("GI Elbow 1 inch", "Fittings", "GI Fittings", 55, "piece", "Standard", "GI", "1 inch", "Silver", False, "elbow"),
    ("GI Tee 1 inch", "Fittings", "GI Fittings", 68, "piece", "Standard", "GI", "1 inch", "Silver", False, "tee"),
    ("Pipe Clamp 1 inch (10 pcs)", "Hardware", "Brackets & Clamps", 90, "pack", "Standard", "Steel", "1 inch", "Silver", False, "clamp"),

    # ---- Hardware ----
    ("Wood Screw 2 inch (100 pcs)", "Hardware", "Screws", 150, "pack", "Standard", "Steel", "2 inch", "Silver", False, "screw"),
    ("Wood Screw 3 inch (50 pcs)", "Hardware", "Screws", 170, "pack", "Standard", "Steel", "3 inch", "Silver", False, "screw"),
    ("Wire Nails 2 inch (1 kg)", "Hardware", "Nails", 85, "kg", "Standard", "Steel", "2 inch", "Silver", False, "nail"),
    ("Bolt Nut Washer Set (50 pcs)", "Hardware", "Bolts & Nuts", 210, "set", "Standard", "Steel", "M8", "Silver", False, "bolt"),
    ("Door Hinge 6 inch", "Hardware", "Hinges", 140, "piece", "Heavy Duty", "Stainless Steel", "6 inch", "Silver", False, "hinge"),
    ("Brass Door Handle Pair", "Hardware", "Handles & Latches", 780, "pair", "Premium", "Brass", "8 inch", "Gold", True, "handle"),
    ("Mortice Lock with Keys", "Hardware", "Locks", 1650, "piece", "Heavy Duty", "Steel", "Standard", "Silver", False, "lock"),
    ("Tower Bolt Latch 8 inch", "Hardware", "Handles & Latches", 120, "piece", "Standard", "Steel", "8 inch", "Silver", False, "latch"),
    ("Shelf Bracket 10 inch", "Hardware", "Brackets & Clamps", 95, "piece", "Standard", "Steel", "10 inch", "Black", False, "bracket"),
    ("U Clamp 2 inch (10 pcs)", "Hardware", "Brackets & Clamps", 110, "pack", "Standard", "GI", "2 inch", "Silver", False, "clamp"),

    # ---- Tiles ----
    ("Floor Tile 600x600 Glossy Grey", "Tiles", "Floor Tiles", 820, "box", "Standard", "Vitrified", "600x600 mm", "Grey", False, "tile"),
    ("Anti Skid Floor Tile 600x600", "Tiles", "Floor Tiles", 690, "box", "Standard", "Ceramic", "600x600 mm", "Brown", False, "tile_dots"),
    ("Kitchen Wall Tile 300x450", "Tiles", "Kitchen Tiles", 480, "box", "Standard", "Ceramic", "300x450 mm", "Cream", False, "tile"),
    ("Designer Wall Tile 300x600", "Tiles", "Designer Tiles", 640, "box", "Premium", "Ceramic", "300x600 mm", "Multicolor", True, "tile_designer"),
    ("Marble Finish Floor Tile 800x800", "Tiles", "Marble Finish", 1450, "box", "Premium", "Vitrified", "800x800 mm", "White", False, "tile_marble"),
    ("Granite Finish Floor Tile 600x600", "Tiles", "Granite Finish", 960, "box", "Premium", "Vitrified", "600x600 mm", "Black", False, "tile_dots"),

    # ---- Tools ----
    ("Combination Plier 8 inch", "Tools", None, 280, "piece", "Heavy Duty", "Steel", "8 inch", "Red", False, "pliers"),
    ("Pipe Wrench 14 inch", "Tools", None, 720, "piece", "Heavy Duty", "Steel", "14 inch", "Red", False, "pipewrench"),
    ("Measuring Tape 5 m", "Tools", None, 160, "piece", "Standard", "Steel", "5 m", "Yellow", False, "tape"),
    ("Spanner Set 12 pcs", "Tools", None, 890, "set", "Heavy Duty", "Chrome Vanadium", "6-32 mm", "Silver", True, "spanner"),
    ("Plastic Tool Box 16 inch", "Tools", None, 540, "piece", "Standard", "Plastic", "16 inch", "Red", False, "toolbox"),
    ("Hacksaw Frame with Blade", "Tools", None, 230, "piece", "Standard", "Steel", "12 inch", "Black", False, "saw"),

    # ---- Machines ----
    ("Welding Machine 200A", "Machines", "Welding Machines", 8900, "piece", "Heavy Duty", "Metal", "200 A", "Red", False, "welder"),
    ("Water Pump 1 HP", "Machines", "Pumps", 5400, "piece", "Standard", "Cast Iron", "1 HP", "Blue", True, "pump"),
    ("Pressure Pump 0.5 HP", "Machines", "Pumps", 3900, "piece", "Standard", "Cast Iron", "0.5 HP", "Black", False, "pump"),

    # ---- Construction materials & accessories ----
    ("Tile Adhesive 20 kg", "Construction Materials", None, 520, "bag", "Standard", "Cement Based", "20 kg", "Grey", False, "bag"),
    ("Waterproofing Compound 5 L", "Construction Materials", None, 680, "can", "Standard", "Polymer", "5 L", "White", False, "can"),
    ("Binding Wire 1 kg", "Construction Materials", None, 95, "kg", "Standard", "Steel", "1 kg", "Silver", False, "roll"),
    ("PTFE Thread Seal Tape", "Accessories", None, 25, "piece", "Standard", "PTFE", "12 mm", "White", False, "roll"),
    ("PVC Solvent Cement 100 ml", "Accessories", None, 70, "piece", "Standard", "Solvent", "100 ml", "Clear", False, "can"),
]

# percent discount applied (demo data) so the "Best Deals" row has content
DISCOUNTS = {
    "Brass Water Tap": 12, "Pillar Cock Tap": 10, "Chrome Bathroom Shower Set": 15,
    "Wall Mounted Wash Basin": 8, "Designer Floor Tile 600x600": 10, "Drilling Machine 13mm": 14,
    "Steel Claw Hammer": 10, "Adjustable Wrench 10 inch": 12, "Brass Door Lock": 9,
    "Swan Neck Tap": 18, "Basin Mixer Tap": 11, "Water Pump 1 HP": 13,
    "Marble Finish Floor Tile 800x800": 16, "Spanner Set 12 pcs": 20, "Overhead Shower 8 inch": 7,
}

# gallery demo images (generated by gen_images.py): (title, category, filename)
GALLERY_DEMO = [
    ("Showroom front", "Shop", "showroom-front.svg"),
    ("Shop interior", "Shop", "shop-interior.svg"),
    ("Sanitary display", "Sanitary", "sanitary-display.svg"),
    ("Bathroom fittings display", "Sanitary", "taps-display.svg"),
    ("Tiles display", "Tiles", "tiles-display.svg"),
    ("Hardware shelves", "Hardware", "hardware-shelves.svg"),
    ("Tools display", "Tools", "tools-display.svg"),
    ("Machine corner", "Machines", "machine-corner.svg"),
    ("Packaging and delivery", "Shop", "packaging-delivery.svg"),
    ("Pipes and fittings rack", "Hardware", "pipes-rack.svg"),
]

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS = os.path.join(BACKEND_DIR, "uploads")
IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".svg")


def find_image(folder, slug):
    """Return '/uploads/<folder>/<slug>.<ext>' if such a file exists, else None."""
    for ext in IMG_EXTS:
        if os.path.exists(os.path.join(UPLOADS, folder, slug + ext)):
            return f"/uploads/{folder}/{slug}{ext}"
    return None


def run():
    app = create_app()
    with app.app_context():
        print("Creating database tables…")
        db.create_all()
        ensure_columns()

        # ---------- admin user ----------
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", email="admin@mhardware.com")
            admin.set_password("admin123")     # CHANGE THIS AFTER FIRST LOGIN
            db.session.add(admin)
            print("✔ Admin created  →  username: admin   password: admin123")
        else:
            print("• Admin already exists")

        # ---------- settings ----------
        for key, value in DEFAULTS.items():
            if not Setting.query.filter_by(key=key).first():
                db.session.add(Setting(key=key, value=value))
        print("✔ Default settings inserted")

        # ---------- categories ----------
        created = {}
        for i, (cat_name, subs) in enumerate(CATEGORY_TREE.items()):
            cat = Category.query.filter_by(name=cat_name, parent_id=None).first()
            if not cat:
                cat = Category(name=cat_name, slug=slugify(cat_name), sort_order=i)
                db.session.add(cat)
                db.session.flush()
                print(f"  + Category: {cat_name}")
            created[cat_name] = cat

            for j, sub_name in enumerate(subs):
                if not Category.query.filter_by(name=sub_name, parent_id=cat.id).first():
                    db.session.add(Category(
                        name=sub_name,
                        slug=slugify(f"{cat_name}-{sub_name}"),
                        parent_id=cat.id,
                        sort_order=j,
                    ))
        db.session.commit()
        print("✔ Categories & subcategories inserted")

        # ---------- products ----------
        for n, (name, cat_name, sub_name, price, unit, brand,
                material, size, color, featured, _icon) in enumerate(DEMO_PRODUCTS, 1):

            if Product.query.filter_by(name=name).first() or \
               Product.query.filter_by(slug=slugify(name)).first():
                continue

            cat = created.get(cat_name)
            sub = None
            if sub_name and cat:
                sub = Category.query.filter_by(name=sub_name, parent_id=cat.id).first()

            db.session.add(Product(
                name=name,
                slug=slugify(name),
                sku=f"MH-{n:03d}",
                category_id=(sub.id if sub else (cat.id if cat else None)),
                brand=brand,
                price=price,
                unit=unit,
                material=material,
                size=size,
                color=color,
                stock=5 + zlib.crc32(name.encode()) % 196,
                short_description=f"{name} - {material}, {size}",
                description=f"{name} ({brand}). Material: {material}. Size: {size}. "
                            "Suitable for homes and construction projects. Demo listing.",
                availability=True,
                featured=featured,
            ))
        db.session.commit()

        # demo discounts and images, only where none is set yet
        for p in Product.query.all():
            pct = DISCOUNTS.get(p.name)
            if pct and p.discount_price is None:
                p.discount_price = round(p.price * (100 - pct) / 100)
            if not p.image:
                p.image = find_image("products", p.slug)
        db.session.commit()
        from services.image_service import refresh_status
        for p in Product.query.all():
            refresh_status(p)
        db.session.commit()
        print(f"✔ Demo products inserted ({Product.query.count()} total)")

        # category images
        for cat in Category.query.filter_by(parent_id=None):
            if not cat.image:
                cat.image = find_image("categories", cat.slug)
        db.session.commit()

        # ---------- gallery ----------
        # repoint rows whose file is missing (old placeholder-N.jpg) to a demo image
        fallback = {cat: fn for _t, cat, fn in reversed(GALLERY_DEMO)}
        for g in GalleryImage.query.all():
            rel = (g.image or "").lstrip("/")
            if rel and not os.path.exists(os.path.join(BACKEND_DIR, rel)):
                fn = fallback.get(g.category)
                if fn and os.path.exists(os.path.join(UPLOADS, "gallery", fn)):
                    g.image = f"/uploads/gallery/{fn}"
        for i, (title, cat, fn) in enumerate(GALLERY_DEMO):
            path = f"/uploads/gallery/{fn}"
            if os.path.exists(os.path.join(UPLOADS, "gallery", fn)) and \
               not GalleryImage.query.filter_by(image=path).first():
                db.session.add(GalleryImage(title=title, category=cat, image=path, sort_order=i))
        db.session.commit()
        print("✔ Gallery inserted")

        print("\n✅ Database seeded successfully.\n")
        print("Next (optional): python scripts/generate_images.py --dry-run   (AI product images)")


if __name__ == "__main__":
    run()
