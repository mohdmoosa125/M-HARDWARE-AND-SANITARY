"""
invoice_service.py
------------------
Creates the invoice for an order and renders it as print-ready HTML or PDF.
Totals always come from the stored order (already computed server-side).
"""
import io
import json
from datetime import datetime

from flask import render_template_string

from database.db import db
from models import Invoice
from services import store_config
from utils import clean


def create_invoice(order, settings=None, year=None):
    """Called inside create_order()'s transaction (caller commits)."""
    from services.order_service import next_number
    settings = settings or store_config.all_settings()
    year = year or datetime.utcnow().year
    prefix = f"{clean(settings.get('invoice_prefix'), 10) or 'MHS'}-{year}"
    invoice = Invoice(
        invoice_number=next_number(Invoice.invoice_number, prefix),
        order_id=order.id,
        business_snapshot=json.dumps(store_config.business_snapshot(settings)),
    )
    db.session.add(invoice)
    db.session.flush()
    return invoice


def inr(value):
    """Indian digit grouping: 123456.5 -> 1,23,456.50"""
    value = round(float(value or 0), 2)
    neg = value < 0
    whole, frac = f"{abs(value):.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"{'-' if neg else ''}{whole}.{frac}"


PAYMENT_LABELS = {"cod": "Cash on Delivery / Pay at Store", "upi": "UPI", "online": "Online"}


def _context(invoice):
    order = invoice.order
    biz = invoice.business()
    issued = invoice.issued_at or datetime.utcnow()
    return {
        "inv": invoice, "o": order, "d": order.to_dict(admin=True), "biz": biz,
        "cur": biz.get("currency_symbol") or "₹", "inr": inr,
        "date": issued.strftime("%d %b %Y"),
        "payment_label": PAYMENT_LABELS.get(order.payment_method or "cod", order.payment_method),
    }


INVOICE_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Invoice {{ inv.invoice_number }} | {{ biz.name }}</title>
<meta name="robots" content="noindex">
<style>
  :root{--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--brand:#0f4c81;--bg:#f1f5f9}
  *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.5 Inter,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
  .bar{max-width:860px;margin:20px auto 0;display:flex;gap:8px;justify-content:flex-end;padding:0 16px;flex-wrap:wrap}
  .bar a,.bar button{font:inherit;font-weight:600;border:1px solid var(--line);background:#fff;color:var(--ink);
    padding:9px 16px;border-radius:10px;cursor:pointer;text-decoration:none}
  .bar .primary{background:var(--brand);border-color:var(--brand);color:#fff}
  .sheet{max-width:860px;margin:12px auto 40px;background:#fff;border-radius:16px;padding:40px;
    box-shadow:0 10px 30px rgba(15,23,42,.08)}
  .head{display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap;border-bottom:3px solid var(--brand);padding-bottom:20px}
  .brand h1{margin:0;font-size:22px;letter-spacing:.5px;color:var(--brand)}
  .brand p{margin:2px 0;color:var(--muted)} .title{text-align:right}
  .title h2{margin:0;font-size:26px;letter-spacing:3px;color:var(--ink)}
  .title table td{padding:1px 0 1px 12px} .title td:first-child{color:var(--muted)}
  .demo{margin-top:14px;background:#fef3c7;color:#92400e;border-radius:8px;padding:8px 12px;font-size:12px}
  .parties{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin:24px 0}
  .parties h3{margin:0 0 6px;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--muted)}
  .parties p{margin:2px 0}
  table.items{width:100%;border-collapse:collapse;margin-top:8px}
  .items th{background:#f8fafc;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.6px;
    color:var(--muted);padding:10px;border-bottom:1px solid var(--line)}
  .items td{padding:10px;border-bottom:1px solid var(--line);vertical-align:top}
  .num{text-align:right;white-space:nowrap} .sku{color:var(--muted);font-size:12px}
  .totals{margin-left:auto;margin-top:16px;width:320px;max-width:100%}
  .totals td{padding:6px 10px} .totals tr.grand td{border-top:2px solid var(--ink);font-size:17px;font-weight:700}
  .meta{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}
  .pill{border:1px solid var(--line);border-radius:999px;padding:4px 12px;font-size:12px}
  .foot{margin-top:32px;padding-top:16px;border-top:1px solid var(--line);text-align:center;color:var(--muted)}
  .foot strong{color:var(--ink);display:block;margin-bottom:4px}
  .cancelled{color:#b91c1c;font-weight:700}
  @media (max-width:640px){.sheet{padding:20px;border-radius:0}.parties{grid-template-columns:1fr}
    .title{text-align:left}.items .hide-sm{display:none}}
  @media print{body{background:#fff}.bar{display:none}.sheet{box-shadow:none;margin:0;max-width:none;padding:0;border-radius:0}
    @page{size:A4;margin:14mm}}
</style></head>
<body>
<div class="bar">
  <button class="primary" onclick="window.print()">Print</button>
  <a href="{{ pdf_url }}">Download PDF</a>
</div>
<div class="sheet">
  <div class="head">
    <div class="brand">
      <h1>{{ biz.name | upper }}</h1>
      {% if biz.address %}<p>{{ biz.address }}</p>{% endif %}
      <p>{% if biz.phone %}Phone: {{ biz.phone }}{% endif %}{% if biz.email %} · {{ biz.email }}{% endif %}</p>
      {% if biz.gstin %}<p>GSTIN: {{ biz.gstin }}</p>{% endif %}
    </div>
    <div class="title">
      <h2>INVOICE</h2>
      <table>
        <tr><td>Invoice No.</td><td><b>{{ inv.invoice_number }}</b></td></tr>
        <tr><td>Order No.</td><td>{{ d.order_number }}</td></tr>
        <tr><td>Date</td><td>{{ date }}</td></tr>
      </table>
    </div>
  </div>
  {% if biz.demo %}<div class="demo">Demo store: the business contact details on this invoice are placeholders.</div>{% endif %}

  <div class="parties">
    <div>
      <h3>Bill to</h3>
      <p><b>{{ d.shipping.name }}</b></p>
      {% if d.shipping.phone %}<p>{{ d.shipping.phone }}</p>{% endif %}
      {% if d.shipping.email %}<p>{{ d.shipping.email }}</p>{% endif %}
    </div>
    <div>
      <h3>{{ 'Deliver to' if d.order_type == 'delivery' else 'Fulfilment' }}</h3>
      {% if d.order_type == 'delivery' %}
        <p>{{ d.shipping.address or '' }}</p>
        <p>{{ [d.shipping.city, d.shipping.state, d.shipping.pincode] | select | join(', ') }}</p>
      {% else %}<p>Store pickup</p>{% endif %}
    </div>
  </div>

  <table class="items">
    <thead><tr><th>#</th><th>Product</th><th class="num">Qty</th><th class="num hide-sm">MRP</th>
      <th class="num">Unit price</th><th class="num hide-sm">Discount</th><th class="num">Amount</th></tr></thead>
    <tbody>
    {% for it in d['items'] %}
      <tr><td>{{ loop.index }}</td>
        <td>{{ it.product_name }}{% if it.sku %}<div class="sku">SKU: {{ it.sku }}</div>{% endif %}</td>
        <td class="num">{{ it.quantity }} {{ it.unit }}</td>
        <td class="num hide-sm">{{ cur }}{{ inr(it.mrp) }}</td>
        <td class="num">{{ cur }}{{ inr(it.price) }}</td>
        <td class="num hide-sm">{% if it.discount %}−{{ cur }}{{ inr(it.discount) }}{% else %}—{% endif %}</td>
        <td class="num">{{ cur }}{{ inr(it.subtotal) }}</td></tr>
    {% endfor %}
    </tbody>
  </table>

  <table class="totals">
    <tr><td>Subtotal (MRP)</td><td class="num">{{ cur }}{{ inr(d.subtotal) }}</td></tr>
    {% if d.discount %}<tr><td>Discount</td><td class="num">−{{ cur }}{{ inr(d.discount) }}</td></tr>{% endif %}
    {% if d.tax %}<tr><td>Tax{% if tax_inclusive %} (included){% endif %}</td><td class="num">{{ cur }}{{ inr(d.tax) }}</td></tr>{% endif %}
    <tr><td>Delivery</td><td class="num">{% if d.delivery_fee %}{{ cur }}{{ inr(d.delivery_fee) }}{% else %}Free{% endif %}</td></tr>
    <tr class="grand"><td>Grand Total</td><td class="num">{{ cur }}{{ inr(d.grand_total) }}</td></tr>
  </table>

  <div class="meta">
    <span class="pill">Payment: {{ payment_label }} — <b>{{ d.payment_status | capitalize }}</b></span>
    <span class="pill {{ 'cancelled' if d.status == 'cancelled' else '' }}">Order status: <b>{{ d.status_label }}</b></span>
  </div>
  {% if d.note %}<p style="margin-top:16px;color:var(--muted)">Customer note: {{ d.note }}</p>{% endif %}

  <div class="foot">
    <strong>{{ biz.footer or ('Thank you for shopping with ' ~ biz.name ~ '.') }}</strong>
    {% if biz.terms %}<span>{{ biz.terms }}</span>{% endif %}
    <div style="margin-top:6px;font-size:12px">This is a computer-generated invoice.</div>
  </div>
</div>
{% if autoprint %}<script>window.addEventListener('load',()=>window.print())</script>{% endif %}
</body></html>"""


def render_html(invoice, pdf_url, autoprint=False):
    ctx = _context(invoice)
    tax_inclusive = (invoice.order.tax or 0) and abs(
        (invoice.order.subtotal or 0) - (invoice.order.discount or 0) + (invoice.order.delivery_fee or 0)
        - (invoice.order.grand_total or 0)) < 0.01
    return render_template_string(INVOICE_HTML, pdf_url=pdf_url, autoprint=autoprint,
                                  tax_inclusive=tax_inclusive, **ctx)


def render_pdf(invoice):
    """A4 PDF via reportlab. Uses 'Rs.' because the built-in PDF fonts have no ₹ glyph."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape

    ctx = _context(invoice)
    d, biz = ctx["d"], ctx["biz"]
    rs = lambda v: "Rs. " + inr(v)          # noqa: E731
    e = lambda v: escape(str(v or ""))      # noqa: E731

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"Invoice {invoice.invoice_number}", author=biz.get("name", ""))
    ss = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=9, leading=12)
    muted = ParagraphStyle("muted", parent=small, textColor=colors.HexColor("#64748b"))
    brand = ParagraphStyle("brand", parent=ss["Title"], fontSize=17, alignment=0,
                           textColor=colors.HexColor("#0f4c81"), spaceAfter=2)
    right = ParagraphStyle("right", parent=small, alignment=2)
    blue = colors.HexColor("#0f4c81")
    line = colors.HexColor("#e2e8f0")

    biz_lines = [e(biz.get("address"))]
    contact = " · ".join(x for x in (biz.get("phone"), biz.get("email")) if x)
    if contact:
        biz_lines.append(e(contact))
    if biz.get("gstin"):
        biz_lines.append("GSTIN: " + e(biz["gstin"]))
    head = Table([[
        [Paragraph(e((biz.get("name") or "").upper()), brand),
         Paragraph("<br/>".join(x for x in biz_lines if x), muted)],
        [Paragraph("<b>INVOICE</b>", ParagraphStyle("t", parent=right, fontSize=16, leading=20)),
         Paragraph(f"Invoice No. <b>{e(invoice.invoice_number)}</b><br/>Order No. {e(d['order_number'])}"
                   f"<br/>Date {e(ctx['date'])}", right)],
    ]], colWidths=["60%", "40%"])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("LINEBELOW", (0, 0), (-1, 0), 2, blue),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story = [head, Spacer(1, 8)]
    if biz.get("demo"):
        story.append(Paragraph("Demo store: the business contact details on this invoice are placeholders.", muted))
        story.append(Spacer(1, 6))

    s = d["shipping"]
    bill = f"<b>Bill to</b><br/>{e(s['name'])}<br/>{e(s['phone'])}" + (f"<br/>{e(s['email'])}" if s.get("email") else "")
    if d["order_type"] == "delivery":
        place = ", ".join(x for x in (s.get("city"), s.get("state"), s.get("pincode")) if x)
        ship = f"<b>Deliver to</b><br/>{e(s.get('address'))}<br/>{e(place)}"
    else:
        ship = "<b>Fulfilment</b><br/>Store pickup"
    parties = Table([[Paragraph(bill, small), Paragraph(ship, small)]], colWidths=["50%", "50%"])
    parties.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [parties, Spacer(1, 10)]

    rows = [["#", "Product", "Qty", "MRP", "Unit price", "Discount", "Amount"]]
    for i, it in enumerate(d["items"], 1):
        name = e(it["product_name"]) + (f"<br/><font color='#64748b' size='8'>SKU: {e(it['sku'])}</font>" if it.get("sku") else "")
        rows.append([str(i), Paragraph(name, small), f"{it['quantity']} {it['unit']}", rs(it["mrp"]),
                     rs(it["price"]), ("-" + rs(it["discount"])) if it["discount"] else "-", rs(it["subtotal"])])
    items = Table(rows, colWidths=[8 * mm, None, 20 * mm, 24 * mm, 24 * mm, 22 * mm, 26 * mm], repeatRows=1)
    items.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, line),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story += [items, Spacer(1, 8)]

    tot = [["Subtotal (MRP)", rs(d["subtotal"])]]
    if d["discount"]:
        tot.append(["Discount", "-" + rs(d["discount"])])
    if d["tax"]:
        tot.append(["Tax", rs(d["tax"])])
    tot.append(["Delivery", rs(d["delivery_fee"]) if d["delivery_fee"] else "Free"])
    tot.append(["Grand Total", rs(d["grand_total"])])
    totals = Table(tot, colWidths=[40 * mm, 34 * mm], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, -1), (-1, -1), 11.5),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, colors.black),
    ]))
    story += [totals, Spacer(1, 10)]
    story.append(Paragraph(f"Payment: {e(ctx['payment_label'])} — <b>{e(d['payment_status'].capitalize())}</b>"
                           f" &nbsp;&nbsp; Order status: <b>{e(d['status_label'])}</b>", small))
    story.append(Spacer(1, 18))
    footer = biz.get("footer") or f"Thank you for shopping with {biz.get('name', '')}."
    story.append(Paragraph(f"<b>{e(footer)}</b>", ParagraphStyle("f", parent=small, alignment=1)))
    if biz.get("terms"):
        story.append(Paragraph(e(biz["terms"]), ParagraphStyle("f2", parent=muted, alignment=1)))
    story.append(Paragraph("This is a computer-generated invoice.", ParagraphStyle("f3", parent=muted, alignment=1)))

    doc.build(story)
    return buf.getvalue()
