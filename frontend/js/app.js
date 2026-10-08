/* ============================================================
   app.js — shared helpers, header, footer, toasts, page boot
   ============================================================ */

const API_BASE = "/api";

/* Global caches so buttons can look up data instantly */
window.__productCache = {};
window.__settings = {};
window.__me = null;              // logged-in customer (or null)
window.__wishlist = new Set();   // product ids in the customer's wishlist

/* ---------- fetch wrapper ---------- */
async function api(path, options = {}) {
  let res;
  try {
    res = await fetch(API_BASE + path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error("Network problem. Please check your connection and try again.");
  }
  let data;
  try {
    data = await res.json();
  } catch {
    data = { success: false, message: "Something went wrong. Please try again." };
  }
  if (!res.ok || data.success === false) {
    const err = new Error(data.message || "Request failed. Please try again.");
    err.status = res.status;
    throw err;
  }
  return data;
}

/* ---------- HTML escaping (prevents broken layout / XSS) ---------- */
function esc(text) {
  if (text === null || text === undefined) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/* ---------- inline SVG placeholder for missing images ---------- */
const PLACEHOLDER =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
      <rect width="400" height="400" fill="#eef4fa"/>
      <path d="M150 230l40-48 32 38 22-26 56 66H120z" fill="#c9daea"/>
      <circle cx="245" cy="160" r="18" fill="#c9daea"/>
    </svg>`,
  );

function imgSrc(path) {
  return path && String(path).trim() ? path : PLACEHOLDER;
}

/* ---------- money / dates ---------- */
function money(value) {
  const n = Number(value || 0);
  return (window.__settings.currency_symbol || "₹") +
    n.toLocaleString("en-IN", { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 });
}

function fmtDate(iso, withTime = false) {
  if (!iso) return "";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  const opts = { day: "numeric", month: "short", year: "numeric" };
  if (withTime) Object.assign(opts, { hour: "numeric", minute: "2-digit" });
  return d.toLocaleString("en-IN", opts);
}

function productUrl(p) {
  return p && p.slug ? `/products/${encodeURIComponent(p.slug)}` : `/product-details.html?id=${p.id}`;
}

function flag(key) {
  return ["1", "true", "yes", "on"].includes(String(window.__settings[key] || "").toLowerCase());
}

function debounce(fn, ms = 300) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

/* ---------- icons (inline SVG, always paired with text or aria-label) ---------- */
const ICONS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  cart: '<circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/><path d="M2.5 3h2.7l2.4 11.2a1.6 1.6 0 0 0 1.6 1.3h8.3a1.6 1.6 0 0 0 1.6-1.2L21 7H6"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
  heart: '<path d="M12 20.5s-7.5-4.6-9.3-9.2C1.4 7.9 3.6 4.5 7 4.5c2 0 3.6 1.1 5 3 1.4-1.9 3-3 5-3 3.4 0 5.6 3.4 4.3 6.8-1.8 4.6-9.3 9.2-9.3 9.2z"/>',
  phone: '<path d="M5 3h3.5l1.7 4.4-2.3 1.5a12 12 0 0 0 7.2 7.2l1.5-2.3L21 15.5V19a2 2 0 0 1-2.2 2A17 17 0 0 1 3 5.2 2 2 0 0 1 5 3z"/>',
  whatsapp: '<path d="M3.5 20.5l1.3-4.1A8.5 8.5 0 1 1 8 19.6z"/><path d="M9 8.6c.2 2.9 2.6 5.6 6 6.3l1-1.4-1.9-1-1 .8a5 5 0 0 1-2.4-2.4l.8-1-1-1.9z"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  chevronRight: '<path d="m9 6 6 6-6 6"/>',
  chevronLeft: '<path d="m15 6-6 6 6 6"/>',
  arrowRight: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  sparkle: '<path d="M12 3l1.8 4.9L19 9.7l-5.2 1.8L12 16.5l-1.8-5L5 9.7l5.2-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
  truck: '<path d="M2 6h11v10H2zM13 9h4.5L21 12.5V16h-8"/><circle cx="6.5" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',
  shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
  tag: '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.4"/>',
  tools: '<path d="M14.5 6.5a4 4 0 0 0 5 5L21 13l-8 8-3-3 8-8M3 21l6-6"/><path d="m4 4 5 5M3 7l4-4"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
  list: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
  filter: '<path d="M4 5h16l-6 7.5V19l-4 1.5v-8z"/>',
  compare: '<path d="M8 4v16M16 4v16M4 8h8M12 16h8"/>',
  pin: '<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 6.5 8.5 6.5 8.5-6.5"/>',
  download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
  printer: '<path d="M7 9V3h10v6M7 17H4v-7h16v7h-3"/><rect x="7" y="14" width="10" height="7"/>',
  box: '<path d="M3 7.5 12 3l9 4.5v9L12 21l-9-4.5z"/><path d="M3 7.5 12 12l9-4.5M12 12v9"/>',
  receipt: '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>',
  logout: '<path d="M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  send: '<path d="M4 12 20 4l-6 16-3-7z"/>',
  expand: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
  star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
  store: '<path d="M4 9h16l-1.5-5h-13zM5 9v11h14V9M9 20v-6h6v6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5v.5"/>',
  calculator: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15v3"/>',
};

function icon(name, cls = "") {
  return `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;
}

/* ============================================================
   SETTINGS, CUSTOMER SESSION
   ============================================================ */
async function loadSettings() {
  try {
    const res = await api("/settings");
    window.__settings = res.data || {};
  } catch (err) {
    console.warn("Could not load settings:", err.message);
    window.__settings = {};
  }
}

async function loadMe() {
  try {
    window.__me = (await api("/account/me")).data;
  } catch {
    window.__me = null;
  }
  window.__wishlist = new Set();
  if (window.__me) {
    try {
      const res = await api("/account/wishlist");
      (res.data || []).forEach((p) => window.__wishlist.add(p.id));
    } catch {}
  }
}

function waNumber() {
  return String(window.__settings.whatsapp || "").replace(/\D/g, "");
}

function waLink(text) {
  return `https://wa.me/${waNumber()}?text=${encodeURIComponent(text || "")}`;
}

function telLink() {
  return "tel:" + String(window.__settings.phone || "").replace(/\s/g, "");
}

/* ============================================================
   HEADER
   ============================================================ */
const NAV_LINKS = [
  ["/index.html", "Home", "home"],
  ["/products.html", "Products", "products"],
  ["/categories.html", "Categories", "categories"],
  ["/about.html", "About", "about"],
  ["/gallery.html", "Gallery", "gallery"],
  ["/contact.html", "Contact", "contact"],
];

function logoHTML() {
  const s = window.__settings;
  const name = s.business_name || "M Hardware & Sanitary";
  const mark = s.logo ? `<img src="${esc(s.logo)}" alt="">` : esc(name.trim().charAt(0) || "M");
  return `
    <a class="logo" href="/index.html" aria-label="${esc(name)} home">
      <span class="logo-mark">${mark}</span>
      <span><span class="logo-name">${esc(name)}</span><span class="logo-sub">Hardware · Sanitary · Tiles</span></span>
    </a>`;
}

function renderNav() {
  const s = window.__settings;
  const page = document.body.dataset.page;
  const host = document.getElementById("site-nav");
  if (!host) return;
  const me = window.__me;
  const accountLabel = me ? esc(me.name.split(" ")[0]) : "Account";

  host.innerHTML = `
    ${flag("demo_mode") ? `<div class="demo-bar" role="note">Demo store — the phone, WhatsApp, email and address shown are placeholders until the owner updates them.</div>` : ""}
    <div class="topbar"><div class="wrap">
      <span>${icon("pin")} ${esc(s.address || "Bhopal, Madhya Pradesh")}</span>
      <span>${s.opening_hours ? `${icon("clock")} ${esc(s.opening_hours)}` : ""}
        ${s.phone ? `&nbsp;·&nbsp; <a href="${telLink()}">${icon("phone")} ${esc(s.phone)}</a>` : ""}</span>
    </div></div>
    <header class="site-header" id="siteHeader">
      <div class="wrap header-main">
        <button class="h-action menu-btn" id="menuBtn" aria-label="Open menu" aria-expanded="false">${icon("menu")}</button>
        ${logoHTML()}
        <div class="header-search" role="search">
          <form id="globalSearchForm" autocomplete="off">
            <label class="sr-only" for="globalSearch">Search products</label>
            <input id="globalSearch" type="search" placeholder="Search taps, pipes, tiles, SKU, brand…"
                   aria-autocomplete="list" aria-controls="searchSuggest">
            <button type="submit" aria-label="Search">${icon("search")}</button>
          </form>
          <div class="suggest hidden" id="searchSuggest" role="listbox"></div>
        </div>
        <nav class="header-actions" aria-label="Shortcuts">
          <button class="h-action hide-sm" type="button" onclick="openAI()">${icon("sparkle")}<span class="h-label">Ask AI</span></button>
          <a class="h-action hide-sm" href="/account.html#wishlist">${icon("heart")}<span class="h-label">Wishlist</span></a>
          <a class="h-action" href="/account.html">${icon("user")}<span class="h-label">${accountLabel}</span></a>
          <a class="h-action" href="/cart.html" aria-label="Cart">${icon("cart")}<span class="h-label">Cart</span>
            <span class="h-badge" data-cart-count style="display:none">0</span></a>
          ${s.phone ? `<a class="btn btn-primary btn-sm header-call" href="${telLink()}">${icon("phone")} Call</a>` : ""}
        </nav>
      </div>
      <nav class="nav-row" aria-label="Main">
        <div class="wrap">
          ${NAV_LINKS.map(([href, label, key]) =>
            `<a href="${href}" class="${page === key ? "active" : ""}" ${page === key ? 'aria-current="page"' : ""}>${label}</a>`).join("")}
          <span class="nav-spacer"></span>
          ${waNumber() ? `<a href="${waLink("Hello, I would like to enquire about your products.")}" target="_blank" rel="noopener">${icon("whatsapp")} WhatsApp us</a>` : ""}
        </div>
      </nav>
    </header>
    <div class="drawer-backdrop" id="drawerBackdrop"></div>
    <aside class="drawer" id="menuDrawer" aria-label="Menu" aria-hidden="true">
      <div class="drawer-head">${logoHTML()}
        <button class="btn btn-ghost btn-icon" id="menuClose" aria-label="Close menu">${icon("x")}</button></div>
      <div class="drawer-body">
        ${NAV_LINKS.map(([href, label, key]) => `<a class="d-link ${page === key ? "active" : ""}" href="${href}">${label}</a>`).join("")}
        <a class="d-link" href="/account.html">${icon("user")} ${me ? "My account" : "Login / Register"}</a>
        <a class="d-link" href="/account.html#orders">${icon("box")} My orders</a>
        <a class="d-link" href="/account.html#wishlist">${icon("heart")} Wishlist</a>
        <a class="d-link" href="/order.html">${icon("truck")} Track an order</a>
        <a class="d-link" href="#" onclick="closeMenu();openAI();return false;">${icon("sparkle")} Ask our AI assistant</a>
      </div>
      <div class="drawer-foot">
        ${s.phone ? `<a class="btn btn-primary" href="${telLink()}">${icon("phone")} Call ${esc(s.phone)}</a>` : ""}
        ${waNumber() ? `<a class="btn btn-whatsapp" href="${waLink("Hello, I would like to enquire about your products.")}" target="_blank" rel="noopener">${icon("whatsapp")} WhatsApp</a>` : ""}
      </div>
    </aside>`;

  const drawer = document.getElementById("menuDrawer");
  const backdrop = document.getElementById("drawerBackdrop");
  const btn = document.getElementById("menuBtn");
  btn.addEventListener("click", () => {
    drawer.classList.add("open");
    backdrop.classList.add("open");
    drawer.setAttribute("aria-hidden", "false");
    btn.setAttribute("aria-expanded", "true");
    document.getElementById("menuClose").focus();
  });
  document.getElementById("menuClose").addEventListener("click", closeMenu);
  backdrop.addEventListener("click", closeMenu);
  drawer.querySelectorAll("a.d-link").forEach((a) => a.addEventListener("click", closeMenu));

  if (typeof initHeaderSearch === "function") initHeaderSearch();
  if (typeof updateCartCount === "function") updateCartCount();
}

function closeMenu() {
  document.getElementById("menuDrawer")?.classList.remove("open");
  document.getElementById("drawerBackdrop")?.classList.remove("open");
  document.getElementById("menuDrawer")?.setAttribute("aria-hidden", "true");
  document.getElementById("menuBtn")?.setAttribute("aria-expanded", "false");
}

window.addEventListener("scroll", () => {
  document.getElementById("siteHeader")?.classList.toggle("scrolled", window.scrollY > 8);
}, { passive: true });

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeMenu();
});

/* ============================================================
   FOOTER
   ============================================================ */
function renderFooter() {
  const s = window.__settings;
  const host = document.getElementById("site-footer");
  if (!host) return;
  const name = s.business_name || "M Hardware & Sanitary";
  const social = [["facebook", "Facebook"], ["instagram", "Instagram"], ["youtube", "YouTube"], ["twitter", "X / Twitter"]]
    .filter(([k]) => s[k] && s[k] !== "#")
    .map(([k, label]) => `<a href="${esc(s[k])}" target="_blank" rel="noopener">${label}</a>`).join("");

  host.innerHTML = `
    <footer class="footer">
      <div class="wrap footer-top">
        <div>
          <p class="footer-logo">${esc(name)}</p>
          <p>${esc(s.footer_text || "Quality hardware and sanitary products for homes, businesses and construction projects.")}</p>
          ${social ? `<div class="social">${social}</div>` : ""}
        </div>
        <div>
          <h3>Quick links</h3>
          <ul>
            <li><a href="/products.html">Products</a></li>
            <li><a href="/categories.html">Categories</a></li>
            <li><a href="/about.html">About</a></li>
            <li><a href="/gallery.html">Gallery</a></li>
            <li><a href="/contact.html">Contact</a></li>
          </ul>
        </div>
        <div>
          <h3>Customer</h3>
          <ul>
            <li><a href="/account.html">My account</a></li>
            <li><a href="/account.html#orders">Orders</a></li>
            <li><a href="/order.html">Track order</a></li>
            <li><a href="/account.html#wishlist">Wishlist</a></li>
            <li><a href="/cart.html">Cart</a></li>
          </ul>
        </div>
        <div>
          <h3>Categories</h3>
          <ul>
            ${["sanitary", "pipes", "fittings", "hardware", "tiles", "tools", "machines"].map((slug) =>
              `<li><a href="/products.html?category=${slug}">${slug.charAt(0).toUpperCase() + slug.slice(1)}</a></li>`).join("")}
          </ul>
        </div>
        <div>
          <h3>Contact</h3>
          <ul>
            ${s.phone ? `<li>${icon("phone")}<a href="${telLink()}">${esc(s.phone)}</a></li>` : ""}
            ${waNumber() ? `<li>${icon("whatsapp")}<a href="${waLink("Hello!")}" target="_blank" rel="noopener">WhatsApp</a></li>` : ""}
            ${s.email ? `<li>${icon("mail")}<a href="mailto:${esc(s.email)}">${esc(s.email)}</a></li>` : ""}
            <li>${icon("pin")}<span>${esc(s.address || "Bhopal, Madhya Pradesh")}</span></li>
            ${s.opening_hours ? `<li>${icon("clock")}<span>${esc(s.opening_hours)}</span></li>` : ""}
          </ul>
        </div>
      </div>
      <div class="footer-bottom"><div class="wrap">
        <span>© ${new Date().getFullYear()} ${esc(name)}. All rights reserved.</span>
        ${s.developer_name ? `<span>Developed by ${esc(s.developer_name)}</span>` : ""}
      </div></div>
    </footer>`;
}

/* ---------- legacy data-whatsapp / data-phone-link hooks ---------- */
function applyWhatsappLinks() {
  document.querySelectorAll("[data-whatsapp]").forEach((el) => {
    el.href = waLink(el.getAttribute("data-whatsapp") || "");
    el.target = "_blank";
    el.rel = "noopener";
  });
  document.querySelectorAll("[data-phone-link]").forEach((el) => {
    el.href = telLink();
  });
}

/* ============================================================
   FEEDBACK: toasts, dialogs, skeletons, empty states
   ============================================================ */
function toast(message, type = "success", link = null) {
  let host = document.getElementById("toasts");
  if (!host) {
    host = document.createElement("div");
    host.id = "toasts";
    host.className = "toasts";
    host.setAttribute("role", "status");
    host.setAttribute("aria-live", "polite");
    document.body.appendChild(host);
  }
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `${icon(type === "error" ? "info" : "check")}<span>${esc(message)}</span>` +
    (link ? `<a href="${esc(link.href)}">${esc(link.label)}</a>` : "");
  host.appendChild(el);
  setTimeout(() => {
    el.classList.add("leaving");
    setTimeout(() => el.remove(), 250);
  }, type === "error" ? 4500 : 3000);
}

function showToast(message) {          // backwards compatible name
  toast(message);
}

function confirmDialog({ title, text = "", confirm = "Confirm", cancel = "Cancel", danger = false }) {
  return new Promise((resolve) => {
    const wrap = document.createElement("div");
    wrap.className = "modal-backdrop";
    wrap.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="dlgTitle">
        <h3 id="dlgTitle">${esc(title)}</h3>
        ${text ? `<p class="muted">${esc(text)}</p>` : ""}
        <div class="modal-actions">
          <button class="btn btn-outline" data-v="0">${esc(cancel)}</button>
          <button class="btn ${danger ? "btn-danger" : "btn-primary"}" data-v="1">${esc(confirm)}</button>
        </div>
      </div>`;
    const done = (v) => {
      wrap.remove();
      document.removeEventListener("keydown", onKey);
      resolve(v);
    };
    const onKey = (e) => e.key === "Escape" && done(false);
    wrap.addEventListener("click", (e) => {
      if (e.target === wrap) done(false);
      const b = e.target.closest("[data-v]");
      if (b) done(b.dataset.v === "1");
    });
    document.addEventListener("keydown", onKey);
    document.body.appendChild(wrap);
    wrap.querySelector('[data-v="1"]').focus();
  });
}

function skeletonCards(n = 4) {
  return Array.from({ length: n }, () => `
    <div class="sk-card" aria-hidden="true">
      <div class="skeleton sk-img"></div>
      <div class="sk-lines">
        <div class="skeleton sk-line w40"></div>
        <div class="skeleton sk-line w80"></div>
        <div class="skeleton sk-line w60"></div>
      </div>
    </div>`).join("");
}

function emptyState(iconName, title, text = "", actionHTML = "") {
  return `<div class="empty">
      <div class="e-ico">${icon(iconName)}</div>
      <h3>${esc(title)}</h3>
      ${text ? `<p>${esc(text)}</p>` : ""}
      ${actionHTML}
    </div>`;
}

function setButtonLoading(btn, loading, label) {
  if (!btn) return;
  if (loading) {
    btn.dataset.label = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>${esc(label || "Please wait…")}`;
  } else {
    btn.disabled = false;
    if (btn.dataset.label) btn.innerHTML = btn.dataset.label;
  }
}

function setMeta(title, description) {
  const biz = window.__settings.business_name || "M Hardware & Sanitary";
  if (title) document.title = `${title} | ${biz}`;
  if (description) {
    let m = document.querySelector('meta[name="description"]');
    if (!m) {
      m = document.createElement("meta");
      m.name = "description";
      document.head.appendChild(m);
    }
    m.content = description.slice(0, 160);
  }
}

/* ============================================================
   PAGE BOOT
   ============================================================ */
const PAGE_INITS = {
  home: "initHome",
  products: "initProductsPage",
  "product-details": "initProductDetails",
  categories: "initCategoriesPage",
  gallery: "initGalleryPage",
  about: "initAboutPage",
  contact: "initContactPage",
  cart: "initCartPage",
  checkout: "initCheckoutPage",
  account: "initAccountPage",
  order: "initOrderPage",
  compare: "initComparePage",
};

function hydrateIcons(root = document) {
  root.querySelectorAll("[data-icon]:empty").forEach((el) => (el.innerHTML = icon(el.dataset.icon)));
}

function runPageInit(page) {
  hydrateIcons();
  const fn = window[PAGE_INITS[page]];
  if (typeof fn === "function") {
    Promise.resolve()
      .then(() => fn())
      .catch((err) => console.error("Page init failed:", page, err));
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await Promise.all([loadSettings(), loadMe()]);
  renderNav();
  renderFooter();
  applyWhatsappLinks();
  runPageInit(document.body.dataset.page);
  if (typeof initAIAssistant === "function" && window.__settings.ai_assistant_enabled !== "0") initAIAssistant();
  if (typeof renderCompareBar === "function") renderCompareBar();
});
