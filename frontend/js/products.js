/* ============================================================
   products.js — product cards, catalog page, product details,
   wishlist and compare. All data comes from the API.
   ============================================================ */

/* ---------- small pieces ---------- */
function priceHTML(p, big = false) {
  const off = p.discount_percent || 0;
  return `<div class="price-row">
      <span class="price">${priceText(p)}</span>
      ${off ? `<span class="price-old">${money(p.price)}</span><span class="price-off">${off}% off</span>` : ""}
      <span class="price-unit">/ ${esc(p.unit || "piece")}</span>
    </div>`;
}

function stockHTML(p) {
  if (!p.in_stock) return `<span class="stock-line ${stockText(p) === "Out of stock" ? "stock-out" : "stock-low"}"><span class="dot"></span>${stockText(p)}</span>`;
  if (p.stock_status === "low") return `<span class="stock-line stock-low"><span class="dot"></span>Only ${p.stock} left</span>`;
  return `<span class="stock-line stock-in"><span class="dot"></span>In stock</span>`;
}

function productCardHTML(p) {
  window.__productCache[p.id] = p;
  const url = productUrl(p);
  const wished = window.__wishlist.has(p.id);
  const compared = getCompare().includes(p.id);
  return `
    <article class="product-card">
      <a class="product-thumb" href="${url}" aria-label="${esc(p.name)}">
        <img src="${imgSrc(p.image)}" alt="${esc(p.name)}" loading="lazy" decoding="async" onerror="this.src=PLACEHOLDER">
        <span class="badges">
          ${p.discount_percent ? `<span class="badge badge-sale">${p.discount_percent}% OFF</span>` : ""}
          ${p.featured ? `<span class="badge badge-brand">Featured</span>` : ""}
          ${!p.in_stock && stockText(p) === "Out of stock" ? `<span class="badge badge-out">Out of stock</span>` : ""}
        </span>
      </a>
      <div class="card-tools">
        <button class="tool-btn ${wished ? "on" : ""}" data-wish="${p.id}" onclick="toggleWishlist(${p.id})"
                aria-pressed="${wished}" aria-label="${wished ? "Remove from" : "Save to"} wishlist">${icon("heart")}</button>
        <button class="tool-btn ${compared ? "compare-on" : ""}" data-compare="${p.id}" onclick="toggleCompare(${p.id})"
                aria-pressed="${compared}" aria-label="Compare ${esc(p.name)}">${icon("compare")}</button>
      </div>
      <div class="product-body">
        <div class="product-meta"><span>${esc(p.brand || p.category_name || "")}</span>${p.sku ? `<span class="sku">${esc(p.sku)}</span>` : ""}</div>
        <h3 class="product-name"><a href="${url}">${esc(p.name)}</a></h3>
        <p class="product-desc">${esc(p.short_description || "")}</p>
        ${priceHTML(p)}
        ${stockHTML(p)}
        <div class="product-actions">
          <button class="btn btn-outline" onclick="addToCartById(${p.id})" ${p.in_stock ? "" : "disabled"}>${icon("cart")} Add</button>
          <button class="btn btn-primary" onclick="buyNow(${p.id})" ${p.in_stock ? "" : "disabled"}>Buy now</button>
        </div>
      </div>
    </article>`;
}

/* ============================================================
   WISHLIST
   ============================================================ */
async function toggleWishlist(id) {
  if (!window.__me) {
    toast("Log in to save products to your wishlist.", "error", { href: "/account.html", label: "Log in" });
    return;
  }
  const on = window.__wishlist.has(id);
  try {
    if (on) {
      await api("/account/wishlist/" + id, { method: "DELETE" });
      window.__wishlist.delete(id);
      toast("Removed from wishlist");
    } else {
      await api("/account/wishlist", { method: "POST", body: JSON.stringify({ product_id: id }) });
      window.__wishlist.add(id);
      toast("Saved to wishlist", "success", { href: "/account.html#wishlist", label: "View" });
    }
    document.querySelectorAll(`[data-wish="${id}"]`).forEach((b) => {
      b.classList.toggle("on", !on);
      b.setAttribute("aria-pressed", String(!on));
    });
    if (typeof onWishlistChanged === "function") onWishlistChanged();
  } catch (err) {
    toast(err.message, "error");
  }
}

/* ============================================================
   COMPARE (up to 4 products, kept in localStorage)
   ============================================================ */
const COMPARE_KEY = "mh_compare_v1";

function getCompare() {
  try {
    return (JSON.parse(localStorage.getItem(COMPARE_KEY)) || []).filter(Number.isInteger).slice(0, 4);
  } catch {
    return [];
  }
}

function setCompare(ids) {
  try {
    localStorage.setItem(COMPARE_KEY, JSON.stringify(ids.slice(0, 4)));
  } catch {}
  renderCompareBar();
}

function toggleCompare(id) {
  let ids = getCompare();
  if (ids.includes(id)) {
    ids = ids.filter((x) => x !== id);
  } else {
    if (ids.length >= 4) {
      toast("You can compare up to 4 products.", "error");
      return;
    }
    ids.push(id);
  }
  setCompare(ids);
  document.querySelectorAll(`[data-compare="${id}"]`).forEach((b) => {
    b.classList.toggle("compare-on", ids.includes(id));
    b.classList.toggle("on", ids.includes(id));
    b.setAttribute("aria-pressed", String(ids.includes(id)));
  });
}

function renderCompareBar() {
  document.getElementById("compareBar")?.remove();
  const ids = getCompare();
  if (!ids.length || document.body.dataset.page === "compare") return;
  const bar = document.createElement("div");
  bar.id = "compareBar";
  bar.className = "compare-bar";
  bar.innerHTML = `<span>${icon("compare")} ${ids.length} product${ids.length === 1 ? "" : "s"} to compare</span>
    <a class="btn btn-accent btn-sm" href="/compare.html?ids=${ids.join(",")}" ${ids.length < 2 ? 'aria-disabled="true" onclick="toast(\'Add one more product to compare.\',\'error\');return false"' : ""}>Compare</a>
    <button class="x" aria-label="Clear compare list" onclick="setCompare([]);document.querySelectorAll('[data-compare]').forEach(b=>b.classList.remove('compare-on','on'))">${icon("x")}</button>`;
  document.body.appendChild(bar);
}

async function initComparePage() {
  setMeta("Compare products");
  const host = document.getElementById("compareContent");
  if (!host) return;
  const fromUrl = (new URLSearchParams(location.search).get("ids") || "").split(",").map(Number).filter(Number.isInteger).filter(Boolean);
  const ids = fromUrl.length ? fromUrl : getCompare();
  if (ids.length < 2) {
    host.innerHTML = emptyState("compare", "Pick at least two products", "Use the compare button on any product card.",
      `<a class="btn btn-primary" href="/products.html">Browse products</a>`);
    return;
  }
  host.innerHTML = `<p class="loading"><span class="spinner"></span>Loading comparison…</p>`;
  try {
    const items = (await api("/products/compare?ids=" + ids.join(","))).data;
    items.forEach((p) => (window.__productCache[p.id] = p));
    const rows = [
      ["Price", (p) => priceText(p) + (p.discount_percent ? ` <s class="muted">${money(p.price)}</s>` : "")],
      ["Discount", (p) => (p.discount_percent ? p.discount_percent + "% off" : "")],
      ["Availability", (p) => (p.in_stock ? `In stock (${p.stock})` : stockText(p))],
      ["Brand", (p) => esc(p.brand)], ["Category", (p) => esc(p.category_name)], ["SKU", (p) => esc(p.sku)],
      ["Material", (p) => esc(p.material)], ["Size", (p) => esc(p.size)], ["Colour", (p) => esc(p.color)],
      ["Weight", (p) => esc(p.weight)], ["Finish", (p) => esc(p.finish)], ["Thickness", (p) => esc(p.thickness)],
      ["Pieces per box", (p) => esc(p.pieces_per_box)], ["Coverage", (p) => esc(p.coverage)], ["Unit", (p) => esc(p.unit)],
    ].filter(([, f]) => items.some((p) => f(p)));
    host.innerHTML = `<div class="table-scroll"><table class="compare-table">
      <tr><th></th>${items.map((p) => `<td class="c-head">
        <a href="${productUrl(p)}"><img src="${imgSrc(p.image)}" alt="${esc(p.name)}" onerror="this.src=PLACEHOLDER"></a>
        <a href="${productUrl(p)}"><b>${esc(p.name)}</b></a>
        <div class="mt-1" style="display:flex;gap:6px;flex-wrap:wrap">
          <button class="btn btn-primary btn-sm" onclick="addToCartById(${p.id})" ${p.in_stock ? "" : "disabled"}>Add to cart</button>
          <button class="btn btn-ghost btn-sm" onclick="setCompare(getCompare().filter(x=>x!==${p.id}));initComparePage()">Remove</button>
        </div></td>`).join("")}</tr>
      ${rows.map(([label, f]) => {
        const vals = items.map((p) => f(p) || "—");
        const diff = new Set(vals).size > 1;
        return `<tr class="${diff ? "diff" : ""}"><th>${label}</th>${vals.map((v) => `<td>${v}</td>`).join("")}</tr>`;
      }).join("")}
    </table></div>
    <p class="muted mt-1">Highlighted rows show where the products differ.</p>`;
  } catch (err) {
    host.innerHTML = emptyState("info", "Unable to load comparison", err.message);
  }
}

/* ============================================================
   CATALOG PAGE
   ============================================================ */
const productsState = { page: 1, limit: 12, filters: {}, view: "grid", options: null };

const SORTS = [
  ["featured", "Featured"], ["newest", "Newest"], ["price_asc", "Price: Low → High"],
  ["price_desc", "Price: High → Low"], ["name_asc", "Name: A → Z"], ["discount", "Biggest discount"],
];

async function initProductsPage() {
  const grid = document.getElementById("productsGrid");
  if (!grid) return;
  const params = new URLSearchParams(location.search);
  productsState.filters = Object.fromEntries([...params.entries()].filter(([k]) => k !== "page"));
  productsState.page = Math.max(1, parseInt(params.get("page"), 10) || 1);
  try {
    productsState.view = localStorage.getItem("mh_view") === "list" ? "list" : "grid";
  } catch {}

  const sortEl = document.getElementById("sortSelect");
  sortEl.innerHTML = SORTS.map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
  sortEl.value = productsState.filters.sort || "featured";
  sortEl.onchange = () => {
    productsState.filters.sort = sortEl.value;
    productsState.page = 1;
    loadProducts();
  };
  document.querySelectorAll(".view-toggle button").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === productsState.view);
    b.onclick = () => {
      productsState.view = b.dataset.view;
      try { localStorage.setItem("mh_view", b.dataset.view); } catch {}
      document.querySelectorAll(".view-toggle button").forEach((x) => x.classList.toggle("active", x === b));
      grid.classList.toggle("list", productsState.view === "list");
    };
  });
  grid.classList.toggle("list", productsState.view === "list");
  document.getElementById("filterOpen").onclick = () => toggleFilters(true);

  await buildFilterSidebar();
  loadProducts(false);
}

function toggleFilters(open) {
  document.getElementById("filters")?.classList.toggle("open", open);
  document.getElementById("filterBackdrop")?.classList.toggle("open", open);
}

function updateURL() {
  const params = new URLSearchParams();
  Object.entries(productsState.filters).forEach(([k, v]) => {
    if (v !== "" && v !== null && v !== undefined) params.set(k, v);
  });
  if (productsState.page > 1) params.set("page", productsState.page);
  const qs = params.toString();
  history.replaceState(history.state, "", location.pathname + (qs ? `?${qs}` : ""));
}

async function loadProducts(syncUrl = true) {
  const grid = document.getElementById("productsGrid");
  if (!grid) return;
  if (syncUrl) updateURL();
  syncFilterInputs();
  renderActiveFilters();
  updateCatalogHeading();
  const countEl = document.getElementById("resultCount");
  grid.innerHTML = skeletonCards(productsState.limit > 8 ? 8 : 4);
  grid.setAttribute("aria-busy", "true");

  const params = new URLSearchParams();
  Object.entries(productsState.filters).forEach(([k, v]) => {
    if (v !== "" && v !== null && v !== undefined && k !== "view") params.set(k, v);
  });
  if (!params.get("sort")) params.set("sort", "featured");
  params.set("page", productsState.page);
  params.set("limit", productsState.limit);

  try {
    const res = await api("/products?" + params.toString());
    const items = res.data || [];
    const meta = res.meta || {};
    if (countEl) countEl.textContent = meta.total ? `${meta.total} product${meta.total === 1 ? "" : "s"}` : "";
    if (!items.length) {
      const q = productsState.filters.q;
      grid.innerHTML = emptyState("search", q ? `No results for “${q}”` : "No products match these filters",
        q ? "Check the spelling, try a more general word (e.g. “tap”, “pipe”), or ask our AI assistant." : "Try removing a filter.",
        `<button class="btn btn-primary" onclick="clearAllFilters()">Clear filters</button>
         <button class="btn btn-outline" onclick="openAI(${esc(JSON.stringify(q || ""))})">${icon("sparkle")} Ask AI</button>`);
      document.getElementById("pagination").innerHTML = "";
      return;
    }
    grid.innerHTML = items.map(productCardHTML).join("");
    renderPagination(meta);
  } catch (err) {
    grid.innerHTML = emptyState("info", "Unable to load products", "Please try again.",
      `<button class="btn btn-primary" onclick="loadProducts()">Retry</button>`);
  } finally {
    grid.removeAttribute("aria-busy");
  }
}

function updateCatalogHeading() {
  const f = productsState.filters;
  const title = document.getElementById("catalogTitle");
  const sub = document.getElementById("catalogSub");
  if (!title) return;
  const cat = productsState.options?.categories.find((c) => c.slug === f.category);
  let t = "All products";
  if (f.q) t = `Search: “${f.q}”`;
  else if (cat) t = cat.name;
  else if (f.featured) t = "Featured products";
  else if (f.discount) t = "Best deals";
  title.textContent = t;
  if (sub) sub.textContent = cat?.description || "Genuine hardware, sanitary, plumbing and tiles — prices updated from our store.";
  setMeta(t);
}

function renderPagination(meta) {
  const host = document.getElementById("pagination");
  if (!host) return;
  if (!meta.pages || meta.pages <= 1) {
    host.innerHTML = "";
    return;
  }
  let html = `<button ${meta.page === 1 ? "disabled" : ""} onclick="gotoPage(${meta.page - 1})" aria-label="Previous page">${icon("chevronLeft")}</button>`;
  for (let i = 1; i <= meta.pages; i++) {
    if (i === 1 || i === meta.pages || Math.abs(i - meta.page) <= 1) {
      html += `<button class="${i === meta.page ? "active" : ""}" ${i === meta.page ? 'aria-current="page"' : ""} onclick="gotoPage(${i})">${i}</button>`;
    } else if (Math.abs(i - meta.page) === 2) {
      html += `<button disabled>…</button>`;
    }
  }
  html += `<button ${meta.page === meta.pages ? "disabled" : ""} onclick="gotoPage(${meta.page + 1})" aria-label="Next page">${icon("chevronRight")}</button>`;
  host.innerHTML = html;
}

function gotoPage(p) {
  productsState.page = p;
  loadProducts();
  document.getElementById("catalogTop")?.scrollIntoView({ behavior: "smooth" });
}

async function buildFilterSidebar() {
  const host = document.getElementById("filterBody");
  if (!host) return;
  let opts = productsState.options;
  if (!opts) {
    try {
      opts = productsState.options = (await api("/products/filters")).data;
    } catch {
      opts = { brands: [], categories: [] };
    }
  }
  const topCats = opts.categories.filter((c) => !c.parent_id);
  host.innerHTML = `
    <div class="filter-group">
      <span class="label">Category</span>
      <div class="filter-list" role="radiogroup" aria-label="Category">
        <label class="check"><input type="radio" name="fCat" value=""> All categories</label>
        ${topCats.map((c) => `<label class="check"><input type="radio" name="fCat" value="${esc(c.slug)}"> ${esc(c.name)}</label>`).join("")}
      </div>
    </div>
    ${opts.brands.length ? `
    <div class="filter-group">
      <span class="label">Brand</span>
      <div class="filter-list">
        ${opts.brands.map((b) => `<label class="check"><input type="checkbox" name="fBrand" value="${esc(b)}"> ${esc(b)}</label>`).join("")}
      </div>
    </div>` : ""}
    <div class="filter-group">
      <span class="label">Price (${esc(window.__settings.currency_symbol || "₹")})</span>
      <div class="price-row-inputs">
        <input type="number" id="fMin" placeholder="Min" min="0" inputmode="numeric" aria-label="Minimum price">
        <input type="number" id="fMax" placeholder="Max" min="0" inputmode="numeric" aria-label="Maximum price">
      </div>
    </div>
    <div class="filter-group">
      <span class="label">Availability & offers</span>
      <div class="filter-list">
        <label class="check"><input type="checkbox" id="fAvail"> In stock only</label>
        <label class="check"><input type="checkbox" id="fDiscount"> On discount</label>
        <label class="check"><input type="checkbox" id="fFeatured"> Featured</label>
      </div>
    </div>`;

  const f = productsState.filters;
  host.querySelectorAll('input[name="fCat"]').forEach((r) => (r.onchange = () => {
    f.category = r.value;
    delete f.subcategory;
    applyFilters();
  }));
  host.querySelectorAll('input[name="fBrand"]').forEach((c) => (c.onchange = () => {
    f.brand = [...host.querySelectorAll('input[name="fBrand"]:checked')].map((x) => x.value).join(",");
    applyFilters();
  }));
  const priceChanged = debounce(() => {
    f.min_price = document.getElementById("fMin").value.trim();
    f.max_price = document.getElementById("fMax").value.trim();
    applyFilters();
  }, 500);
  ["fMin", "fMax"].forEach((id) => document.getElementById(id).addEventListener("input", priceChanged));
  [["fAvail", "availability"], ["fDiscount", "discount"], ["fFeatured", "featured"]].forEach(([id, key]) => {
    document.getElementById(id).onchange = (e) => {
      f[key] = e.target.checked ? "1" : "";
      applyFilters();
    };
  });
  document.getElementById("clearFilters").onclick = clearAllFilters;
}

function applyFilters() {
  productsState.page = 1;
  loadProducts();
}

function clearAllFilters() {
  const sort = productsState.filters.sort;
  productsState.filters = sort ? { sort } : {};
  productsState.page = 1;
  const gs = document.getElementById("globalSearch");
  if (gs) gs.value = "";
  loadProducts();
}

function syncFilterInputs() {
  const f = productsState.filters;
  const host = document.getElementById("filterBody");
  if (!host) return;
  host.querySelectorAll('input[name="fCat"]').forEach((r) => (r.checked = r.value === (f.category || "")));
  const brands = (f.brand || "").split(",");
  host.querySelectorAll('input[name="fBrand"]').forEach((c) => (c.checked = brands.includes(c.value)));
  const set = (id, v) => {
    const el = document.getElementById(id);
    if (el && document.activeElement !== el) el.value = v || "";
  };
  set("fMin", f.min_price);
  set("fMax", f.max_price);
  document.getElementById("fAvail").checked = !!f.availability;
  document.getElementById("fDiscount").checked = !!f.discount;
  document.getElementById("fFeatured").checked = !!f.featured;
  const sortEl = document.getElementById("sortSelect");
  if (sortEl) sortEl.value = f.sort || "featured";
  const gs = document.getElementById("globalSearch");
  if (gs && f.q && document.activeElement !== gs) gs.value = f.q;
}

function renderActiveFilters() {
  const host = document.getElementById("activeFilters");
  if (!host) return;
  const f = productsState.filters;
  const cats = productsState.options?.categories || [];
  const chips = [];
  if (f.q) chips.push(["q", `“${f.q}”`]);
  if (f.category) chips.push(["category", cats.find((c) => c.slug === f.category)?.name || f.category]);
  (f.brand || "").split(",").filter(Boolean).forEach((b) => chips.push(["brand:" + b, b]));
  if (f.min_price) chips.push(["min_price", `Min ${money(f.min_price)}`]);
  if (f.max_price) chips.push(["max_price", `Max ${money(f.max_price)}`]);
  if (f.availability) chips.push(["availability", "In stock"]);
  if (f.discount) chips.push(["discount", "On discount"]);
  if (f.featured) chips.push(["featured", "Featured"]);
  host.innerHTML = chips.map(([k, label]) =>
    `<button onclick="removeFilter(${esc(JSON.stringify(k))})" aria-label="Remove filter ${esc(label)}">${esc(label)} ${icon("x")}</button>`).join("");
}

function removeFilter(key) {
  const f = productsState.filters;
  if (key.startsWith("brand:")) {
    const b = key.slice(6);
    f.brand = (f.brand || "").split(",").filter((x) => x && x !== b).join(",");
  } else {
    delete f[key];
    if (key === "q") {
      const gs = document.getElementById("globalSearch");
      if (gs) gs.value = "";
    }
  }
  applyFilters();
}

/* ============================================================
   PRODUCT DETAILS PAGE
   ============================================================ */
let pdState = { product: null, images: [], index: 0, qty: 1 };

async function initProductDetails() {
  const host = document.getElementById("productDetails");
  if (!host) return;
  const m = location.pathname.match(/^\/products\/([^/]+)/);
  const id = new URLSearchParams(location.search).get("id");
  if (!m && !id) {
    host.innerHTML = emptyState("box", "Product not specified", "", `<a class="btn btn-primary" href="/products.html">Browse products</a>`);
    return;
  }
  host.innerHTML = `<div class="pd"><div class="skeleton" style="aspect-ratio:1;border-radius:18px"></div>
    <div><div class="skeleton sk-line w40"></div><div class="skeleton sk-line w80 mt-2" style="height:28px"></div>
    <div class="skeleton sk-line w60 mt-2"></div><div class="skeleton mt-3" style="height:110px"></div></div></div>`;

  let p;
  try {
    p = (await api(m ? "/products/slug/" + encodeURIComponent(decodeURIComponent(m[1])) : "/products/" + encodeURIComponent(id))).data;
  } catch {
    host.innerHTML = emptyState("search", "Product not found", "It may have been removed or renamed.",
      `<a class="btn btn-primary" href="/products.html">Browse products</a>`);
    return;
  }
  window.__productCache[p.id] = p;
  pdState = { product: p, images: [p.image, ...(p.additional_images || [])].filter(Boolean), index: 0, qty: 1 };
  if (!pdState.images.length) pdState.images = [""];
  setMeta(p.name, p.short_description || p.description || `${p.name} — ${p.category_name || "product"}`);
  injectProductJsonLd(p);

  const s = window.__settings;
  const specs = [
    ["Brand", p.brand], ["SKU", p.sku], ["Category", p.category_name], ["Material", p.material],
    ["Size", p.size], ["Colour", p.color], ["Weight", p.weight], ["Finish", p.finish],
    ["Thickness", p.thickness], ["Pieces per box", p.pieces_per_box], ["Coverage", p.coverage],
    ["Unit", p.unit],
  ].filter(([, v]) => v !== null && v !== undefined && String(v).trim() !== "");
  const wished = window.__wishlist.has(p.id);
  const compared = getCompare().includes(p.id);
  const save = p.discount_percent ? p.price - p.final_price : 0;

  host.innerHTML = `
    <nav class="crumbs" aria-label="Breadcrumb">
      <a href="/index.html">Home</a><span>/</span><a href="/products.html">Products</a><span>/</span>
      ${p.category_slug ? `<a href="/products.html?category=${encodeURIComponent(p.category_slug)}">${esc(p.category_name)}</a><span>/</span>` : ""}
      <span aria-current="page">${esc(p.name)}</span>
    </nav>
    <div class="pd">
      <div class="pd-gallery">
        <div class="pd-main" id="pdMain" tabindex="0" role="button" aria-label="Open image viewer">
          <img id="pdMainImg" src="${imgSrc(pdState.images[0])}" alt="${esc(p.name)}" onerror="this.src=PLACEHOLDER">
          <button class="btn btn-light btn-icon expand" aria-label="View full screen" onclick="event.stopPropagation();openLightbox(pdState.index)">${icon("expand")}</button>
        </div>
        ${pdState.images.length > 1 ? `<div class="pd-thumbs" role="list">
          ${pdState.images.map((src, i) => `<button role="listitem" class="${i === 0 ? "active" : ""}" onclick="pdShow(${i})" aria-label="Image ${i + 1}">
            <img src="${imgSrc(src)}" alt="" loading="lazy" onerror="this.src=PLACEHOLDER"></button>`).join("")}
        </div>` : ""}
      </div>

      <div class="pd-info">
        ${p.category_name ? `<span class="pill pill-blue">${esc(p.category_name)}</span>` : ""}
        <h1 class="mt-1">${esc(p.name)}</h1>
        <div class="pd-sub">
          ${p.brand ? `<span>Brand: <b>${esc(p.brand)}</b></span>` : ""}
          ${p.sku ? `<span>SKU: <b>${esc(p.sku)}</b></span>` : ""}
          <span>${stockHTML(p)}</span>
        </div>

        <div class="pd-price">
          <div class="price-row">
            <span class="price">${priceText(p)}</span>
            ${p.discount_percent ? `<span class="badge badge-sale">${p.discount_percent}% OFF</span>` : ""}
            <span class="price-unit">per ${esc(p.unit || "piece")}</span>
          </div>
          ${p.discount_percent ? `<div class="mrp">MRP <s>${money(p.price)}</s> · <span class="save">You save ${money(save)}</span></div>` : ""}
          ${s.tax_enabled === "1" ? `<div class="mrp">${s.tax_inclusive === "1" ? "Inclusive of" : "Plus"} ${esc(s.tax_label || "tax")}</div>` : ""}
        </div>

        ${p.short_description ? `<p class="pd-short">${esc(p.short_description)}</p>` : ""}

        <div class="pd-buy">
          <div class="qty" role="group" aria-label="Quantity">
            <button id="qtyMinus" aria-label="Decrease quantity" disabled>${icon("minus")}</button>
            <input id="qtyInput" type="number" min="1" max="${p.stock || 1}" value="1" aria-label="Quantity" ${p.in_stock ? "" : "disabled"}>
            <button id="qtyPlus" aria-label="Increase quantity" ${p.in_stock && p.stock > 1 ? "" : "disabled"}>${icon("plus")}</button>
          </div>
          <button class="btn btn-outline btn-lg" onclick="addToCart(pdState.product, pdState.qty)" ${p.in_stock ? "" : "disabled"}>${icon("cart")} Add to cart</button>
          <button class="btn btn-primary btn-lg" onclick="pdBuyNow()" ${p.in_stock ? "" : "disabled"}>Buy now</button>
        </div>
        ${!p.in_stock ? `<div class="alert alert-warn">This product is currently unavailable. Ask us on WhatsApp — we can tell you when it's back or suggest an alternative.</div>` : ""}

        <div class="pd-help">
          ${waNumber() ? `<button class="btn btn-whatsapp" onclick="whatsappProduct(${p.id})">${icon("whatsapp")} WhatsApp inquiry</button>` : ""}
          ${s.phone ? `<a class="btn btn-outline" href="${telLink()}">${icon("phone")} Call for assistance</a>` : ""}
        </div>

        <div class="pd-links">
          <button class="wish ${wished ? "on" : ""}" data-wish="${p.id}" aria-pressed="${wished}" onclick="toggleWishlist(${p.id})">${icon("heart")} Wishlist</button>
          <button class="${compared ? "on" : ""}" data-compare="${p.id}" aria-pressed="${compared}" onclick="toggleCompare(${p.id})">${icon("compare")} Compare</button>
          <button onclick="document.getElementById('inquiryBox').classList.toggle('hidden')">${icon("receipt")} Bulk quote</button>
          <button onclick="openAI(${esc(JSON.stringify("What else do I need with " + p.name + "?"))})">${icon("sparkle")} Ask AI</button>
        </div>

        <div class="pd-perks">
          ${s.pickup_enabled !== "0" ? `<div>${icon("store")} Store pickup available in ${esc(s.city || "Bhopal")}</div>` : ""}
          ${s.delivery_enabled !== "0" ? `<div>${icon("truck")} ${esc(s.delivery_note || "Home delivery available")}</div>` : ""}
          ${s.payment_cod_enabled !== "0" ? `<div>${icon("shield")} Pay on delivery or at the store</div>` : ""}
        </div>
      </div>
    </div>

    <div id="inquiryBox" class="card mt-3 hidden">
      <h2>Request a bulk quote</h2>
      <p class="muted">For contractor or bulk quantities, send us your requirement and we'll get back to you.</p>
      <div id="inquiryAlert"></div>
      <form id="inquiryForm" class="form-grid">
        <input type="hidden" name="product_id" value="${p.id}">
        <input type="hidden" name="product_name" value="${esc(p.name)}">
        <div class="field"><label for="iqName">Name *</label><input id="iqName" name="name" required autocomplete="name"></div>
        <div class="field"><label for="iqPhone">Phone *</label><input id="iqPhone" name="phone" type="tel" required autocomplete="tel"></div>
        <div class="field"><label for="iqEmail">Email</label><input id="iqEmail" type="email" name="email" autocomplete="email"></div>
        <div class="field"><label for="iqQty">Quantity</label><input id="iqQty" name="quantity" placeholder="e.g. 50 boxes"></div>
        <div class="field span-2"><label for="iqMsg">Message</label><textarea id="iqMsg" name="message" placeholder="Any specific requirement?"></textarea></div>
        <div class="span-2"><button class="btn btn-primary" type="submit">Send enquiry</button></div>
      </form>
    </div>

    <div class="split mt-3" style="align-items:start">
      <section class="card">
        <h2>Description</h2>
        <div class="pd-desc">${esc(p.description || p.short_description || "Detailed description coming soon. Contact us for specifications.")}</div>
      </section>
      ${specs.length ? `<section class="card">
        <h2>Specifications</h2>
        <table class="spec-table">${specs.map(([k, v]) => `<tr><th scope="row">${esc(k)}</th><td>${esc(v)}</td></tr>`).join("")}</table>
      </section>` : ""}
    </div>

    <section class="mt-3">
      <div class="section-head"><div><h2>Related products</h2><p>From the same category and similar price range</p></div></div>
      <div id="relatedProducts" class="product-grid cols-4">${skeletonCards(4)}</div>
    </section>

    <div class="sticky-buy">
      <button class="btn btn-outline" onclick="addToCart(pdState.product, pdState.qty)" ${p.in_stock ? "" : "disabled"}>${icon("cart")} Add</button>
      <button class="btn btn-primary" onclick="pdBuyNow()" ${p.in_stock ? "" : "disabled"}>Buy now · ${priceText(p)}</button>
    </div>`;

  bindQty(p);
  bindZoom();
  bindInquiryForm();
  loadRelated(p.id);
}

function injectProductJsonLd(p) {
  document.getElementById("productLd")?.remove();
  const ld = {
    "@context": "https://schema.org", "@type": "Product", name: p.name, sku: p.sku || undefined,
    brand: p.brand ? { "@type": "Brand", name: p.brand } : undefined,
    category: p.category_name || undefined, description: p.short_description || p.description || undefined,
    image: p.image ? [location.origin + p.image] : undefined,
    offers: {
      "@type": "Offer", priceCurrency: window.__settings.currency || "INR", price: p.final_price,
      availability: p.in_stock ? "https://schema.org/InStock" : "https://schema.org/OutOfStock", url: location.href,
    },
  };
  const el = document.createElement("script");
  el.type = "application/ld+json";
  el.id = "productLd";
  el.textContent = JSON.stringify(ld);
  document.head.appendChild(el);
}

function bindQty(p) {
  const input = document.getElementById("qtyInput");
  const minus = document.getElementById("qtyMinus");
  const plus = document.getElementById("qtyPlus");
  const max = Math.max(1, p.stock || 1);
  const set = (v) => {
    v = Math.min(max, Math.max(1, parseInt(v, 10) || 1));
    if (parseInt(input.value, 10) > max) toast(`Only ${max} available.`, "error");
    pdState.qty = v;
    input.value = v;
    minus.disabled = v <= 1;
    plus.disabled = v >= max || !p.in_stock;
  };
  minus.onclick = () => set(pdState.qty - 1);
  plus.onclick = () => set(pdState.qty + 1);
  input.onchange = () => set(input.value);
}

function pdBuyNow() {
  const p = pdState.product;
  const inCart = getCart().find((i) => i.id === p.id);
  if (inCart || addToCart(p, pdState.qty, { silent: true })) navigateTo("/checkout.html");
}

function pdShow(i) {
  pdState.index = i;
  const img = document.getElementById("pdMainImg");
  if (img) img.src = imgSrc(pdState.images[i]);
  document.querySelectorAll(".pd-thumbs button").forEach((b, j) => b.classList.toggle("active", j === i));
}

function bindZoom() {
  const box = document.getElementById("pdMain");
  const img = document.getElementById("pdMainImg");
  if (!box || !img) return;
  const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  if (fine) {
    box.addEventListener("mousemove", (e) => {
      const r = box.getBoundingClientRect();
      img.style.transformOrigin = `${((e.clientX - r.left) / r.width) * 100}% ${((e.clientY - r.top) / r.height) * 100}%`;
      box.classList.add("zooming");
    });
    box.addEventListener("mouseleave", () => box.classList.remove("zooming"));
  }
  box.addEventListener("click", () => openLightbox(pdState.index));
  box.addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), openLightbox(pdState.index)));
}

/* ---------- shared lightbox (product images + gallery) ---------- */
function openLightbox(index, images = pdState.images, captions = []) {
  let i = index;
  const lb = document.createElement("div");
  lb.className = "lightbox";
  lb.setAttribute("role", "dialog");
  lb.setAttribute("aria-modal", "true");
  lb.setAttribute("aria-label", "Image viewer");
  const draw = () => {
    lb.innerHTML = `<img src="${imgSrc(images[i])}" alt="${esc(captions[i] || "")}" onerror="this.src=PLACEHOLDER">
      <button class="lb-close" aria-label="Close">${icon("x")}</button>
      ${images.length > 1 ? `<button class="lb-prev" aria-label="Previous image">${icon("chevronLeft")}</button>
      <button class="lb-next" aria-label="Next image">${icon("chevronRight")}</button>` : ""}
      <div class="lb-cap">${esc(captions[i] || "")}${images.length > 1 ? ` · ${i + 1} / ${images.length}` : ""}</div>`;
    lb.querySelector(".lb-close").focus();
  };
  const close = () => {
    lb.remove();
    document.removeEventListener("keydown", onKey);
  };
  const step = (d) => {
    i = (i + d + images.length) % images.length;
    draw();
  };
  const onKey = (e) => {
    if (e.key === "Escape") close();
    if (e.key === "ArrowLeft") step(-1);
    if (e.key === "ArrowRight") step(1);
  };
  lb.addEventListener("click", (e) => {
    if (e.target === lb || e.target.closest(".lb-close")) close();
    else if (e.target.closest(".lb-prev")) step(-1);
    else if (e.target.closest(".lb-next")) step(1);
  });
  document.addEventListener("keydown", onKey);
  document.body.appendChild(lb);
  draw();
}

async function loadRelated(id) {
  const host = document.getElementById("relatedProducts");
  if (!host) return;
  try {
    const items = (await api(`/products/${id}/related?limit=8`)).data || [];
    host.innerHTML = items.length ? items.map(productCardHTML).join("")
      : `<p class="muted">No related products yet.</p>`;
  } catch {
    host.innerHTML = `<p class="muted">Related products are unavailable right now.</p>`;
  }
}

function bindInquiryForm() {
  const form = document.getElementById("inquiryForm");
  if (!form || form._bound) return;
  form._bound = true;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const alertBox = document.getElementById("inquiryAlert");
    const btn = form.querySelector('button[type="submit"]');
    setButtonLoading(btn, true, "Sending…");
    try {
      const res = await api("/inquiries", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form).entries())) });
      alertBox.innerHTML = `<div class="alert alert-success">${esc(res.message || "Thank you! We will contact you shortly.")}</div>`;
      form.reset();
    } catch (err) {
      alertBox.innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
    } finally {
      setButtonLoading(btn, false);
    }
  });
}

function whatsappProduct(id) {
  const p = window.__productCache[id];
  if (!p) return;
  const text =
    `Hello, I am interested in this product:\n\n*${p.name}*\n` +
    (p.sku ? `SKU: ${p.sku}\n` : "") +
    `Price: ${priceText(p)} / ${p.unit || "piece"}\n` +
    `${location.origin}${productUrl(p)}\n\nPlease share availability and details.`;
  window.open(waLink(text), "_blank", "noopener");
}
