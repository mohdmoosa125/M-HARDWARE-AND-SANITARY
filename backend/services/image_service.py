"""
image_service.py
----------------
Orchestrator of the Image Agent. Reusable from the CLI, the admin API and product hooks.

    process_product_image(product, force=False, provider=None, log=print) -> result dict

Priority per product:
    1. valid existing image          -> kept (no API call, no cost)
    2. reference image               -> processed locally (no API call)
    3. configured AI provider chain  -> only providers listed in .env that have a key
    4. SVG fallback                  -> image_status = "fallback"

Only product.image and the image_* bookkeeping columns are ever modified.
Statuses: missing | processing | ready | fallback | failed
"""
import os
import threading
import time
import uuid
from datetime import datetime

from database.db import db
from models import Product
from services import image_generation as gen
from services.image_processor import process
from services.image_validator import check_bytes, find_duplicate, local_path, validate
from services.prompt_builder import build_prompt
from services.image_research import research
from services.svg_fallback import save_svg

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_DIR = os.path.join(BACKEND, "uploads", "references")
REF_EXTS = ("jpg", "jpeg", "png", "webp")

_in_progress = set()        # product ids being processed right now (this process)


def reference_dir():
    """REFERENCE_DIR from .env (relative paths resolve from the project root)."""
    custom = os.getenv("REFERENCE_DIR")
    if custom:
        return custom if os.path.isabs(custom) else os.path.join(os.path.dirname(BACKEND), custom)
    return REF_DIR


# ------------------------------------------------------------------ status
def evaluate(product):
    """(status, reason) derived from the file on disk: missing | fallback | ready."""
    if not product.image:
        return "missing", "no image"
    path = local_path(product.image)
    if path is None:                                   # external URL: leave it alone
        return "ready", "external image"
    if not os.path.isfile(path):
        return "missing", "image file not found"
    if path.lower().endswith(".svg"):
        return "fallback", "SVG placeholder"
    ok, reason = validate(path)
    return ("ready", "ok") if ok else ("missing", f"broken image: {reason}")


def refresh_status(product):
    """Recompute and store image_status. A stored 'failed'/'processing' is kept while it still applies."""
    status, reason = evaluate(product)
    if product.id in _in_progress:
        return "processing", "in progress"
    if status == "missing" and product.image_status == "failed":
        return "failed", product.image_error or reason
    if product.image_status != status:
        product.image_status = status
        product.image_updated_at = product.image_updated_at or datetime.utcnow()
    return status, reason


def find_reference(product):
    """User-provided reference by slug, SKU, product id or an explicit filename match."""
    folder = reference_dir()
    names = [product.slug, (product.sku or "").lower(), str(product.id)]
    for name in filter(None, names):
        for ext in REF_EXTS:
            path = os.path.join(folder, f"{name}.{ext}")
            if os.path.isfile(path):
                return path
    return None


def _file_slug(product):
    """<slug>, or <slug>-2, -3 ... when that file already belongs to another product."""
    base, slug, n = product.slug, product.slug, 2
    while Product.query.filter(Product.image == f"/uploads/products/{slug}.webp",
                               Product.id != product.id).first():
        slug, n = f"{base}-{n}", n + 1
    return slug


def _set(product, status, provider=None, error=None):
    product.image_status = status
    product.image_provider = provider
    product.image_error = (error or None) and str(error)[:250]
    product.image_updated_at = datetime.utcnow()


# ------------------------------------------------------------------ plan (dry run)
def plan_product(product, force=False, provider=None):
    """What WOULD happen. Makes no API call and writes nothing."""
    status, reason = refresh_status(product)
    chain = gen.usable_chain(provider)
    ref = find_reference(product)
    prompt, _neg = build_prompt(product, research(product))
    if status == "ready" and not force:
        action, op = "SKIP (valid image kept)", "none"
    elif ref:
        action, op = "USE REFERENCE IMAGE", "local image processing"
    elif chain:
        action, op = f"GENERATE via {' -> '.join(chain)}", "paid API call(s)"
    elif status == "fallback" and not force:
        action, op = "SKIP (SVG in place, no provider configured)", "none"
    else:
        action, op = "SVG FALLBACK (no provider configured)", "local SVG"
    cat = product.category.name if product.category else "-"
    return {"id": product.id, "name": product.name, "category": cat, "status": status,
            "reason": reason, "providers": chain, "configured": gen.configured_chain(provider),
            "reference": os.path.basename(ref) if ref else None, "prompt": prompt,
            "action": action, "operation": op}


# ------------------------------------------------------------------ one product
def process_product_image(product, force=False, provider=None, log=print):
    """Make sure one product has an image. Returns {"status", "detail"} where status is
    skip | generated | reference | fallback | failed."""
    status, reason = refresh_status(product)
    if status == "ready" and not force:
        db.session.commit()
        return {"status": "skip", "detail": "valid image exists"}

    ref = find_reference(product)
    chain = [] if ref else gen.usable_chain(provider)
    if status == "fallback" and not force and not ref and not chain:
        db.session.commit()
        return {"status": "skip", "detail": "SVG fallback in place; no provider configured"}

    _in_progress.add(product.id)
    old_image, was_ready = product.image, status == "ready"
    slug = made_slug = None
    error = None
    try:
        raw, used, centre = None, None, False
        if ref:
            log(f"           Source: reference image ({os.path.basename(ref)})")
            with open(ref, "rb") as f:
                raw, used, centre = f.read(), "reference", True
        elif chain:
            prompt, negative = build_prompt(product, research(product))
            res = gen.generate_with_fallback(prompt, negative, None, chain, log, accept=check_bytes)
            if res["success"]:
                raw, used = res["image_bytes"], f"{res['provider']}:{res['model']}"
            else:
                error = res["error"]
        else:
            error = "no provider configured (set IMAGE_PROVIDER and its API key in .env)"

        if raw is not None:
            slug = _file_slug(product)
            try:
                url = process(raw, slug, centre_subject=centre)
                path = local_path(url)
                ok, why = validate(path, strict=True)
                if not ok:
                    raise ValueError(why)
            except Exception as e:                       # bad output: remove it, never keep a broken file
                for ext in ("webp", "jpg"):
                    p = os.path.join(BACKEND, "uploads", "products", f"{slug}.{ext}")
                    if os.path.isfile(p) and product.image != f"/uploads/products/{slug}.{ext}":
                        os.remove(p)
                error = f"processing/validation failed: {e}"
                raw = None

        if raw is not None:
            dup = find_duplicate(path, product)
            note = f"possible duplicate of product #{dup} (review)" if dup else None
            product.image = url
            _set(product, "ready", "reference" if used == "reference" else used, note)
            db.session.commit()
            kb = os.path.getsize(path) // 1024
            return {"status": "reference" if used == "reference" else "generated",
                    "detail": f"{used} -> {os.path.basename(url)} ({kb} KB)" + (f"; {note}" if note else "")}

        # ---- nothing worked: keep a valid old image, otherwise SVG fallback
        if was_ready:
            _set(product, "ready", product.image_provider, f"regeneration failed: {error}")
            db.session.commit()
            return {"status": "failed", "detail": f"kept existing image ({error})"}
        product.image = save_svg(product, product.slug)
        _set(product, "fallback", "svg", error)
        db.session.commit()
        return {"status": "fallback", "detail": f"SVG fallback used ({error})"}
    except Exception as e:
        db.session.rollback()
        product = db.session.get(Product, product.id)
        _set(product, "failed", None, f"{type(e).__name__}: {e}")
        db.session.commit()
        return {"status": "failed", "detail": f"{type(e).__name__}: {e}"}
    finally:
        _in_progress.discard(product.id)


# ------------------------------------------------------------------ hooks for product routes
def mark_manual_image(product):
    """Admin uploaded/set an image by hand: it always wins over generated ones."""
    status, _ = evaluate(product)
    _set(product, status if product.image else "missing", "manual" if product.image else None)


def on_product_created(app, product):
    """New product: status is derived from its image. Auto-generation only if explicitly enabled."""
    if product.image:
        mark_manual_image(product)
        return
    _set(product, "missing")
    if os.getenv("AUTO_GENERATE_PRODUCT_IMAGES", "false").lower() == "true" and gen.usable_chain():
        db.session.commit()
        start_job(app, [product.id])


# ------------------------------------------------------------------ selection
def select_products(mode="missing", product_id=None, category=None, limit=None):
    from models import Category
    q = Product.query.order_by(Product.id)
    if product_id:
        q = q.filter(Product.id == product_id)
    if category:
        cat = Category.query.filter((Category.slug == category) | (Category.name.ilike(category))).first()
        ids = ([cat.id] + [c.id for c in cat.children]) if cat else [-1]
        q = q.filter(Product.category_id.in_(ids))
    items = q.all()
    if mode == "missing":
        items = [p for p in items if refresh_status(p)[0] in ("missing", "fallback", "failed")]
    return items[:limit] if limit else items


# ------------------------------------------------------------------ batch
def run_batch(products, force=False, provider=None, batch=5, log=print, cancel=None,
              on_start=None, on_done=None, pause=1.0):
    """Process products one by one; a failure never stops the batch. Returns a summary."""
    gen.reset_run_state()
    t0 = time.time()
    s = {"total": len(products), "skip": 0, "generated": 0, "reference": 0,
         "fallback": 0, "failed": 0, "results": [], "cancelled": False}
    api_used = False
    for i, p in enumerate(products, 1):
        if cancel and cancel.is_set():
            s["cancelled"] = True
            log("Cancelled.")
            break
        if on_start:
            on_start(i, len(products), p)
        log(f"[{i}/{len(products)}] {p.name}")
        res = process_product_image(p, force=force, provider=provider, log=log)
        log(f"           Result: {res['status'].upper()} - {res['detail']}")
        s[res["status"]] += 1
        s["results"].append({"id": p.id, "name": p.name, **res})
        api_used = api_used or res["status"] in ("generated", "fallback", "failed") and bool(gen.usable_chain(provider))
        if on_done:
            on_done(i, len(products), p, res)
        if api_used and i % batch == 0 and i < len(products):
            time.sleep(pause)                          # respect provider rate limits
    s["seconds"] = round(time.time() - t0, 1)
    return s


# ------------------------------------------------------------------ background jobs (in memory)
# NOTE: jobs live in this process only; they are lost when the server restarts.
JOBS = {}


def active_job():
    return next((j for j in JOBS.values() if j["state"] == "running"), None)


def start_job(app, product_ids, force=False, provider=None):
    """Run a batch in a background thread. Returns job id (or the running job's id)."""
    running = active_job()
    if running:
        return running["id"]
    job = {"id": uuid.uuid4().hex[:10], "state": "running", "total": len(product_ids),
           "processed": 0, "succeeded": 0, "failed": 0, "fallback": 0, "skipped": 0,
           "current_product": "", "current_provider": "", "log": [], "summary": None,
           "cancel": threading.Event()}
    JOBS[job["id"]] = job

    def on_start(i, total, p):
        chain = gen.usable_chain(provider)
        job["current_product"] = p.name
        job["current_provider"] = ", ".join(chain) if chain else "none (local only)"

    def on_done(i, total, p, res):
        job["processed"] = i
        key = {"generated": "succeeded", "reference": "succeeded", "fallback": "fallback",
               "failed": "failed", "skip": "skipped"}[res["status"]]
        job[key] += 1

    def worker():
        with app.app_context():
            try:
                products = Product.query.filter(Product.id.in_(product_ids)).order_by(Product.id).all()
                job["summary"] = run_batch(products, force=force, provider=provider, cancel=job["cancel"],
                                           on_start=on_start, on_done=on_done,
                                           log=lambda m: job["log"].append(m))
                job["state"] = "cancelled" if job["cancel"].is_set() else "done"
            except Exception as e:
                job["state"], job["error"] = "error", f"{type(e).__name__}: {e}"
            finally:
                job["current_product"] = job["current_provider"] = ""

    threading.Thread(target=worker, daemon=True).start()
    return job["id"]


def job_public(job):
    out = {k: v for k, v in job.items() if k not in ("cancel", "log")}
    out["log"] = job["log"][-30:]
    return out


# ------------------------------------------------------------------ report
def report():
    """Live image status of every product plus counts."""
    counts = {"ready": 0, "missing": 0, "processing": 0, "fallback": 0, "failed": 0}
    rows, review = {}, []
    for p in Product.query.order_by(Product.id):
        status, reason = refresh_status(p)
        counts[status] = counts.get(status, 0) + 1
        rows[p.id] = {"status": status, "reason": reason, "provider": p.image_provider,
                      "error": p.image_error}
        if p.image_error and p.image_error.startswith("possible duplicate"):
            review.append(p.id)
    db.session.commit()
    counts["total"] = len(rows)
    return {"counts": counts, "products": rows, "review": review,
            "providers_configured": gen.configured_chain(),
            "providers_usable": gen.usable_chain()}
