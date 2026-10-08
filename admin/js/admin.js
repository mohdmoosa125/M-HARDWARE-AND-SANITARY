/* ============================================================
   admin.js — shared logic for every admin page
   (fetch helper, shell, toasts, dialogs, formatters, charts,
    image-agent helpers, dashboard + analytics)
   ============================================================ */

const API_BASE = "/api";

/* ---------- fetch helper ---------- */
async function api(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let data;
  try {
    data = await res.json();
  } catch {
    data = { success: false, message: "Invalid server response (" + res.status + ")" };
  }

  if (res.status === 401 && !path.startsWith("/auth/login")) {
    // Not logged in -> go to login page
    const p = location.pathname;
    if (!p.endsWith("login.html") && !/\/admin\/?$/.test(p)) location.href = "login.html";
    throw new Error("Not authenticated");
  }
  if (!res.ok || data.success === false) {
    const err = new Error(data.message || "Request failed");
    err.status = res.status;
    throw err;
  }
  return data;
}

/** Multipart upload -> returns the stored URL. folder: products | categories | gallery */
async function apiUpload(folder, file) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_BASE}/upload/${folder}`, { method: "POST", body: fd, credentials: "same-origin" });
  let data;
  try { data = await res.json(); } catch { data = { success: false, message: "Upload failed (" + res.status + ")" }; }
  if (res.status === 401) { location.href = "login.html"; throw new Error("Not authenticated"); }
  if (!res.ok || !data.success) throw new Error(data.message || "Upload failed");
  return data.data.url;
}

/* ---------- formatting ---------- */
function esc(t) {
  if (t === null || t === undefined) return "";
  return String(t)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
function money(v) {
  return "₹" + Number(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}
function moneyShort(v) {
  v = Number(v || 0);
  if (v >= 1e7) return "₹" + (v / 1e7).toFixed(v >= 1e8 ? 0 : 1).replace(/\.0$/, "") + "Cr";
  if (v >= 1e5) return "₹" + (v / 1e5).toFixed(v >= 1e6 ? 0 : 1).replace(/\.0$/, "") + "L";
  if (v >= 1e3) return "₹" + (v / 1e3).toFixed(v >= 1e4 ? 0 : 1).replace(/\.0$/, "") + "k";
  return "₹" + Math.round(v);
}
function num(v) { return Number(v || 0).toLocaleString("en-IN"); }
function imgSrc(p) { return p && String(p).trim() ? p : ""; }

/** API timestamps are naive UTC ("2026-10-08T15:17:28"); plain dates are local. */
function parseDate(s) {
  if (!s) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); }
  if (!/[zZ]|[+-]\d{2}:?\d{2}$/.test(s)) s += "Z";
  const d = new Date(s);
  return isNaN(d) ? null : d;
}
function fmtDate(s) {
  const d = parseDate(s);
  return d ? d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—";
}
function fmtDateTime(s) {
  const d = parseDate(s);
  return d ? d.toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" }) : "—";
}
function debounce(fn, ms = 300) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}
function qsGet(name) { return new URLSearchParams(location.search).get(name); }
function setQuery(params) {
  const u = new URL(location.href);
  Object.entries(params).forEach(([k, v]) => (v === "" || v == null ? u.searchParams.delete(k) : u.searchParams.set(k, v)));
  history.replaceState(null, "", u);
}
function digits(s) { return String(s || "").replace(/\D/g, ""); }
function waNumber(phone) {
  const d = digits(phone);
  return d.length === 10 ? "91" + d : d;
}

/* ---------- state snippets ---------- */
const loadingHTML = (msg = "Loading…") => `<div class="loading" role="status"><span class="spinner"></span>${esc(msg)}</div>`;
const emptyHTML = (msg) => `<div class="empty">${icon("inbox")}${esc(msg)}</div>`;
const errorHTML = (msg) => `<div class="error-state" role="alert">Could not load: ${esc(msg)}</div>`;

/* ---------- icons (inline SVG, decorative) ---------- */
const ICONS = {
  dashboard: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
  box: '<path d="M21 8l-9-5-9 5 9 5 9-5z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  tag: '<path d="M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
  cart: '<circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M2 3h3l2.7 12.4a1 1 0 0 0 1 .8h9.6a1 1 0 0 0 1-.8L21 7H6"/>',
  users: '<circle cx="9" cy="8" r="4"/><path d="M2 21c0-4 3-6 7-6s7 2 7 6"/><path d="M16 4a4 4 0 0 1 0 8"/><path d="M22 21c0-3-1.5-5-4-5.7"/>',
  file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M8 13h8M8 17h5"/>',
  layers: '<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 17l-5-5-9 8"/>',
  chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
  sparkles: '<path d="M12 3l1.8 4.7 4.7 1.8-4.7 1.8L12 16l-1.8-4.7-4.7-1.8 4.7-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
  chart: '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  wrench: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
  external: '<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
  logout: '<path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4"/><path d="M10 17l5-5-5-5"/><path d="M15 12H3"/>',
  alert: '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18h.01"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  refresh: '<path d="M20 11a8 8 0 0 0-14.8-3.6L4 9"/><path d="M4 4v5h5"/><path d="M4 13a8 8 0 0 0 14.8 3.6L20 15"/><path d="M20 20v-5h-5"/>',
  download: '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M5 21h14"/>',
  printer: '<path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M6 14h12v7H6z"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  inbox: '<path d="M3 13l3-8h12l3 8"/><path d="M3 13v6h18v-6h-5l-1 2h-6l-1-2z"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/>',
};
function icon(name, cls = "icon") {
  return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[name] || ""}</svg>`;
}

/* ---------- sidebar + topbar ---------- */
const NAV_ITEMS = [
  ["dashboard.html", "Dashboard", "dashboard", "Overview"],
  ["products.html", "Products", "box", "Catalogue"],
  ["categories.html", "Categories", "folder"],
  ["brands.html", "Brands", "tag"],
  ["orders.html", "Orders", "cart", "Sales"],
  ["customers.html", "Customers", "users"],
  ["invoices.html", "Invoices", "file"],
  ["inventory.html", "Inventory", "layers"],
  ["inquiries.html", "Inquiries", "mail", "Engagement"],
  ["gallery.html", "Gallery", "image"],
  ["ai.html#assistant", "AI Assistant", "chat", "AI"],
  ["ai.html#images", "AI Image Generator", "sparkles"],
  ["analytics.html", "Analytics", "chart", "Insights"],
  ["settings.html", "Settings", "settings"],
];
let ADMIN_USER = null;

function setPageTitle(t) {
  const h = document.getElementById("pageTitle");
  if (h) h.textContent = t;
  document.title = `${t} | M Hardware Admin`;
}

function markActiveNav(activePage) {
  let key = activePage;
  if (activePage === "ai.html") key = "ai.html" + (location.hash === "#images" ? "#images" : "#assistant");
  document.querySelectorAll(".nav a").forEach((a) => {
    const on = a.getAttribute("href") === key;
    a.classList.toggle("active", on);
    if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
}

async function renderAdminShell(activePage, title) {
  // verify login
  let user;
  try {
    user = (await api("/auth/me")).data;
  } catch {
    return null;
  }
  ADMIN_USER = user;

  let navHTML = "";
  NAV_ITEMS.forEach(([href, label, ic, group]) => {
    if (group) navHTML += `<div class="nav-label">${group}</div>`;
    navHTML += `<a href="${href}">${icon(ic)}<span>${label}</span></a>`;
  });

  const initial = esc((user.username || "A").charAt(0).toUpperCase());
  const layout = document.createElement("div");
  layout.className = "layout";
  layout.innerHTML = `
    <aside class="sidebar" id="sidebar" aria-label="Admin navigation">
      <div class="brand"><span class="brand-mark">${icon("wrench")}</span>
        <span>M Hardware<small>Admin panel</small></span></div>
      <nav class="nav">${navHTML}</nav>
    </aside>
    <div class="overlay" id="navOverlay"></div>
    <div class="main">
      <header class="topbar">
        <button class="btn btn-outline btn-sm menu-btn" id="menuBtn" aria-label="Open navigation menu" aria-controls="sidebar" aria-expanded="false">${icon("menu")}<span>Menu</span></button>
        <h1 id="pageTitle">${esc(title || "Dashboard")}</h1>
        <div class="user">
          <span class="avatar" aria-hidden="true">${initial}</span>
          <span class="who">Signed in as <b>${esc(user.username)}</b></span>
          <a class="btn btn-ghost btn-sm" href="/" target="_blank" rel="noopener">${icon("external")}View site</a>
          <button class="btn btn-outline btn-sm" id="logoutBtn">${icon("logout")}Logout</button>
        </div>
      </header>
      ${user.default_password ? `
        <div class="pw-banner" role="alert">${icon("alert")}
          <span><b>Security:</b> you are still using the default admin password.</span>
          <a href="settings.html#password">Settings → Change admin password</a>
        </div>` : ""}
      <main class="content" id="adminContent" tabindex="-1"></main>
    </div>`;

  document.body.innerHTML = "";
  document.body.appendChild(layout);
  if (title) setPageTitle(title);
  markActiveNav(activePage);
  if (activePage === "ai.html") window.addEventListener("hashchange", () => markActiveNav("ai.html"));

  const menuBtn = document.getElementById("menuBtn");
  const setNav = (open) => {
    layout.classList.toggle("nav-open", open);
    menuBtn.setAttribute("aria-expanded", String(open));
    if (open) layout.querySelector(".nav a")?.focus();
  };
  menuBtn.addEventListener("click", () => setNav(!layout.classList.contains("nav-open")));
  document.getElementById("navOverlay").addEventListener("click", () => setNav(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && layout.classList.contains("nav-open")) { setNav(false); menuBtn.focus(); } });
  layout.querySelectorAll(".nav a").forEach((a) => a.addEventListener("click", () => setNav(false)));

  document.getElementById("logoutBtn").addEventListener("click", async () => {
    try { await api("/auth/logout", { method: "POST" }); } catch {}
    location.href = "login.html";
  });

  return document.getElementById("adminContent");
}

/* ---------- toasts ---------- */
function toast(message, type = "info", ms = 4500) {
  let host = document.getElementById("toastHost");
  if (!host) {
    host = document.createElement("div");
    host.id = "toastHost";
    host.className = "toast-host";
    host.setAttribute("aria-live", "polite");
    document.body.appendChild(host);
  }
  const el = document.createElement("div");
  el.className = "toast " + type;
  el.setAttribute("role", type === "error" ? "alert" : "status");
  el.innerHTML = `<span class="t-msg">${esc(message)}</span><button aria-label="Dismiss notification">×</button>`;
  el.querySelector("button").onclick = () => el.remove();
  host.appendChild(el);
  if (ms) setTimeout(() => el.remove(), ms);
  return el;
}

/* ---------- modal / drawer / confirm ---------- */
function openModal({ title, body = "", footer = "", drawer = false, wide = false, onClose } = {}) {
  const prevFocus = document.activeElement;
  const back = document.createElement("div");
  back.className = "modal-backdrop" + (drawer ? " drawer-backdrop" : "");
  const id = "m" + Math.random().toString(36).slice(2, 8);
  back.innerHTML = `
    <div class="${drawer ? "drawer" : "modal"}" role="dialog" aria-modal="true" aria-labelledby="${id}" ${wide ? 'style="max-width:720px"' : ""}>
      <div class="modal-head"><h2 id="${id}">${esc(title || "")}</h2>
        <button class="btn btn-ghost btn-sm" data-close aria-label="Close dialog">${icon("x")}</button></div>
      <div class="modal-body">${body}</div>
      ${footer ? `<div class="modal-foot">${footer}</div>` : ""}
    </div>`;
  const close = () => {
    back.remove();
    document.removeEventListener("keydown", onKey);
    if (prevFocus && prevFocus.focus) prevFocus.focus();
    if (onClose) onClose();
  };
  const onKey = (e) => {
    if (e.key === "Escape") close();
    if (e.key === "Tab") { // simple focus trap
      const f = [...back.querySelectorAll("button, a[href], input, select, textarea, [tabindex]:not([tabindex='-1'])")].filter((x) => !x.disabled);
      if (!f.length) return;
      if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
    }
  };
  back.addEventListener("click", (e) => { if (e.target === back || e.target.closest("[data-close]")) close(); });
  document.addEventListener("keydown", onKey);
  document.body.appendChild(back);
  const first = back.querySelector(".modal-body input, .modal-body select, .modal-foot .btn-primary, .modal-foot .btn-danger") || back.querySelector("[data-close]");
  first && first.focus();
  return { el: back, body: back.querySelector(".modal-body"), close };
}

function confirmDialog({ title = "Are you sure?", message = "", confirmLabel = "Confirm", danger = false } = {}) {
  return new Promise((resolve) => {
    let done = false;
    const m = openModal({
      title,
      body: `<p class="mt-0">${esc(message)}</p>`,
      footer: `<button class="btn btn-outline" data-close>Cancel</button>
               <button class="btn ${danger ? "btn-danger" : "btn-primary"}" data-ok>${esc(confirmLabel)}</button>`,
      onClose: () => { if (!done) resolve(false); },
    });
    m.el.querySelector("[data-ok]").focus();
    m.el.querySelector("[data-ok]").onclick = () => { done = true; m.close(); resolve(true); };
  });
}

function promptDialog({ title, label, value = "", confirmLabel = "Save", help = "" } = {}) {
  return new Promise((resolve) => {
    let done = false;
    const m = openModal({
      title,
      body: `<div class="form-group"><label for="promptInput">${esc(label)}</label>
             <input id="promptInput" value="${esc(value)}">${help ? `<div class="help">${esc(help)}</div>` : ""}</div>`,
      footer: `<button class="btn btn-outline" data-close>Cancel</button><button class="btn btn-primary" data-ok>${esc(confirmLabel)}</button>`,
      onClose: () => { if (!done) resolve(null); },
    });
    const inp = m.el.querySelector("#promptInput");
    const ok = () => { done = true; const v = inp.value; m.close(); resolve(v); };
    m.el.querySelector("[data-ok]").onclick = ok;
    inp.addEventListener("keydown", (e) => { if (e.key === "Enter") ok(); });
    inp.focus(); inp.select();
  });
}

async function copyText(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); } catch {}
    ta.remove();
  }
  toast("Copied to clipboard", "success", 2000);
  if (btn) { const t = btn.innerHTML; btn.textContent = "Copied"; setTimeout(() => (btn.innerHTML = t), 1500); }
}

/** Disable a button while an async action runs. */
async function withBusy(btn, fn, busyLabel) {
  if (!btn) return fn();
  const old = btn.innerHTML;
  btn.disabled = true;
  if (busyLabel) btn.innerHTML = `<span class="spinner"></span>${esc(busyLabel)}`;
  try { return await fn(); } finally { btn.disabled = false; btn.innerHTML = old; }
}

/* ---------- badges ---------- */
const ORDER_STATUSES = [
  ["pending", "Pending", "badge-amber"],
  ["confirmed", "Confirmed", "badge-blue"],
  ["processing", "Processing", "badge-violet"],
  ["ready_for_pickup", "Ready for pickup", "badge-blue"],
  ["out_for_delivery", "Out for delivery", "badge-violet"],
  ["delivered", "Delivered", "badge-green"],
  ["cancelled", "Cancelled", "badge-red"],
];
const PAYMENT_STATUSES = [
  ["pending", "Pending", "badge-amber"],
  ["paid", "Paid", "badge-green"],
  ["cash", "Cash received", "badge-green"],
  ["failed", "Failed", "badge-red"],
  ["refunded", "Refunded", "badge-grey"],
];
const PAYMENT_METHODS = { cod: "Cash on delivery", upi: "UPI", online: "Online" };
function statusLabel(s) { const r = ORDER_STATUSES.find((x) => x[0] === s); return r ? r[1] : (s || "—"); }
function statusBadge(s, label) {
  const r = ORDER_STATUSES.find((x) => x[0] === s);
  return `<span class="badge ${r ? r[2] : "badge-grey"}">${esc(label || (r ? r[1] : s || "—"))}</span>`;
}
function paymentBadge(s) {
  const r = PAYMENT_STATUSES.find((x) => x[0] === s);
  return `<span class="badge ${r ? r[2] : "badge-grey"}">${esc(r ? r[1] : s || "—")}</span>`;
}
function stockBadge(p) {
  const st = p.stock_status || (p.stock <= 0 ? "out" : "in");
  if (st === "out" || !p.availability) return `<span class="badge badge-red">${p.availability ? "Out" : "Unavailable"} · ${num(p.stock)}</span>`;
  if (st === "low") return `<span class="badge badge-amber">Low · ${num(p.stock)}</span>`;
  return `<span class="badge badge-green">${num(p.stock)}</span>`;
}
function optionList(list, selected, blankLabel) {
  return (blankLabel !== undefined ? `<option value="">${esc(blankLabel)}</option>` : "") +
    list.map(([v, l]) => `<option value="${esc(v)}" ${String(selected) === String(v) ? "selected" : ""}>${esc(l)}</option>`).join("");
}

/* ---------- pagination ---------- */
function renderPager(el, meta, onPage) {
  if (!el) return;
  if (!meta || !meta.total) { el.innerHTML = ""; return; }
  const { page, pages, total, limit } = meta;
  const from = (page - 1) * limit + 1, to = Math.min(total, page * limit);
  el.innerHTML = `<div class="pager"><span>Showing ${num(from)}–${num(to)} of ${num(total)}</span>
    <div class="hstack">
      <button class="btn btn-outline btn-sm" data-p="${page - 1}" ${page <= 1 ? "disabled" : ""}>Previous</button>
      <span>Page ${page} of ${pages}</span>
      <button class="btn btn-outline btn-sm" data-p="${page + 1}" ${page >= pages ? "disabled" : ""}>Next</button>
    </div></div>`;
  el.querySelectorAll("[data-p]").forEach((b) => b.addEventListener("click", () => onPage(Number(b.dataset.p))));
}

/* ============================================================
   CHARTS — hand-rolled inline SVG, single series, light theme.
   One hue (--chart-1), 2px lines, ≤24px bars with 4px rounded
   data-ends, hairline solid grid, hover tooltip + table view.
   ============================================================ */
function niceScale(max, ticks = 4) {
  if (!(max > 0)) return { max: 1, step: 0.25 };
  const raw = max / ticks;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw);
  return { max: step * ticks, step };
}
function shortDay(dateStr) {
  const d = parseDate(dateStr);
  return d ? d.toLocaleDateString("en-IN", { day: "numeric", month: "short" }) : dateStr;
}

/** Mount a responsive chart: draw(width) returns SVG markup; re-draws on resize. */
function mountChart(el, draw, after) {
  const render = () => {
    const w = Math.max(260, Math.floor(el.clientWidth || 600));
    if (el._w === w) return;
    el._w = w;
    el.querySelector(".chart-canvas").innerHTML = draw(w);
    if (after) after(el, w);
  };
  render();
  if (window.ResizeObserver) {
    if (el._ro) el._ro.disconnect();
    el._ro = new ResizeObserver(() => render());
    el._ro.observe(el);
  }
}

function chartTableHTML(points, valueLabel, fmt) {
  return `<details class="chart-table"><summary>View as table</summary>
    <div class="table-wrap"><table><thead><tr><th>Date</th><th class="right">${esc(valueLabel)}</th></tr></thead>
    <tbody>${points.map((p) => `<tr><td>${esc(shortDay(p.date))}</td><td class="right num">${esc(fmt(p.value))}</td></tr>`).join("")}</tbody></table></div></details>`;
}

/**
 * Time series chart. kind: "area" (line + wash) | "bars".
 * points: [{date:"YYYY-MM-DD", value}]
 */
function timeChart(el, points, { kind = "area", height = 220, fmt = num, axisFmt, valueLabel = "Value", emptyText = "No data for this period yet." } = {}) {
  axisFmt = axisFmt || fmt;
  const total = points.reduce((s, p) => s + (Number(p.value) || 0), 0);
  if (!points.length || total === 0) {
    el.innerHTML = `<div class="chart-empty">${esc(emptyText)}</div>`;
    return;
  }
  el.classList.add("chart");
  el.innerHTML = `<div class="chart-canvas"></div><div class="chart-tip" hidden></div>${chartTableHTML(points, valueLabel, fmt)}`;
  const n = points.length;
  const max = Math.max(...points.map((p) => Number(p.value) || 0));
  const scale = niceScale(max);
  const padL = 46, padR = 8, padT = 10, padB = 26;

  const geom = (w) => {
    const pw = w - padL - padR, ph = height - padT - padB;
    const band = pw / n;
    const x = (i) => padL + band * i + band / 2;
    const y = (v) => padT + ph - (v / scale.max) * ph;
    return { pw, ph, band, x, y };
  };

  mountChart(el, (w) => {
    const { pw, ph, band, x, y } = geom(w);
    let s = `<svg viewBox="0 0 ${w} ${height}" width="${w}" height="${height}" role="img" aria-label="${esc(valueLabel)} chart, ${n} days">`;
    // grid + y ticks
    for (let v = 0; v <= scale.max + 1e-9; v += scale.step) {
      const yy = Math.round(y(v)) + 0.5;
      s += `<line class="${v === 0 ? "base-line" : "grid-line"}" x1="${padL}" x2="${padL + pw}" y1="${yy}" y2="${yy}"/>`;
      s += `<text class="tick" x="${padL - 8}" y="${yy + 4}" text-anchor="end">${esc(axisFmt(v))}</text>`;
    }
    // x labels: ~6 evenly spaced
    const every = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(pw / 70))));
    points.forEach((p, i) => {
      if (i % every === 0 || i === n - 1) {
        if (i !== n - 1 && n - 1 - i < every * 0.6) return;
        s += `<text class="tick" x="${x(i)}" y="${height - 6}" text-anchor="middle">${esc(shortDay(p.date))}</text>`;
      }
    });
    if (kind === "bars") {
      const bw = Math.max(2, Math.min(24, band - 2));
      const r = Math.min(4, bw / 2);
      points.forEach((p, i) => {
        const v = Number(p.value) || 0;
        if (!v) return;
        const x0 = x(i) - bw / 2, y0 = y(v), h = y(0) - y0;
        const rr = Math.min(r, h);
        // rounded data-end (top), square at baseline
        s += `<path class="bar" data-i="${i}" d="M${x0},${y(0)} V${y0 + rr} Q${x0},${y0} ${x0 + rr},${y0} H${x0 + bw - rr} Q${x0 + bw},${y0} ${x0 + bw},${y0 + rr} V${y(0)} Z"/>`;
      });
    } else {
      const line = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(Number(p.value) || 0).toFixed(1)}`).join(" ");
      s += `<path class="series-area" d="${line} L${x(n - 1).toFixed(1)},${y(0)} L${x(0).toFixed(1)},${y(0)} Z"/>`;
      s += `<path class="series-line" d="${line}"/>`;
      s += `<circle class="end-dot" r="4" cx="${x(n - 1).toFixed(1)}" cy="${y(Number(points[n - 1].value) || 0).toFixed(1)}"/>`;
      s += `<line class="crosshair" x1="0" x2="0" y1="${padT}" y2="${padT + ph}" visibility="hidden"/>`;
      s += `<circle class="hover-dot" r="4.5" cx="0" cy="0" visibility="hidden"/>`;
    }
    // hit targets: one full-height band per point (bigger than the mark)
    points.forEach((p, i) => {
      s += `<rect class="hit" data-i="${i}" x="${padL + band * i}" y="${padT}" width="${band}" height="${ph}"/>`;
    });
    return s + "</svg>";
  }, (root, w) => {
    const { x, y } = geom(w);
    const tip = root.querySelector(".chart-tip");
    const svg = root.querySelector("svg");
    const cross = svg.querySelector(".crosshair"), dot = svg.querySelector(".hover-dot");
    const hide = () => {
      tip.hidden = true;
      if (cross) { cross.setAttribute("visibility", "hidden"); dot.setAttribute("visibility", "hidden"); }
      svg.querySelectorAll(".bar.is-hover").forEach((b) => b.classList.remove("is-hover"));
    };
    svg.querySelectorAll(".hit").forEach((h) => {
      h.addEventListener("mouseenter", () => {
        const i = Number(h.dataset.i), p = points[i], v = Number(p.value) || 0;
        hide();
        const scaleX = svg.getBoundingClientRect().width / w || 1;
        const px = x(i) * scaleX, py = (kind === "bars" ? y(v) : y(v)) * scaleX;
        tip.innerHTML = `<span class="muted">${esc(fmtDate(p.date))}</span><b>${esc(fmt(v))}</b> ${esc(valueLabel.toLowerCase())}`;
        tip.style.left = Math.min(Math.max(px, 70), svg.getBoundingClientRect().width - 70) + "px";
        tip.style.top = py + "px";
        tip.hidden = false;
        if (cross) {
          cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("visibility", "visible");
          dot.setAttribute("cx", x(i)); dot.setAttribute("cy", y(v)); dot.setAttribute("visibility", "visible");
        } else {
          const b = svg.querySelector(`.bar[data-i="${i}"]`); if (b) b.classList.add("is-hover");
        }
      });
    });
    svg.addEventListener("mouseleave", hide);
  });
}

/** Ranked horizontal bars (HTML). rows: [{name, value, sub?}] */
function hbarChart(el, rows, { fmt = num, emptyText = "No data yet.", limit = 8, sort = true } = {}) {
  rows = (rows || []).filter((r) => Number(r.value) > 0);
  if (sort) rows = rows.slice().sort((a, b) => b.value - a.value);
  rows = rows.slice(0, limit);
  if (!rows.length) { el.innerHTML = `<div class="chart-empty">${esc(emptyText)}</div>`; return; }
  const max = Math.max(...rows.map((r) => r.value));
  el.innerHTML = `<div class="hbars" role="list">${rows.map((r) => `
    <div class="hbar" role="listitem" title="${esc(r.name)}: ${esc(fmt(r.value))}${r.sub ? " · " + esc(r.sub) : ""}">
      <span class="h-name">${esc(r.name)}</span><span class="h-val">${esc(fmt(r.value))}</span>
      <div class="h-track"><div class="h-fill" style="width:${Math.max(1, (r.value / max) * 100).toFixed(1)}%"></div></div>
    </div>`).join("")}</div>`;
}

/* ============================================================
   IMAGE AGENT helpers (products page, product form, AI page)
   ============================================================ */
function imageBadge(info) {
  const st = info ? info.status : "missing";
  const why = info && (info.error || info.reason) ? ` title="${esc(info.error || info.reason)}"` : "";
  const label = { ready: "Ready", missing: "Missing", processing: "Processing", fallback: "Fallback", failed: "Failed" }[st] || st;
  const cls = { ready: "badge-green", missing: "badge-amber", processing: "badge-blue", fallback: "badge-orange", failed: "badge-red" }[st] || "badge-grey";
  return `<span class="badge ${cls}"${why}>${esc(label)}</span>`;
}

let imageJobTimer = null;

/**
 * Start (or attach to) an image job and render live progress into `panel`.
 * kind: "missing" | "all" | {job_id, total} to resume an existing job.
 */
async function runImageJob(kind, panel, { onDone, buttons = [], limit } = {}) {
  let job_id, total;
  const setBtns = (d) => buttons.forEach((b) => b && (b.disabled = d));
  if (typeof kind === "object") {
    ({ job_id, total } = kind);
  } else {
    if (kind === "all") {
      const ok = await confirmDialog({
        title: "Regenerate ALL product images?",
        message: "This re-creates the image for every product using the configured AI image provider. It can take a long time and uses paid provider credits. Existing images are replaced.",
        confirmLabel: "Generate all", danger: true,
      });
      if (!ok) return;
    }
    setBtns(true);
    try {
      const res = await api(kind === "all" ? "/admin/images/generate-all" : "/admin/images/generate-missing", {
        method: "POST", body: JSON.stringify(kind === "all" ? { confirm: true } : { limit: limit || 0 }),
      });
      ({ job_id, total } = res.data);
      if (!job_id) { toast(res.message || "No products need images.", "info"); setBtns(false); return; }
    } catch (e) {
      toast(e.message, "error"); setBtns(false); return;
    }
  }
  setBtns(true);
  panel.hidden = false;
  panel.innerHTML = `<div class="hstack"><b>Image generation running</b><span class="spacer"></span>
      <button class="btn btn-outline btn-sm" data-cancel>Cancel</button></div>
    <div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="${total}" aria-valuenow="0"><span style="width:0%"></span></div>
    <div class="progress-line" aria-live="polite">Starting…</div>`;
  const bar = panel.querySelector(".progress"), line = panel.querySelector(".progress-line");
  const cancelBtn = panel.querySelector("[data-cancel]");
  cancelBtn.onclick = async () => {
    cancelBtn.disabled = true; cancelBtn.textContent = "Cancelling…";
    try { const r = await api("/admin/images/cancel/" + job_id, { method: "POST" }); toast(r.message || "Cancelling…", "info"); }
    catch (e) { toast(e.message, "error"); cancelBtn.disabled = false; cancelBtn.textContent = "Cancel"; }
  };
  clearInterval(imageJobTimer);
  const tick = async () => {
    try {
      const j = (await api("/admin/images/status/" + job_id)).data;
      const tot = j.total || total || 0;
      bar.setAttribute("aria-valuenow", j.processed);
      bar.firstElementChild.style.width = (tot ? (100 * j.processed) / tot : 0).toFixed(1) + "%";
      line.innerHTML = `<span>${j.state === "running" ? "Processing" : esc(j.state.charAt(0).toUpperCase() + j.state.slice(1))} <b>${j.processed} / ${tot}</b></span>
        <span>Successful <b>${j.succeeded}</b></span><span>Failed <b>${j.failed}</b></span>
        <span>Skipped/fallback <b>${(j.fallback || 0) + (j.skipped || 0)}</b></span>
        ${j.current_product ? `<span>Current: <b>${esc(j.current_product)}</b>${j.current_provider ? ` <span class="muted">(${esc(j.current_provider)})</span>` : ""}</span>` : ""}
        ${j.error ? `<span class="field-error">${esc(j.error)}</span>` : ""}`;
      if (j.state !== "running") {
        clearInterval(imageJobTimer);
        cancelBtn.remove();
        panel.querySelector("b").textContent = "Image generation " + j.state;
        setBtns(false);
        toast(`Images ${j.state}: ${j.succeeded} successful, ${j.failed} failed, ${(j.fallback || 0) + (j.skipped || 0)} skipped/fallback.`, j.failed ? "warning" : "success", 7000);
        if (onDone) onDone(j);
      }
    } catch (e) {
      clearInterval(imageJobTimer);
      line.textContent = e.message;
      setBtns(false);
    }
  };
  tick();
  imageJobTimer = setInterval(tick, 1500);
}

/** Back-compat wrapper (older pages): progress text into statusEl. */
function generateMissingImages(btn, statusEl, onDone) {
  let panel = statusEl;
  if (!panel.classList.contains("progress-panel")) {
    panel = document.createElement("div");
    panel.className = "progress-panel";
    statusEl.replaceWith(panel);
  }
  return runImageJob("missing", panel, { onDone, buttons: [btn], limit: 20 });
}

async function regenerateImage(id, btn, onDone) {
  const old = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span>Generating…`;
  try {
    const res = await api("/admin/images/regenerate/" + id, { method: "POST" });
    const d = res.data || {};
    const detail = d.result && d.result.detail ? ` — ${d.result.detail}` : "";
    toast(`Image ${d.image_status || "updated"}${detail}`, d.image_status === "ready" ? "success" : "warning", 6000);
    if (onDone) onDone(d);
  } catch (e) {
    toast("Regenerate failed: " + e.message, "error");
  }
  btn.innerHTML = old;
  btn.disabled = false;
}

/* ============================================================
   DASHBOARD
   ============================================================ */
function statTile({ label, value, hint, href, dot }) {
  const inner = `<div class="label">${dot ? `<span class="dot ${dot}"></span>` : ""}${esc(label)}</div>
    <div class="value">${esc(value)}</div>${hint ? `<div class="hint">${esc(hint)}</div>` : ""}`;
  return href ? `<a class="stat" href="${href}">${inner}</a>` : `<div class="stat">${inner}</div>`;
}

function seriesPoints(d, key) { return (d.series || []).map((r) => ({ date: r.date, value: Number(r[key]) || 0 })); }

function ordersByStatusRows(d) {
  return ORDER_STATUSES.map(([k, l]) => ({ name: l, value: Number((d.orders_by_status || {})[k]) || 0 }));
}

function recentOrdersTable(orders) {
  if (!orders || !orders.length) return emptyHTML("No orders yet.");
  return `<div class="table-wrap"><table>
    <thead><tr><th>Order</th><th>Customer</th><th>Date</th><th class="right">Total</th><th>Payment</th><th>Status</th></tr></thead>
    <tbody>${orders.map((o) => `
      <tr class="clickable-row" onclick="location.href='order-detail.html?id=${Number(o.id)}'">
        <td><a href="order-detail.html?id=${Number(o.id)}"><b>${esc(o.order_number || "#" + o.id)}</b></a></td>
        <td>${esc((o.shipping && o.shipping.name) || (o.customer && o.customer.name) || "—")}</td>
        <td class="nowrap">${esc(fmtDate(o.created_at))}</td>
        <td class="right num">${money(o.grand_total ?? o.total)}</td>
        <td>${paymentBadge(o.payment_status)}</td>
        <td>${statusBadge(o.status, o.status_label)}</td>
      </tr>`).join("")}</tbody></table></div>`;
}

function lowStockList(items) {
  if (!items || !items.length) return emptyHTML("All products have healthy stock.");
  return `<div class="table-wrap"><table>
    <thead><tr><th>Product</th><th>Stock</th><th>Min</th><th></th></tr></thead>
    <tbody>${items.slice(0, 8).map((p) => `
      <tr><td><div class="cell-title">${esc(p.name)}</div><div class="cell-sub">${esc(p.sku || p.category_name || "")}</div></td>
        <td>${stockBadge(p)}</td><td class="num">${num(p.min_stock ?? 5)}</td>
        <td class="right"><a class="btn btn-outline btn-sm" href="inventory.html?q=${encodeURIComponent(p.name)}">Restock</a></td></tr>`).join("")}
    </tbody></table></div>`;
}

async function initDashboard() {
  const host = await renderAdminShell("dashboard.html", "Dashboard");
  if (!host) return;
  host.innerHTML = loadingHTML("Loading statistics…");

  let d;
  try {
    d = (await api("/admin/stats?days=30")).data;
  } catch (err) {
    host.innerHTML = `<div class="card">${errorHTML(err.message)}</div>`;
    return;
  }
  let img = null;
  try { img = (await api("/admin/images/report")).data.counts; } catch {}

  host.innerHTML = `
    <div class="stat-grid">
      ${statTile({ label: "Total products", value: num(d.total_products), href: "products.html" })}
      ${statTile({ label: "Total orders", value: num(d.total_orders), href: "orders.html" })}
      ${statTile({ label: "Pending orders", value: num(d.pending_orders), href: "orders.html?status=pending", dot: d.pending_orders ? "dot-warn" : "" })}
      ${statTile({ label: "Today's sales", value: money(d.today_sales), hint: `${num(d.today_orders)} order${d.today_orders === 1 ? "" : "s"} today` })}
      ${statTile({ label: "Total customers", value: num(d.total_customers), href: "customers.html", hint: `${num(d.registered_customers)} registered` })}
      ${statTile({ label: "Low stock", value: num(d.low_stock_count), href: "inventory.html?status=low", dot: d.low_stock_count ? "dot-warn" : "" })}
      ${statTile({ label: "Out of stock", value: num(d.out_of_stock_count), href: "inventory.html?status=out", dot: d.out_of_stock_count ? "dot-bad" : "" })}
      ${statTile({ label: "Products without images", value: num(d.products_without_images), href: "products.html?missing_images=1" })}
      ${statTile({ label: "Fallback images", value: num(d.fallback_images), href: "products.html?image_status=fallback" })}
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-head"><div><h2>Sales · last 30 days</h2><p class="sub">Revenue from non-cancelled orders</p></div>
          <span class="chart-total">${money((d.series || []).reduce((s, r) => s + (Number(r.sales) || 0), 0))}</span></div>
        <div id="salesChart"></div>
      </div>
      <div class="card">
        <div class="card-head"><div><h2>Orders · last 30 days</h2><p class="sub">Orders placed per day</p></div>
          <span class="chart-total">${num((d.series || []).reduce((s, r) => s + (Number(r.orders) || 0), 0))}</span></div>
        <div id="ordersChart"></div>
      </div>
    </div>

    <div class="grid-3">
      <div class="card"><div class="card-head"><h2>Orders by status</h2></div><div id="statusChart"></div></div>
      <div class="card"><div class="card-head"><h2>Top products</h2><span class="sub">by revenue</span></div><div id="topChart"></div></div>
      <div class="card"><div class="card-head"><h2>Category sales</h2></div><div id="catChart"></div></div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-head"><h2>Recent orders</h2><a class="btn btn-outline btn-sm" href="orders.html">View all orders</a></div>
        ${recentOrdersTable(d.recent_orders)}
      </div>
      <div class="stack" style="gap:20px">
        <div class="card mb-0">
          <div class="card-head"><h2>Low stock</h2><a class="btn btn-outline btn-sm" href="inventory.html?status=low">Open inventory</a></div>
          ${lowStockList(d.low_stock)}
        </div>
        <div class="card mb-0">
          <div class="card-head"><h2>AI image status</h2><a class="btn btn-outline btn-sm" href="ai.html#images">Image generator</a></div>
          ${img ? `<div class="stat-grid mb-0" style="grid-template-columns:repeat(auto-fill,minmax(110px,1fr))">
              ${[["Ready", img.ready, "dot-good"], ["Missing", img.missing, "dot-warn"], ["Fallback", img.fallback, "dot-grey"], ["Failed", img.failed, "dot-bad"], ["Processing", img.processing, "dot-info"]]
                .map(([l, v, c]) => `<div class="stat" style="box-shadow:none"><div class="label"><span class="dot ${c}"></span>${l}</div><div class="value" style="font-size:1.2rem">${num(v)}</div></div>`).join("")}
            </div>` : emptyHTML("Image report unavailable.")}
        </div>
      </div>
    </div>`;

  timeChart(document.getElementById("salesChart"), seriesPoints(d, "sales"), { kind: "area", fmt: money, axisFmt: moneyShort, valueLabel: "Sales", emptyText: "No sales in the last 30 days." });
  timeChart(document.getElementById("ordersChart"), seriesPoints(d, "orders"), { kind: "bars", fmt: num, valueLabel: "Orders", emptyText: "No orders yet." });
  hbarChart(document.getElementById("statusChart"), ordersByStatusRows(d), { sort: false, emptyText: "No orders yet." });
  hbarChart(document.getElementById("topChart"), (d.top_products || []).map((p) => ({ name: p.name, value: p.revenue, sub: `${num(p.quantity)} sold` })), { fmt: money, emptyText: "No product sales yet." });
  hbarChart(document.getElementById("catChart"), (d.category_sales || []).map((c) => ({ name: c.name || "Uncategorised", value: c.revenue })), { fmt: money, emptyText: "No category sales yet." });
}

/* ============================================================
   ANALYTICS
   ============================================================ */
async function initAnalytics() {
  const host = await renderAdminShell("analytics.html", "Analytics");
  if (!host) return;
  let days = [7, 30, 90].includes(Number(qsGet("days"))) ? Number(qsGet("days")) : 30;

  host.innerHTML = `
    <div class="toolbar">
      <div class="seg" role="group" aria-label="Date range">
        ${[7, 30, 90].map((n) => `<button data-days="${n}" aria-pressed="${n === days}">Last ${n} days</button>`).join("")}
      </div>
      <span class="spacer"></span>
      <span class="muted small" id="rangeNote"></span>
    </div>
    <div id="analyticsBody">${loadingHTML()}</div>`;

  host.querySelectorAll("[data-days]").forEach((b) => b.addEventListener("click", () => {
    days = Number(b.dataset.days);
    host.querySelectorAll("[data-days]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    setQuery({ days });
    load();
  }));

  async function load() {
    const body = document.getElementById("analyticsBody");
    body.innerHTML = loadingHTML();
    let d;
    try { d = (await api("/admin/stats?days=" + days)).data; }
    catch (e) { body.innerHTML = `<div class="card">${errorHTML(e.message)}</div>`; return; }
    const series = d.series || [];
    const rev = series.reduce((s, r) => s + (Number(r.sales) || 0), 0);
    const ord = series.reduce((s, r) => s + (Number(r.orders) || 0), 0);
    document.getElementById("rangeNote").textContent = series.length
      ? `${fmtDate(series[0].date)} – ${fmtDate(series[series.length - 1].date)}` : "";
    body.innerHTML = `
      <div class="stat-grid">
        ${statTile({ label: `Revenue · ${days} days`, value: money(rev) })}
        ${statTile({ label: `Orders · ${days} days`, value: num(ord) })}
        ${statTile({ label: "Average order value", value: ord ? money(rev / ord) : "—" })}
        ${statTile({ label: "All-time revenue", value: money(d.total_revenue) })}
        ${statTile({ label: "All-time orders", value: num(d.total_orders) })}
        ${statTile({ label: "Customers with orders", value: num(d.customers_with_orders) })}
      </div>
      <div class="card"><div class="card-head"><div><h2>Sales</h2><p class="sub">Daily revenue, last ${days} days</p></div><span class="chart-total">${money(rev)}</span></div><div id="aSales"></div></div>
      <div class="card"><div class="card-head"><div><h2>Orders</h2><p class="sub">Orders placed per day, last ${days} days</p></div><span class="chart-total">${num(ord)}</span></div><div id="aOrders"></div></div>
      <div class="grid-3">
        <div class="card"><div class="card-head"><h2>Orders by status</h2></div><div id="aStatus"></div></div>
        <div class="card"><div class="card-head"><h2>Top products</h2><span class="sub">by revenue</span></div><div id="aTop"></div></div>
        <div class="card"><div class="card-head"><h2>Category sales</h2></div><div id="aCat"></div></div>
      </div>`;
    timeChart(document.getElementById("aSales"), seriesPoints(d, "sales"), { kind: "area", height: 300, fmt: money, axisFmt: moneyShort, valueLabel: "Sales", emptyText: `No sales in the last ${days} days.` });
    timeChart(document.getElementById("aOrders"), seriesPoints(d, "orders"), { kind: "bars", height: 260, fmt: num, valueLabel: "Orders", emptyText: `No orders in the last ${days} days.` });
    hbarChart(document.getElementById("aStatus"), ordersByStatusRows(d), { sort: false, emptyText: "No orders yet." });
    hbarChart(document.getElementById("aTop"), (d.top_products || []).map((p) => ({ name: p.name, value: p.revenue, sub: `${num(p.quantity)} sold` })), { fmt: money, limit: 10, emptyText: "No product sales yet." });
    hbarChart(document.getElementById("aCat"), (d.category_sales || []).map((c) => ({ name: c.name || "Uncategorised", value: c.revenue })), { fmt: money, limit: 10, emptyText: "No category sales yet." });
  }
  load();
}
