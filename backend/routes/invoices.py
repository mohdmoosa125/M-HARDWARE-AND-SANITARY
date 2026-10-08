"""Invoices: JSON, print-ready HTML and PDF. Access follows the order's access rules."""
from flask import Blueprint, request, Response, url_for
from sqlalchemy import or_

from database.db import db
from models import Invoice, Order
from routes.orders import can_view
from services import invoice_service
from services.product_service import paginate
from utils import ok, fail, admin_required, is_admin, clean

invoices_bp = Blueprint("invoices", __name__)


def _find(ident):
    if str(ident).isdigit():
        return db.session.get(Invoice, int(ident))
    return Invoice.query.filter_by(invoice_number=str(ident)).first()


def _allowed(ident):
    inv = _find(ident)
    if not inv or not can_view(inv.order, request.args.get("t")):
        return None
    return inv


def _pdf_url(inv):
    url = url_for("invoices.invoice_pdf", ident=inv.invoice_number)
    t = request.args.get("t")
    return f"{url}?t={t}" if t else url


@invoices_bp.get("/api/invoices")
@admin_required
def list_invoices():
    q = Invoice.query.join(Order)
    term = clean(request.args.get("q"), 80)
    if term:
        like = f"%{term}%"
        q = q.filter(or_(Invoice.invoice_number.ilike(like), Order.order_number.ilike(like),
                         Order.shipping_name.ilike(like), Order.shipping_phone.ilike(like)))
    q = q.order_by(Invoice.issued_at.desc())
    items, meta = paginate(q, request.args.get("page", 1), request.args.get("limit", 50))
    return ok([{
        "id": i.id, "invoice_number": i.invoice_number,
        "issued_at": i.issued_at.isoformat() if i.issued_at else None,
        "order_id": i.order_id, "order_number": i.order.order_number,
        "customer": i.order.shipping_name, "phone": i.order.shipping_phone,
        "grand_total": i.order.grand_total, "payment_status": i.order.payment_status,
        "status": i.order.status_key,
    } for i in items], meta=meta)


@invoices_bp.get("/api/invoices/<ident>")
def get_invoice(ident):
    inv = _allowed(ident)
    if not inv:
        return fail("Invoice not found", 404)
    return ok(inv.to_dict(admin=is_admin()))


@invoices_bp.get("/invoice/<ident>")
@invoices_bp.get("/api/invoices/<ident>/print")
def invoice_page(ident):
    inv = _allowed(ident)
    if not inv:
        return Response("<h1>Invoice not found</h1>", status=404, mimetype="text/html")
    html = invoice_service.render_html(inv, _pdf_url(inv), autoprint=request.args.get("print") == "1")
    return Response(html, mimetype="text/html")


@invoices_bp.get("/invoice/<ident>/pdf")
@invoices_bp.get("/api/invoices/<ident>/pdf")
def invoice_pdf(ident):
    inv = _allowed(ident)
    if not inv:
        return fail("Invoice not found", 404)
    try:
        pdf = invoice_service.render_pdf(inv)
    except ImportError:
        return fail("PDF download is not available (reportlab not installed). Use Print instead.", 503)
    return Response(pdf, mimetype="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{inv.invoice_number}.pdf"',
        "Cache-Control": "private, no-store",
    })
