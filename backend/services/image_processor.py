"""
image_processor.py
------------------
Normalises raw image bytes into a 1200x1200 catalog image.

    process(raw_bytes, slug, centre_subject=False) -> "/uploads/products/<slug>.webp"

Steps: open -> EXIF rotate -> flatten transparency -> fit (contain, never crops the
product) onto a clean #f4f8fb square -> light sharpen -> save WebP (+ JPG fallback).
All disk writes go through save_image(), so storage can later move to S3/CDN
without touching the generation logic.
"""
import io
import os

from PIL import Image, ImageChops, ImageFilter, ImageOps

UPLOADS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
SIZE = 1200
BG = (244, 248, 251)            # #f4f8fb


def _remove_background(img):
    """Use rembg if installed (optional); otherwise None."""
    try:
        from rembg import remove
    except ImportError:
        return None
    try:
        return remove(img.convert("RGBA"))
    except Exception:
        return None


def _subject_box(img):
    """Bounding box of the subject: alpha if present, else pixels unlike the corner colour."""
    if img.mode == "RGBA":
        box = img.getchannel("A").point(lambda a: 255 if a > 20 else 0).getbbox()
        if box:
            return box
    rgb = img.convert("RGB")
    bg = Image.new("RGB", rgb.size, rgb.getpixel((2, 2)))
    diff = ImageChops.difference(rgb, bg).convert("L").point(lambda v: 255 if v > 24 else 0)
    return diff.getbbox()


def _fit_on_canvas(img, fill):
    """Scale so the whole image fits inside fill*SIZE and centre it on the background."""
    scale = SIZE * fill / max(img.size)
    img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGB", (SIZE, SIZE), BG)
    pos = ((SIZE - img.width) // 2, (SIZE - img.height) // 2)
    if img.mode == "RGBA":
        canvas.paste(img, pos, img)
    else:
        canvas.paste(img.convert("RGB"), pos)
    return canvas


def save_image(img, slug):
    """Write <slug>.webp (primary) and <slug>.jpg (fallback); return the public URL path."""
    folder = os.path.join(UPLOADS, "products")
    os.makedirs(folder, exist_ok=True)
    webp_path = os.path.join(folder, slug + ".webp")
    try:
        img.save(webp_path, "WEBP", quality=85, method=6)
    except Exception:                                  # rare encoder memory error: retry lighter
        img.save(webp_path, "WEBP", quality=85, method=4)
    img.save(os.path.join(folder, slug + ".jpg"), "JPEG", quality=88, optimize=True)
    return f"/uploads/products/{slug}.webp"


def process(raw_bytes, slug, centre_subject=False):
    img = Image.open(io.BytesIO(raw_bytes))
    img.load()
    img = ImageOps.exif_transpose(img)

    if centre_subject:                                 # user reference photos
        cut = _remove_background(img)
        img = cut if cut is not None else img
        box = _subject_box(img)
        if box:
            img = img.crop(box)
        fill = 0.80
    else:                                              # generated images are already framed
        fill = 1.0
    if img.mode in ("P", "LA"):
        img = img.convert("RGBA")

    img = _fit_on_canvas(img, fill)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    return save_image(img, slug)
