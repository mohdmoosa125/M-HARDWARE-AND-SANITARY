"""
image_validator.py
------------------
Checks that an image file is usable. Deliberately NOT strict about style:
a clean white-background product photo is valid.

    validate(path)             -> (ok, reason)   existing / admin-uploaded images
    validate(path, strict=True)-> (ok, reason)   images produced by the agent (1000+ px, square)
    check_bytes(raw)           -> (ok, reason)   raw provider output, before processing
    find_duplicate(path, product) -> product id or None   (perceptual hash; review flag only)
"""
import io
import os

from PIL import Image

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MIN_BYTES, MAX_BYTES = 2 * 1024, 8 * 1024 * 1024
MIN_SIDE_EXISTING = 200         # small supplier photos are still acceptable
MIN_SIDE_GENERATED = 1000
RAW_MIN_SIDE = 512              # provider output, upscaled by the processor
VALID_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}

_hash_cache = {}                # (path, mtime) -> 64-bit average hash


def local_path(url):
    """'/uploads/products/x.webp' -> absolute file path (None if not a local upload)."""
    if not url or not url.startswith("/uploads/"):
        return None
    return os.path.join(BACKEND, url.lstrip("/").replace("/", os.sep))


def _check_image(img, min_side, square):
    w, h = img.size
    if w < min_side or h < min_side:
        return f"too small ({w}x{h}, need {min_side}+)"
    ratio = w / h
    if square and abs(ratio - 1) > 0.08:
        return f"not square ({w}x{h})"
    if not 0.4 <= ratio <= 2.5:
        return f"odd aspect ratio ({w}x{h})"
    return None


def check_bytes(raw):
    if not raw:
        return False, "empty response"
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        return False, "not a readable image"
    problem = _check_image(img, RAW_MIN_SIDE, square=False)
    return (False, problem) if problem else (True, "ok")


def validate(path, strict=False):
    if not path or not os.path.isfile(path):
        return False, "file missing"
    size = os.path.getsize(path)
    if size < MIN_BYTES:
        return False, f"file too small ({size} bytes)"
    if size > MAX_BYTES:
        return False, f"file too large ({size // 1024} KB)"
    try:
        with Image.open(path) as img:
            img.load()
            if img.format not in VALID_FORMATS:
                return False, f"unsupported type {img.format}"
            if img.mode in ("RGBA", "LA") and img.getchannel("A").getextrema()[1] == 0:
                return False, "fully transparent"
            problem = _check_image(img, MIN_SIDE_GENERATED if strict else MIN_SIDE_EXISTING, strict)
    except Exception:
        return False, "cannot open image (corrupt?)"
    return (False, problem) if problem else (True, "ok")


def average_hash(path):
    key = (path, os.path.getmtime(path))
    if key not in _hash_cache:
        with Image.open(path) as im:
            small = im.convert("L").resize((8, 8), Image.LANCZOS)
        px = list(small.getdata())
        avg = sum(px) / 64
        _hash_cache[key] = sum(1 << i for i, v in enumerate(px) if v >= avg)
    return _hash_cache[key]


def find_duplicate(path, product):
    """Id of another product whose image is visually near-identical (Hamming <= 3), else None.
    Used only to flag an image for review, never to reject it."""
    from models import Product
    mine = average_hash(path)
    for other in Product.query.filter(Product.id != product.id, Product.image.isnot(None)):
        op = local_path(other.image)
        if not op or op.lower().endswith(".svg") or not os.path.isfile(op):
            continue
        try:
            if bin(mine ^ average_hash(op)).count("1") <= 3:
                return other.id
        except Exception:
            continue
    return None
