"""
category_image.py
-----------------
Category cover images: AI provider chain first (same providers/keys as the
product Image Agent), otherwise the best real product photo in that category.
Never invents an image when neither exists.
"""
import io
import os

from config import BASE_DIR
from models import Product
from services import image_generation as gen

UPLOADS = os.path.join(BASE_DIR, "uploads", "categories")

NEGATIVE = "text, watermark, logo, people, hands, blurry, distorted, low quality, cartoon"


def _prompt(cat):
    family = cat.parent.name if cat.parent else cat.name
    return (f"Professional e-commerce category banner photo for '{cat.name}' ({family}) at an Indian "
            f"hardware and sanitary store. A clean arrangement of typical {cat.name.lower()} products, "
            "studio lighting, soft shadows, neutral light background, sharp focus, catalog quality, "
            "no text, no logos.")


def _save(raw, slug):
    from PIL import Image, ImageOps
    img = Image.open(io.BytesIO(raw))
    img.load()
    img = ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), (1200, 900))
    os.makedirs(UPLOADS, exist_ok=True)
    img.save(os.path.join(UPLOADS, f"{slug}-ai.webp"), "WEBP", quality=85)
    img.save(os.path.join(UPLOADS, f"{slug}-ai.jpg"), "JPEG", quality=88, optimize=True)
    return f"/uploads/categories/{slug}-ai.webp"


def _best_product_image(cat):
    ids = [cat.id] + [c.id for c in cat.children]
    p = (Product.query.filter(Product.category_id.in_(ids), Product.image_status == "ready",
                              Product.image.isnot(None))
         .order_by(Product.featured.desc(), Product.stock.desc()).first())
    return p.image if p else None


def generate(cat):
    """Returns (path, source, error)."""
    if gen.usable_chain():
        res = gen.generate_with_fallback(_prompt(cat), NEGATIVE, log=lambda *_: None)
        if res.get("success"):
            try:
                return _save(res["image_bytes"], cat.slug), f"AI: {res.get('provider')}", None
            except Exception as e:                       # corrupt bytes etc.
                error = f"Generated image could not be processed ({type(e).__name__})"
        else:
            error = f"AI generation failed: {res.get('error')}"
    else:
        error = "No AI image provider is configured (set IMAGE_PROVIDER and its key in .env)."
    photo = _best_product_image(cat)
    if photo:
        return photo, "best product photo", None
    return None, None, error + " No ready product photo in this category either — please upload an image."
