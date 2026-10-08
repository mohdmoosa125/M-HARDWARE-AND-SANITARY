/* ============================================================
   products.js — product cards, listing page, filters, details
   ============================================================ */

function productCardHTML(p) {
  window.__productCache[p.id] = p;

  const hasDiscount = p.discount_price && p.discount_price < p.price;
  const priceHTML = hasDiscount
    ? `<span>${money(p.discount_price)}</span><span class="price-old">${money(p.price)}</span>`
    : `<span>${money(p.price)}</span>`;

  return `
    <div class="product-card">
      <a class="product-thumb" href="product-details.html?id=${p.id}">
        <img src="${imgSrc(p.image)}" alt="${esc(p.name)}" loading="lazy"
             onerror="this.src=PLACEHOLDER">
        ${hasDiscount ? '<span class="badge sale">Sale</span>' : ""}
        ${p.featured ? '<span class="badge featured">Featured</span>' : ""}
        ${!p.availability ? '<span class="badge out">Out of Stock</span>' : ""}
      </a>

      <div class="product-body">
        <span class="product-cat">${esc(p.category_name || "")}</span>
        <h3 class="product-name">
          <a href="product-details.html?id=${p.id}">${esc(p.name)}</a>
        </h3>
        <div class="product-price">${priceHTML} <small>/ ${esc(p.unit || "piece")}</small></div>

        <div class="product-actions">
          <a class="btn btn-sm btn-primary" href="product-details.html?id=${p.id}">View</a>
          <button class="btn btn-sm btn-outline" onclick="addToCartById(${p.id})">Add to Cart</button>
        </div>
      </div>
    </div>`;
}

/* ============================================================
   PRODUCTS LISTING PAGE
   ============================================================ */
let productsState = {
  page: 1,
  limit: 12,
  filters: {},
};

async function initProductsPage() {
  const grid = document.getElementById("productsGrid");
  if (!grid) return;

  const params = new URLSearchParams(window.location.search);
  productsState.filters = Object.fromEntries(params.entries());
  productsState.page = 1;

  await buildFilterSidebar();
  syncFilterInputs();
  await loadProducts();

  const searchForm = document.getElementById("searchForm");
  if (searchForm && !searchForm._bound) {
    searchForm._bound = true;
    searchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      productsState.filters.q = document
        .getElementById("searchInput")
        .value.trim();
      productsState.page = 1;
      updateURL();
      loadProducts();
    });
  }
}

function updateURL() {
  const params = new URLSearchParams();
  Object.entries(productsState.filters).forEach(([k, v]) => {
    if (v !== "" && v !== null && v !== undefined) params.set(k, v);
  });
  const qs = params.toString();
  history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
}

async function loadProducts() {
  const grid = document.getElementById("productsGrid");
  if (!grid) return;
  const countEl = document.getElementById("resultCount");
  grid.innerHTML = `<p class="loading"><span class="spinner"></span>Loading products…</p>`;

  const params = new URLSearchParams();
  Object.entries(productsState.filters).forEach(([k, v]) => {
    if (v !== "" && v !== null && v !== undefined) params.set(k, v);
  });
  params.set("page", productsState.page);
  params.set("limit", productsState.limit);

  try {
    const res = await api("/products?" + params.toString());
    const items = res.data || [];
    const meta = res.meta || {};

    if (countEl) {
      countEl.textContent = meta.total
        ? `${meta.total} product${meta.total === 1 ? "" : "s"} found`
        : "";
    }

    if (!items.length) {
      const q = productsState.filters.q;
      grid.innerHTML = `<p class="empty">
        ${q ? `No products found for "${esc(q)}".` : "No products are currently available in this category."}
      </p>`;
      const pag = document.getElementById("pagination");
      if (pag) pag.innerHTML = "";
      return;
    }

    grid.innerHTML = items.map(productCardHTML).join("");
    renderPagination(meta);
  } catch (err) {
    grid.innerHTML = `<p class="empty">Unable to load products. Please try again.</p>`;
  }
}

function renderPagination(meta) {
  const host = document.getElementById("pagination");
  if (!host || !meta.pages || meta.pages <= 1) {
    if (host) host.innerHTML = "";
    return;
  }

  let html = `<button ${meta.page === 1 ? "disabled" : ""} onclick="gotoPage(${meta.page - 1})">‹ Prev</button>`;

  for (let i = 1; i <= meta.pages; i++) {
    if (i === 1 || i === meta.pages || Math.abs(i - meta.page) <= 1) {
      html += `<button class="${i === meta.page ? "active" : ""}" onclick="gotoPage(${i})">${i}</button>`;
    } else if (Math.abs(i - meta.page) === 2) {
      html += `<button disabled>…</button>`;
    }
  }

  html += `<button ${meta.page === meta.pages ? "disabled" : ""} onclick="gotoPage(${meta.page + 1})">Next ›</button>`;
  host.innerHTML = html;
}

function gotoPage(p) {
  productsState.page = p;
  loadProducts();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function buildFilterSidebar() {
  const host = document.getElementById("filters");
  if (!host) return;

  let opts = {
    brands: [],
    colors: [],
    materials: [],
    sizes: [],
    categories: [],
  };
  try {
    const res = await api("/products/filters");
    opts = res.data || opts;
  } catch {}

  const topCats = opts.categories.filter((c) => !c.parent_id);

  host.innerHTML = `
    <h3>Filters</h3>

    <div class="filter-group">
      <label>Category</label>
      <select id="fCategory">
        <option value="">All categories</option>
        ${topCats.map((c) => `<option value="${esc(c.slug)}">${esc(c.name)}</option>`).join("")}
      </select>
    </div>

    <div class="filter-group">
      <label>Brand</label>
      <select id="fBrand">
        <option value="">All brands</option>
        ${opts.brands.map((b) => `<option value="${esc(b)}">${esc(b)}</option>`).join("")}
      </select>
    </div>

    <div class="filter-group">
      <label>Price range (₹)</label>
      <div class="price-row">
        <input type="number" id="fMin" placeholder="Min" min="0">
        <input type="number" id="fMax" placeholder="Max" min="0">
      </div>
    </div>

    <div class="filter-group">
      <label>Color</label>
      <select id="fColor">
        <option value="">Any colour</option>
        ${opts.colors.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("")}
      </select>
    </div>

    <div class="filter-group">
      <label>Material</label>
      <select id="fMaterial">
        <option value="">Any material</option>
        ${opts.materials.map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join("")}
      </select>
    </div>

    <div class="filter-group">
      <label>Size</label>
      <select id="fSize">
        <option value="">Any size</option>
        ${opts.sizes.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("")}
      </select>
    </div>

    <div class="filter-group">
      <label>Availability</label>
      <select id="fAvailability">
        <option value="">All</option>
        <option value="1">In stock only</option>
      </select>
    </div>

    <button class="btn btn-outline btn-block btn-sm" id="clearFilters">Clear Filters</button>
  `;

  const val = (id) => {
    const el = document.getElementById(id);
    return el ? el.value.trim() : "";
  };

  const apply = () => {
    productsState.filters.category = val("fCategory");
    productsState.filters.brand = val("fBrand");
    productsState.filters.min_price = val("fMin");
    productsState.filters.max_price = val("fMax");
    productsState.filters.color = val("fColor");
    productsState.filters.material = val("fMaterial");
    productsState.filters.size = val("fSize");
    productsState.filters.availability = val("fAvailability");
    productsState.page = 1;
    updateURL();
    loadProducts();
  };

  [
    "fCategory",
    "fBrand",
    "fColor",
    "fMaterial",
    "fSize",
    "fAvailability",
  ].forEach((id) =>
    document.getElementById(id)?.addEventListener("change", apply),
  );

  let timer;
  ["fMin", "fMax"].forEach((id) => {
    document.getElementById(id)?.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(apply, 500);
    });
  });

  document.getElementById("clearFilters")?.addEventListener("click", () => {
    productsState.filters = {};
    productsState.page = 1;
    document.querySelectorAll("#filters select").forEach((s) => (s.value = ""));
    document.querySelectorAll("#filters input").forEach((i) => (i.value = ""));
    updateURL();
    loadProducts();
  });
}

function syncFilterInputs() {
  const f = productsState.filters;
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el && value) el.value = value;
  };
  set("fCategory", f.category);
  set("fBrand", f.brand);
  set("fMin", f.min_price);
  set("fMax", f.max_price);
  set("fColor", f.color);
  set("fMaterial", f.material);
  set("fSize", f.size);
  set("fAvailability", f.availability);

  const sortEl = document.getElementById("sortSelect");
  if (sortEl && f.sort) sortEl.value = f.sort;

  const searchEl = document.getElementById("searchInput");
  if (searchEl && f.q) searchEl.value = f.q;
}

document.addEventListener("change", (e) => {
  if (e.target && e.target.id === "sortSelect") {
    productsState.filters.sort = e.target.value;
    productsState.page = 1;
    updateURL();
    loadProducts();
  }
});

/* ============================================================
   PRODUCT DETAILS PAGE
   ============================================================ */
async function initProductDetails() {
  const host = document.getElementById("productDetails");
  if (!host) return;

  const id = new URLSearchParams(location.search).get("id");
  if (!id) {
    host.innerHTML = `<p class="empty">Product not specified.</p>`;
    return;
  }

  host.innerHTML = `<p class="loading"><span class="spinner"></span>Loading product…</p>`;

  try {
    const res = await api("/products/" + id);
    const p = res.data;
    window.__productCache[p.id] = p;
    document.title = p.name + " | M Hardware & Sanitary";

    const images = [p.image, ...(p.additional_images || [])].filter(Boolean);
    const hasDiscount = p.discount_price && p.discount_price < p.price;

    const specs = [
      ["Brand", p.brand],
      ["SKU", p.sku],
      ["Category", p.category_name],
      ["Material", p.material],
      ["Size", p.size],
      ["Colour", p.color],
      ["Weight", p.weight],
      ["Finish", p.finish],
      ["Thickness", p.thickness],
      ["Pieces per box", p.pieces_per_box],
      ["Coverage", p.coverage],
    ].filter(([, v]) => v);

    host.innerHTML = `
      <div class="pd-layout">
        <div class="pd-gallery">
          <div class="pd-main-img">
            <img id="pdMain" src="${imgSrc(images[0])}" alt="${esc(p.name)}"
                 onerror="this.src=PLACEHOLDER">
          </div>
          ${
            images.length > 1
              ? `
            <div class="pd-thumbs">
              ${images
                .map(
                  (src, i) =>
                    `<img src="${imgSrc(src)}" onclick="swapMainImage('${esc(src)}')"
                      onerror="this.src=PLACEHOLDER" alt="view ${i + 1}">`,
                )
                .join("")}
            </div>`
              : ""
          }
        </div>

        <div class="pd-info">
          <span class="product-cat">${esc(p.category_name || "")}</span>
          <h1>${esc(p.name)}</h1>
          ${p.brand ? `<p style="color:var(--muted);margin:0">Brand: <b>${esc(p.brand)}</b></p>` : ""}

          <div class="pd-price">
            ${money(p.final_price)}
            ${hasDiscount ? `<span class="price-old">${money(p.price)}</span>` : ""}
            <small style="font-size:.9rem;font-weight:400;color:var(--muted)">/ ${esc(p.unit || "piece")}</small>
          </div>

          <p>
            ${
              p.availability
                ? `<span style="color:#166534;font-weight:600">● In Stock</span>${p.stock ? ` (${p.stock} available)` : ""}`
                : `<span style="color:#991b1b;font-weight:600">● Out of Stock</span>`
            }
          </p>

          <p>${esc(p.short_description || p.description || "")}</p>

          ${p.description && p.short_description ? `<p>${esc(p.description)}</p>` : ""}

          <div class="pd-actions">
            <button class="btn btn-primary" onclick="addToCartById(${p.id})">🛒 Add to Cart</button>
            <button class="btn btn-accent" onclick="openInquiry(${p.id})">📩 Request Quote</button>
            <button class="btn btn-whatsapp" onclick="whatsappProduct(${p.id})">💬 WhatsApp</button>
            <a class="btn btn-outline" href="tel:${esc(window.__settings.phone || "")}">📞 Call</a>
          </div>

          ${
            specs.length
              ? `
            <h3 class="mt-3">Specifications</h3>
            <ul class="pd-specs">
              ${specs.map(([k, v]) => `<li><span>${esc(k)}</span><span>${esc(v)}</span></li>`).join("")}
            </ul>`
              : ""
          }
        </div>
      </div>

      <div id="inquiryBox" class="form-card mt-3 hidden">
        <h1>Request a Quote</h1>
        <div id="inquiryAlert"></div>
        <form id="inquiryForm">
          <input type="hidden" name="product_id" value="${p.id}">
          <input type="hidden" name="product_name" value="${esc(p.name)}">
          <div class="form-row">
            <div class="form-group"><label>Name *</label><input name="name" required></div>
            <div class="form-group"><label>Phone *</label><input name="phone" required></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label>Email</label><input type="email" name="email"></div>
            <div class="form-group"><label>Quantity</label><input name="quantity" placeholder="e.g. 10"></div>
          </div>
          <div class="form-group"><label>Address</label><input name="address"></div>
          <div class="form-group"><label>Message</label><textarea name="message"
              placeholder="Any specific requirement?"></textarea></div>
          <button class="btn btn-primary btn-block" type="submit">Send Enquiry</button>
        </form>
      </div>

      <section class="mt-3">
        <div class="section-head"><h2>Related Products</h2></div>
        <div id="relatedProducts" class="product-grid"></div>
      </section>
    `;

    bindInquiryForm();
    loadRelated(p.id);
  } catch (err) {
    host.innerHTML = `<p class="empty">Product not found.</p>`;
  }
}

function swapMainImage(src) {
  const main = document.getElementById("pdMain");
  if (main) main.src = src;
}

async function loadRelated(id) {
  const host = document.getElementById("relatedProducts");
  if (!host) return;
  try {
    const res = await api(`/products/${id}/related`);
    const items = res.data || [];
    host.innerHTML = items.length
      ? items.map(productCardHTML).join("")
      : `<p class="empty">No related products.</p>`;
  } catch {
    host.innerHTML = `<p class="empty">No related products.</p>`;
  }
}

function openInquiry(id) {
  const box = document.getElementById("inquiryBox");
  if (box) {
    box.classList.remove("hidden");
    box.scrollIntoView({ behavior: "smooth" });
  }
}

function bindInquiryForm() {
  const form = document.getElementById("inquiryForm");
  if (!form || form._bound) return;
  form._bound = true;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const alertBox = document.getElementById("inquiryAlert");
    const payload = Object.fromEntries(new FormData(form).entries());

    try {
      const res = await api("/inquiries", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      alertBox.innerHTML = `<div class="alert alert-success">${esc(res.message)}</div>`;
      form.reset();
    } catch (err) {
      alertBox.innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
    }
  });
}

function whatsappProduct(id) {
  const p = window.__productCache[id];
  if (!p) return;
  const number = (window.__settings.whatsapp || "").replace(/\D/g, "");
  const link = `${location.origin}/product-details.html?id=${p.id}`;
  const text =
    `Hello, I am interested in this product:\n\n` +
    `*${p.name}*\n` +
    `Price: ${money(p.final_price)} / ${p.unit || "piece"}\n` +
    `${link}\n\nPlease share more details.`;
  window.open(
    `https://wa.me/${number}?text=${encodeURIComponent(text)}`,
    "_blank",
  );
}
