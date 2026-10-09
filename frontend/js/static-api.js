/* ============================================================
   static-api.js — read-only API fallback for static hosting
   ------------------------------------------------------------
   Loaded by api() in app.js only when the Flask backend is not
   reachable (e.g. the site is deployed on Netlify alone).
   Answers catalogue GET requests from /data/catalog.json, which
   backend/scripts/export_static.py generates from the database.
   ============================================================ */

let __catalogPromise = null;
function loadCatalog() {
  if (!__catalogPromise) {
    __catalogPromise = fetch("/data/catalog.json").then((r) => {
      if (!r.ok) throw new Error("Catalogue unavailable");
      return r.json();
    }).catch((e) => { __catalogPromise = null; throw e; });
  }
  return __catalogPromise;
}

const STATIC_OFFLINE_MSG = "Online ordering and accounts are unavailable right now. Please order on WhatsApp or call the store.";

function staticFail(message, status = 503) {
  const err = new Error(message);
  err.status = status;
  return err;
}

function staticNum(v) {
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : null;
}

function filterProducts(c, args) {
  let list = c.products.slice();
  const findCat = (v) => c.categories.find((x) => x.slug === v || String(x.id) === String(v));

  const q = (args.get("q") || "").trim().slice(0, 100).toLowerCase();
  if (q) {
    const words = q.split(/\s+/).slice(0, 6);
    list = list.filter((p) => {
      const hay = [p.name, p.brand, p.sku, p.description, p.short_description, p.material, p.category_name]
        .filter(Boolean).join(" ").toLowerCase();
      return words.every((w) => hay.includes(w));
    });
  }
  const category = args.get("category");
  if (category) {
    const cat = findCat(category);
    const ids = cat ? [cat.id, ...(cat.children || []).map((ch) => ch.id)] : [];
    list = list.filter((p) => ids.includes(p.category_id));
  }
  const sub = args.get("subcategory");
  if (sub) {
    const sc = findCat(sub);
    list = list.filter((p) => sc && p.category_id === sc.id);
  }
  if (args.get("brand")) {
    const brands = args.get("brand").split(",").filter(Boolean);
    list = list.filter((p) => brands.includes(p.brand));
  }
  for (const key of ["color", "material", "size"]) {
    if (args.get(key)) list = list.filter((p) => p[key] === args.get(key));
  }
  const min = staticNum(args.get("min_price")), max = staticNum(args.get("max_price"));
  if (min !== null) list = list.filter((p) => (p.final_price || 0) >= min);
  if (max !== null) list = list.filter((p) => (p.final_price || 0) <= max);
  if (["1", "true", "in"].includes(args.get("availability"))) list = list.filter((p) => p.availability && p.stock > 0);
  if (["1", "true"].includes(args.get("featured"))) list = list.filter((p) => p.featured);
  if (["1", "true"].includes(args.get("discount"))) list = list.filter((p) => p.discount_price != null && p.discount_price < p.price);

  const newest = (a, b) => String(b.created_at || "").localeCompare(String(a.created_at || ""));
  const sorters = {
    price_asc: (a, b) => (a.final_price || 0) - (b.final_price || 0),
    price_desc: (a, b) => (b.final_price || 0) - (a.final_price || 0),
    featured: (a, b) => (b.featured - a.featured) || newest(a, b),
    discount: (a, b) => (b.discount_percent || 0) - (a.discount_percent || 0),
    name_asc: (a, b) => String(a.name).localeCompare(String(b.name)),
  };
  return list.sort(sorters[args.get("sort")] || newest);
}

function paginateList(list, args) {
  const page = Math.max(1, parseInt(args.get("page"), 10) || 1);
  const limit = Math.min(100, Math.max(1, parseInt(args.get("limit"), 10) || 20));
  return {
    success: true,
    data: list.slice((page - 1) * limit, page * limit),
    meta: { page, limit, total: list.length, pages: Math.ceil(list.length / limit) },
  };
}

function relatedProducts(c, p, limit) {
  const price = p.final_price || 0;
  const nearest = (rows) => rows.filter((x) => x.id !== p.id)
    .sort((a, b) => (!a.in_stock - !b.in_stock) || Math.abs((a.final_price || 0) - price) - Math.abs((b.final_price || 0) - price))
    .slice(0, limit);
  const pools = [];
  const cat = c.categories.find((x) => x.id === p.category_id);
  if (cat) {
    pools.push(c.products.filter((x) => x.category_id === cat.id));
    const family = c.categories.find((x) => x.id === cat.parent_id) || cat;
    const ids = [family.id, ...(family.children || []).map((ch) => ch.id)];
    pools.push(c.products.filter((x) => ids.includes(x.category_id)));
  }
  if (p.brand) pools.push(c.products.filter((x) => x.brand === p.brand));
  const picked = [];
  for (const pool of pools) {
    for (const x of nearest(pool)) if (!picked.includes(x)) picked.push(x);
    if (picked.length >= limit) break;
  }
  return picked.slice(0, limit);
}

function staticQuote(c, body) {
  const s = c.settings || {};
  const flag = (k) => ["1", "true", "yes", "on"].includes(String(s[k] || "").trim().toLowerCase());
  const num = (k) => Math.max(0, parseFloat(s[k]) || 0);
  const r2 = (n) => Math.round(n * 100) / 100;
  const wanted = new Map();
  for (const i of body.items || []) {
    const id = parseInt(i.product_id, 10), qty = parseInt(i.quantity, 10);
    if (id > 0 && qty > 0) wanted.set(id, (wanted.get(id) || 0) + qty);
  }
  const lines = [], problems = [];
  let subtotal = 0, discount = 0, taxable = 0;
  for (const [id, qty] of wanted) {
    const p = c.products.find((x) => x.id === id);
    if (!p) { problems.push({ product_id: id, message: "This product is no longer available." }); continue; }
    const mrp = p.price || 0, price = p.final_price || 0;
    if (price <= 0) problems.push({ product_id: id, message: `${p.name} has no price yet. Please contact the store.` });
    if (!p.availability || (p.stock || 0) <= 0) problems.push({ product_id: id, message: `${p.name} is out of stock.` });
    else if (qty > p.stock) problems.push({ product_id: id, message: `Only ${p.stock} ${p.unit || "piece"}(s) of ${p.name} available.` });
    const lineMrp = mrp * qty, lineTotal = price * qty;
    subtotal += lineMrp; discount += Math.max(0, lineMrp - lineTotal); taxable += lineTotal;
    lines.push({ product_id: p.id, name: p.name, slug: p.slug, sku: p.sku, unit: p.unit || "piece", image: p.image,
      quantity: qty, stock: p.stock || 0, in_stock: p.in_stock, mrp: r2(mrp), price: r2(price),
      discount: r2(Math.max(0, lineMrp - lineTotal)), subtotal: r2(lineTotal) });
  }
  const orderType = ["delivery", "pickup"].includes(body.order_type) ? body.order_type : "delivery";
  let fee = 0;
  if (orderType === "delivery") {
    const freeAbove = num("free_delivery_above");
    fee = freeAbove > 0 && taxable >= freeAbove ? 0 : num("delivery_fee");
  }
  const inclusive = flag("tax_inclusive");
  let tax = 0;
  if (flag("tax_enabled")) {
    const rate = num("tax_rate");
    tax = inclusive ? taxable * rate / (100 + rate) : taxable * rate / 100;
  }
  return {
    lines, problems, ok: !problems.length && lines.length > 0, order_type: orderType,
    subtotal: r2(subtotal), discount: r2(discount), tax: r2(tax), tax_label: s.tax_label || "Tax",
    tax_enabled: flag("tax_enabled"), tax_inclusive: inclusive, delivery_fee: r2(fee),
    grand_total: r2(taxable + fee + (inclusive ? 0 : tax)),
    item_count: lines.reduce((n, l) => n + l.quantity, 0),
    delivery_options: [], payment_options: [],
  };
}

async function staticApi(path, options = {}) {
  const c = await loadCatalog();
  const method = (options.method || "GET").toUpperCase();
  const url = new URL(path, location.origin);
  const p = url.pathname.replace(/\/+$/, "");
  const args = url.searchParams;
  const ok = (data, extra = {}) => ({ success: true, data, ...extra });
  const byId = (id) => c.products.find((x) => String(x.id) === String(id));
  let m;

  if (method === "POST" && p === "/orders/quote") return ok(staticQuote(c, JSON.parse(options.body || "{}")));
  if (method === "POST" && p === "/ai/chat") {
    return ok({ reply: "Our assistant is offline right now. Browse the products page, or message us on WhatsApp for help.", products: [] });
  }
  if (method !== "GET") throw staticFail(STATIC_OFFLINE_MSG);

  if (p === "/settings") return ok(c.settings);
  if (p === "/categories") return ok(["1", "true"].includes(args.get("tree")) ? c.category_tree : c.categories);
  if (p === "/products/filters") return ok(c.filters);
  if (p === "/products" || p === "/products/search") return paginateList(filterProducts(c, args), args);
  if (p === "/products/compare") {
    const ids = (args.get("ids") || "").split(",").filter((x) => /^\d+$/.test(x.trim())).slice(0, 4);
    return ok(ids.map(byId).filter(Boolean));
  }
  if ((m = p.match(/^\/products\/slug\/(.+)$/))) {
    const prod = c.products.find((x) => x.slug === decodeURIComponent(m[1]));
    if (!prod) throw staticFail("Product not found", 404);
    return ok(prod);
  }
  if ((m = p.match(/^\/products\/(\d+)\/related$/))) {
    const prod = byId(m[1]);
    if (!prod) throw staticFail("Product not found", 404);
    return ok(relatedProducts(c, prod, Math.min(12, Math.max(1, parseInt(args.get("limit"), 10) || 8))));
  }
  if ((m = p.match(/^\/products\/(\d+)$/))) {
    const prod = byId(m[1]);
    if (!prod) throw staticFail("Product not found", 404);
    return ok(prod);
  }
  if (p === "/gallery/categories") return ok([...new Set(c.gallery.map((g) => g.category).filter(Boolean))].sort());
  if (p === "/gallery") {
    const cat = args.get("category");
    return ok(cat ? c.gallery.filter((g) => g.category === cat) : c.gallery);
  }
  if (p.startsWith("/account")) throw staticFail("Not signed in", 401);
  throw staticFail(STATIC_OFFLINE_MSG);
}
