/* ============================================================
   app.js — shared helpers, navbar, footer, page router
   ============================================================ */

const API_BASE = "/api";

/* Global cache so buttons can look up product data instantly */
window.__productCache = {};
window.__settings = {};

/* ---------- tiny fetch wrapper ---------- */
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
    data = { success: false, message: "Invalid server response" };
  }
  if (!res.ok || data.success === false) {
    throw new Error(data.message || "Request failed");
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
    `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">
      <rect width="400" height="400" fill="#eef4fa"/>
      <text x="50%" y="50%" font-family="Arial" font-size="42"
            fill="#9db8d2" text-anchor="middle" dy=".35em">🛠️</text>
    </svg>`,
  );

function imgSrc(path) {
  return path && path.trim() ? path : PLACEHOLDER;
}

/* ---------- money formatting ---------- */
function money(value) {
  const n = Number(value || 0);
  return "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

/* ============================================================
   SETTINGS + NAV + FOOTER
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

function renderNav() {
  const s = window.__settings;
  const page = document.body.dataset.page;
  const host = document.getElementById("site-nav");
  if (!host) return;

  const links = [
    ["index.html", "Home", "home"],
    ["products.html", "Products", "products"],
    ["categories.html", "Categories", "categories"],
    ["gallery.html", "Gallery", "gallery"],
    ["about.html", "About", "about"],
    ["contact.html", "Contact", "contact"],
  ];

  host.innerHTML = `
    <nav class="nav">
      <div class="nav-inner">
        <a class="nav-logo" href="index.html">
          🛠️ ${esc(s.business_name || "M Hardware & Sanitary")}
        </a>

        <button class="nav-toggle" id="navToggle" aria-label="Menu">☰</button>

        <div class="nav-links" id="navLinks">
          ${links
            .map(
              ([href, label, key]) =>
                `<a href="${href}" class="${page === key ? "active" : ""}">${label}</a>`,
            )
            .join("")}
          <div class="nav-actions">
            <a class="btn btn-whatsapp btn-sm" data-whatsapp="Hello, I would like to enquire about your products." href="#">
              WhatsApp
            </a>
            <a class="btn btn-accent btn-sm" href="tel:${esc(s.phone || "")}">📞 Call Now</a>
          </div>
        </div>
      </div>
    </nav>`;

  const toggle = document.getElementById("navToggle");
  const menu = document.getElementById("navLinks");
  if (toggle && menu) {
    toggle.addEventListener("click", () => menu.classList.toggle("open"));
  }
}

function renderFooter() {
  const s = window.__settings;
  const host = document.getElementById("site-footer");
  if (!host) return;

  const tel = (s.phone || "").replace(/\s/g, "");

  host.innerHTML = `
    <footer class="footer">
      <div class="footer-top">

        <div>
          <h2 class="footer-logo">${esc(s.business_name || "M Hardware & Sanitary")}</h2>
          <p>${esc(s.footer_text || "")}</p>
          <div class="social-icons">
            <a href="${esc(s.facebook || "#")}" target="_blank" rel="noopener">📘</a>
            <a href="${esc(s.instagram || "#")}" target="_blank" rel="noopener">📸</a>
            <a href="${esc(s.youtube || "#")}" target="_blank" rel="noopener">▶</a>
            <a href="${esc(s.twitter || "#")}" target="_blank" rel="noopener">🐦</a>
            <a href="https://wa.me/${esc(s.whatsapp || "")}" target="_blank" rel="noopener">💬</a>
          </div>
        </div>

        <div>
          <h3>Our Products</h3>
          <ul>
            <li><a href="products.html?category=sanitary">Sanitary</a></li>
            <li><a href="products.html?category=hardware">Hardware</a></li>
            <li><a href="products.html?category=tiles">Tiles</a></li>
            <li><a href="products.html?category=pipes">Pipes</a></li>
            <li><a href="products.html?category=machines">Machines</a></li>
          </ul>
        </div>

        <div>
          <h3>Useful Links</h3>
          <ul>
            <li><a href="index.html">Home</a></li>
            <li><a href="products.html">Products</a></li>
            <li><a href="categories.html">Categories</a></li>
            <li><a href="about.html">About</a></li>
            <li><a href="contact.html">Contact</a></li>
          </ul>
        </div>

        <div>
          <h3>Contact</h3>
          <ul>
            <li>📞 <a href="tel:${esc(tel)}">${esc(s.phone || "")}</a></li>
            <li>💬 <a href="https://wa.me/${esc(s.whatsapp || "")}" target="_blank" rel="noopener">WhatsApp</a></li>
            <li>✉️ <a href="mailto:${esc(s.email || "")}">${esc(s.email || "")}</a></li>
            <li>📍 ${esc(s.address || "")}</li>
            <li>🕒 ${esc(s.opening_hours || "")}</li>
          </ul>
        </div>
      </div>

      <div class="footer-bottom">
        <p>© ${new Date().getFullYear()} ${esc(s.business_name || "M Hardware & Sanitary")}. All rights reserved.</p>
        <p class="dev">Developed by <span>${esc(s.developer_name || "Moosa")}</span></p>
      </div>
    </footer>`;
}

/* ---------- WhatsApp links ---------- */
function applyWhatsappLinks() {
  const number = (window.__settings.whatsapp || "").replace(/\D/g, "");
  document.querySelectorAll("[data-whatsapp]").forEach((el) => {
    const text = el.getAttribute("data-whatsapp") || "";
    el.href = `https://wa.me/${number}?text=${encodeURIComponent(text)}`;
    el.target = "_blank";
    el.rel = "noopener";
  });
  document.querySelectorAll("[data-phone-link]").forEach((el) => {
    el.href = "tel:" + (window.__settings.phone || "");
  });
}

/* ============================================================
   PAGE ROUTER
   ============================================================ */
document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  renderNav();
  renderFooter();
  applyWhatsappLinks();

  const page = document.body.dataset.page;
  try {
    if (page === "home") initHome();
    if (page === "products") initProductsPage();
    if (page === "product-details") initProductDetails();
    if (page === "categories") initCategoriesPage();
    if (page === "cart") initCartPage();
    if (page === "contact") initContactPage();
    if (page === "gallery") initGalleryPage();
  } catch (err) {
    console.error(err);
  }

  if (typeof initAIAssistant === "function") initAIAssistant();
});
