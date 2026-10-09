"""Apply image mapping + new products to the M Hardware DB. Writes reports to scratch dir.
Run: backend/venv/Scripts/python <this> (cwd = backend)."""
import csv, json, os, sys
from datetime import datetime
from PIL import Image

S = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.getcwd()
sys.path.insert(0, BACKEND)
from app import app
from database.db import db
from models import Product, Category
from utils import slugify

OUT = os.path.join(BACKEND, "uploads", "products")
cls = json.load(open(os.path.join(S, "cls_all.json"), encoding="utf-8"))
GENERIC = {"standard", "store brand", "premium", "heavy duty", "local", "generic"}
NO_PRICE = {"N15", "N16", "N17", "N18", "N19", "N51", "N54", "N56"}   # brand-mismatched or summed-part estimates


def ahash(path):
    im = Image.open(path).convert("L").resize((8, 8))
    px = list(im.getdata()); avg = sum(px) / 64
    return sum(1 << i for i, v in enumerate(px) if v > avg)


def similar(a, b):
    return bin(a ^ b).count("1") <= 6


def save_webp(src_file, slug):
    im = Image.open(os.path.join(S, "images", src_file))
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
    im.thumbnail((1000, 1000), Image.LANCZOS)
    path = os.path.join(OUT, slug + ".webp")
    im.save(path, "WEBP", quality=82, method=6)
    return f"/uploads/products/{slug}.webp"


def usable(x, brand):
    if x["kind"] != "product" or x.get("watermark") or x["quality"] == "poor":
        return False
    b = (x.get("brand") or "").strip().lower()
    return not b or b == (brand or "").strip().lower()


rank = {"high": 0, "medium": 1}
qrank = {"good": 0, "ok": 1}
mapping, new_rows = [], []

with app.app_context():
    # ---------- existing products ----------
    for p in Product.query.order_by(Product.id).all():
        cands = [x for x in cls if x.get("match_id") == p.id and x.get("match_conf") in rank and usable(x, p.brand)]
        cands.sort(key=lambda x: (rank[x["match_conf"]], qrank[x["quality"]]))
        if not cands:
            mapping.append([p.id, p.name, p.category.name if p.category else "", p.final_price, "existing",
                            p.image, "", "", "none", "no usable photo in folder" + (" (still fallback)" if p.image_status == "fallback" else "")])
            continue
        hashes, primary_src = [], ""
        if p.image_status == "ready" and p.image and os.path.isfile(BACKEND + p.image):
            try: hashes.append(ahash(BACKEND + p.image))
            except Exception: pass
        else:
            primary_src = cands.pop(0)["file"]
            p.image = save_webp(primary_src, p.slug)
            p.image_status, p.image_provider, p.image_updated_at = "ready", "manual", datetime.utcnow()
            hashes.append(ahash(os.path.join(S, "images", primary_src)))
        extras, extra_src = list(p.extra_images()), []
        for x in cands:
            if len(extra_src) >= 3: break
            h = ahash(os.path.join(S, "images", x["file"]))
            if any(similar(h, k) for k in hashes): continue
            hashes.append(h)
            extras.append(save_webp(x["file"], f"{p.slug}-{len(extras) + 2}"))
            extra_src.append(x["file"])
        p.additional_images = json.dumps(extras) if extras else p.additional_images
        conf = "high" if (primary_src and any(c.get("file") == primary_src and c["match_conf"] == "high" for c in cls)) else "medium"
        mapping.append([p.id, p.name, p.category.name if p.category else "", p.final_price, "existing",
                        p.image, " ".join(extras), " ".join(filter(None, [primary_src] + extra_src)), conf,
                        ("new primary photo; " if primary_src else "kept your uploaded photo; ") + f"{len(extra_src)} gallery photo(s) added"])

    # ---------- new products ----------
    prices = {r["key"]: r for f in ("new_prices_a.json", "new_prices_b.json") for r in json.load(open(os.path.join(S, f), encoding="utf-8"))}
    rows = list(csv.DictReader(open(os.path.join(S, "new_products.tsv"), encoding="utf-8"), delimiter="\t"))
    next_no = max(int((p.sku or "MH-0").split("-")[-1]) for p in Product.query.all()) + 1
    for r in rows:
        if Product.query.filter(db.func.lower(Product.name) == r["name"].lower()).first():
            continue
        pr = prices.get(r["key"], {})
        typical = pr.get("typical")
        price = float(typical) if typical and r["key"] not in NO_PRICE else 0.0
        cat = Category.query.filter_by(name=r["category"]).first()
        base = slugify(r["name"]); slug = base; i = 2
        while Product.query.filter_by(slug=slug).first():
            slug = f"{base}-{i}"; i += 1
        files = r["images"].split(",")
        img = save_webp(files[0], slug)
        extras = [save_webp(f, f"{slug}-{n + 2}") for n, f in enumerate(files[1:])]
        brand = None if r["brand"] == "Generic" else r["brand"]
        desc = pr.get("description") or r["name"]
        p = Product(name=r["name"], slug=slug, category_id=cat.id if cat else None, brand=brand,
                    sku=f"MH-{next_no:03d}", description=desc, short_description=desc[:300],
                    price=price, unit=(pr.get("unit") or "piece"), stock=0, availability=True,
                    image=img, additional_images=json.dumps(extras) if extras else None,
                    image_status="ready", image_provider="manual", image_updated_at=datetime.utcnow(),
                    material=pr.get("material"), size=pr.get("size"), color=pr.get("color"), finish=pr.get("finish"))
        db.session.add(p); next_no += 1
        conf = pr.get("confidence") or "low"
        new_rows.append([p.sku, r["name"], brand or "", r["category"], price or "Price on request",
                         pr.get("low"), pr.get("typical"), pr.get("high"), pr.get("unit"), pr.get("sources"), "2026-10-09",
                         img + (" " + " ".join(extras) if extras else ""), r["images"], "medium" if brand else "low",
                         conf if price else "not_found", pr.get("notes") or ("price withheld: estimate not from an exact listing" if r["key"] in NO_PRICE else "")])
    db.session.commit()

with open(os.path.join(S, "product_image_mapping.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["id", "name", "category", "price", "price_source", "primary_image", "gallery_images", "original_files", "match_confidence", "note"]); w.writerows(mapping)
with open(os.path.join(S, "new_products_report.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["sku", "name", "brand", "category", "listed_price", "low", "typical", "high", "unit", "sources", "date_checked", "images", "original_files", "id_confidence", "price_confidence", "notes"]); w.writerows(new_rows)
print("existing updated:", sum(1 for m in mapping if m[8] != "none"), "| new products:", len(new_rows),
      "| new without price:", sum(1 for n in new_rows if n[4] == "Price on request"))
