/* ============================================================
   admin.js — shared logic for every admin page
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
    data = { success: false, message: "Invalid server response" };
  }

  if (res.status === 401) {
    // Not logged in -> go to login page
    if (!location.pathname.endsWith("login.html")) {
      location.href = "login.html";
    }
    throw new Error("Not authenticated");
  }
  if (!res.ok || data.success === false)
    throw new Error(data.message || "Request failed");
  return data;
}

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
  return (
    "₹" + Number(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })
  );
}
function imgSrc(p) {
  return p && p.trim() ? p : "";
}

/* ---------- sidebar + topbar ---------- */
const NAV_ITEMS = [
  ["dashboard.html", "📊 Dashboard"],
  ["products.html", "📦 Products"],
  ["categories.html", "🗂️ Categories"],
  ["orders.html", "🧾 Orders"],
  ["inquiries.html", "📩 Inquiries"],
  ["gallery.html", "🖼️ Gallery"],
  ["settings.html", "⚙️ Settings"],
];

async function renderAdminShell(activePage) {
  // verify login
  let user;
  try {
    const res = await api("/auth/me");
    user = res.data;
  } catch {
    return null;
  }

  const layout = document.createElement("div");
  layout.className = "layout";
  layout.innerHTML = `
    <aside class="sidebar">
      <div class="brand">🛠️ M Hardware Admin</div>
      ${NAV_ITEMS.map(
        ([href, label]) =>
          `<a href="${href}" class="${href === activePage ? "active" : ""}">${label}</a>`,
      ).join("")}
    </aside>
    <div class="main">
      <div class="topbar">
        <h1 id="pageTitle">Dashboard</h1>
        <div class="user">
          Logged in as <b>${esc(user.username)}</b>
          &nbsp;·&nbsp;
          <a href="#" id="logoutBtn">Logout</a>
          &nbsp;·&nbsp;
          <a href="/" target="_blank">View site ↗</a>
        </div>
      </div>
      <div class="content" id="adminContent"></div>
    </div>`;

  document.body.innerHTML = "";
  document.body.appendChild(layout);

  document.getElementById("logoutBtn").addEventListener("click", async (e) => {
    e.preventDefault();
    await api("/auth/logout", { method: "POST" });
    location.href = "login.html";
  });

  return document.getElementById("adminContent");
}

/* ============================================================
   DASHBOARD
   ============================================================ */
async function initDashboard() {
  const host = await renderAdminShell("dashboard.html");
  if (!host) return;
  document.getElementById("pageTitle").textContent = "Dashboard";

  host.innerHTML = `<p class="loading">Loading statistics…</p>`;

  try {
    const res = await api("/admin/stats");
    const d = res.data;
    let img = { ready: 0, missing: 0, fallback: 0, failed: 0 };
    try { img = (await api("/admin/images/report")).data.counts; } catch {}

    host.innerHTML = `
      <div class="stat-grid">
        <div class="stat"><div class="label">Products</div><div class="value">${d.total_products}</div></div>
        <div class="stat"><div class="label">Categories</div><div class="value">${d.total_categories}</div></div>
        <div class="stat"><div class="label">Orders</div><div class="value">${d.total_orders}</div></div>
        <div class="stat"><div class="label">Customers</div><div class="value">${d.total_customers}</div></div>
        <div class="stat"><div class="label">Inquiries</div><div class="value">${d.total_inquiries}</div></div>
        <div class="stat"><div class="label">Messages</div><div class="value">${d.total_messages}</div></div>
        <div class="stat"><div class="label">Ready images</div><div class="value">${img.ready}</div></div>
        <a class="stat" href="products.html?missing_images=1" style="text-decoration:none;color:inherit"><div class="label">Products without images</div><div class="value">${img.missing + img.failed}</div></a>
        <a class="stat" href="products.html?image_status=fallback" style="text-decoration:none;color:inherit"><div class="label">Fallback images</div><div class="value">${img.fallback}</div></a>
        <div class="stat"><div class="label">Failed images</div><div class="value">${img.failed}</div></div>
      </div>

      <div class="card">
        <h2>⚠️ Low Stock Products</h2>
        ${
          d.low_stock.length
            ? `
          <div class="table-wrap"><table>
            <thead><tr><th>Product</th><th>Stock</th><th>Price</th></tr></thead>
            <tbody>
              ${d.low_stock
                .map(
                  (p) => `
                <tr>
                  <td>${esc(p.name)}</td>
                  <td><span class="badge badge-red">${p.stock}</span></td>
                  <td>${money(p.final_price)}</td>
                </tr>`,
                )
                .join("")}
            </tbody>
          </table></div>`
            : `<p class="empty">All products have healthy stock.</p>`
        }
      </div>

      <div class="card">
        <h2>⭐ Featured Products</h2>
        ${
          d.featured.length
            ? `
          <div class="table-wrap"><table>
            <thead><tr><th>Product</th><th>Category</th><th>Price</th></tr></thead>
            <tbody>
              ${d.featured
                .map(
                  (p) => `
                <tr>
                  <td>${esc(p.name)}</td>
                  <td>${esc(p.category_name || "—")}</td>
                  <td>${money(p.final_price)}</td>
                </tr>`,
                )
                .join("")}
            </tbody>
          </table></div>`
            : `<p class="empty">No featured products yet.</p>`
        }
      </div>

      <div class="card">
        <h2>🧾 Recent Orders</h2>
        ${
          d.recent_orders.length
            ? `
          <div class="table-wrap"><table>
            <thead><tr><th>#</th><th>Customer</th><th>Total</th><th>Status</th></tr></thead>
            <tbody>
              ${d.recent_orders
                .map(
                  (o) => `
                <tr>
                  <td>#${o.id}</td>
                  <td>${esc(o.customer ? o.customer.name : "—")}</td>
                  <td>${money(o.total)}</td>
                  <td><span class="badge badge-amber">${esc(o.status)}</span></td>
                </tr>`,
                )
                .join("")}
            </tbody>
          </table></div>`
            : `<p class="empty">No orders yet.</p>`
        }
      </div>

      <div class="card">
        <h2>📩 Recent Inquiries</h2>
        ${
          d.recent_inquiries.length
            ? `
          <div class="table-wrap"><table>
            <thead><tr><th>Name</th><th>Product</th><th>Phone</th><th>Status</th></tr></thead>
            <tbody>
              ${d.recent_inquiries
                .map(
                  (i) => `
                <tr>
                  <td>${esc(i.name)}</td>
                  <td>${esc(i.product_name || "—")}</td>
                  <td>${esc(i.phone || "—")}</td>
                  <td><span class="badge badge-amber">${esc(i.status)}</span></td>
                </tr>`,
                )
                .join("")}
            </tbody>
          </table></div>`
            : `<p class="empty">No inquiries yet.</p>`
        }
      </div>
    `;
  } catch (err) {
    host.innerHTML = `<p class="empty">Could not load dashboard: ${esc(err.message)}</p>`;
  }
}


/* ============================================================
   IMAGE AGENT helpers (products page, product form, dashboard)
   ============================================================ */
function imageBadge(info) {
  const st = info ? info.status : "missing";
  const why = info && (info.error || info.reason) ? ` title="${esc(info.error || info.reason)}"` : "";
  const label = { ready: "✓ Ready", missing: "⚠ Missing", processing: "⟳ Processing",
                  fallback: "△ Fallback", failed: "✕ Failed" }[st] || st;
  const style = { ready: "", missing: "background:#fef3c7;color:#92400e",
                  processing: "background:#dbeafe;color:#1e40af", fallback: "background:#ffedd5;color:#9a3412",
                  failed: "" }[st] || "";
  const cls = st === "ready" ? "badge-green" : st === "failed" ? "badge-red" : "badge-red";
  return `<span class="badge ${cls}" style="${style}"${why}>${label}</span>`;
}

let imageJobTimer = null;

async function generateMissingImages(btn, statusEl, onDone) {
  btn.disabled = true;
  statusEl.textContent = "Starting…";
  try {
    const res = await api("/admin/images/generate-missing", {
      method: "POST", body: JSON.stringify({ limit: 20 }),
    });
    const { job_id, total } = res.data;
    if (!job_id) { statusEl.textContent = "No products need images."; btn.disabled = false; return; }
    const cancel = document.createElement("button");
    cancel.className = "btn btn-sm btn-outline";
    cancel.textContent = "Cancel";
    cancel.onclick = () => api("/admin/images/cancel/" + job_id, { method: "POST" });
    statusEl.after(cancel);
    imageJobTimer = setInterval(async () => {
      try {
        const j = (await api("/admin/images/status/" + job_id)).data;
        statusEl.textContent =
          `${j.state}: ${j.processed}/${total} · ok ${j.succeeded} · fallback ${j.fallback} · failed ${j.failed}` +
          (j.current_product ? ` — ${j.current_product} (${j.current_provider})` : "");
        if (j.state !== "running") {
          clearInterval(imageJobTimer);
          cancel.remove();
          btn.disabled = false;
          if (onDone) onDone();
        }
      } catch (e) { clearInterval(imageJobTimer); cancel.remove(); btn.disabled = false; statusEl.textContent = e.message; }
    }, 1500);
  } catch (e) {
    statusEl.textContent = e.message;
    btn.disabled = false;
  }
}

async function regenerateImage(id, btn, onDone) {
  btn.disabled = true;
  const old = btn.textContent;
  btn.textContent = "Generating…";
  try {
    const res = await api("/admin/images/regenerate/" + id, { method: "POST" });
    if (onDone) onDone(res.data);
  } catch (e) {
    alert("Regenerate failed: " + e.message);
  }
  btn.textContent = old;
  btn.disabled = false;
}
