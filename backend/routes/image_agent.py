"""Admin endpoints for the Image Agent (all protected by the existing admin_required)."""
from flask import Blueprint, request, current_app
from database.db import db
from models import Product
from services import image_generation as gen
from services import image_service as svc
from utils import ok, fail, admin_required

image_agent_bp = Blueprint("image_agent", __name__, url_prefix="/api/admin/images")


def _start(products, force=False):
    running = svc.active_job()
    if running:
        return fail(f"Job {running['id']} is already running", 409)
    if not products:
        return ok({"job_id": None, "total": 0}, message="No products need images")
    job_id = svc.start_job(current_app._get_current_object(), [p.id for p in products], force=force)
    return ok({"job_id": job_id, "total": len(products), "providers": gen.usable_chain()})


@image_agent_bp.post("/generate-missing")
@admin_required
def generate_missing():
    data = request.get_json(silent=True) or {}
    limit = int(data.get("limit") or 0) or None
    return _start(svc.select_products("missing", limit=limit))


@image_agent_bp.post("/generate-all")
@admin_required
def generate_all():
    data = request.get_json(silent=True) or {}
    if data.get("confirm") is not True:
        return fail("Send {\"confirm\": true} to regenerate every product image")
    return _start(svc.select_products("all"), force=True)


@image_agent_bp.post("/regenerate/<int:pid>")
@admin_required
def regenerate(pid):
    """Regenerate one product image (runs inline; may take a little while)."""
    product = db.session.get(Product, pid)
    if not product:
        return fail("Product not found", 404)
    gen.reset_run_state()
    result = svc.process_product_image(product, force=True)
    return ok({"result": result, "image": product.image, "image_status": product.image_status})


@image_agent_bp.get("/status/<job_id>")
@admin_required
def job_status(job_id):
    job = svc.JOBS.get(job_id)
    return ok(svc.job_public(job)) if job else fail("Job not found", 404)


@image_agent_bp.post("/cancel/<job_id>")
@admin_required
def job_cancel(job_id):
    job = svc.JOBS.get(job_id)
    if not job:
        return fail("Job not found", 404)
    job["cancel"].set()
    return ok({"id": job_id}, message="Cancelling after the current product")


@image_agent_bp.get("/report")
@admin_required
def image_report():
    return ok(svc.report())
