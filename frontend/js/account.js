/* ============================================================
   account.js — customer account (login/register/reset, profile,
   orders, wishlist, addresses) and the order tracking page.
   ============================================================ */

const ACCOUNT_TABS = [
  ["orders", "My orders", "box"],
  ["wishlist", "Wishlist", "heart"],
  ["addresses", "Saved addresses", "pin"],
  ["profile", "Profile", "user"],
  ["password", "Password", "lock"],
];

const PAY_LABEL = { pending: "Payment pending", paid: "Paid", failed: "Payment failed", refunded: "Refunded", cash: "Paid (cash)" };

function statusPill(o) {
  const cls = o.status === "cancelled" ? "pill-red" : o.status === "delivered" ? "pill-green" : o.status === "pending" ? "pill-amber" : "pill-blue";
  return `<span class="pill ${cls}">${esc(o.status_label || o.status)}</span>`;
}

function payPill(status) {
  const cls = ["paid", "cash"].includes(status) ? "pill-green" : status === "failed" ? "pill-red" : "pill-amber";
  return `<span class="pill ${cls}">${esc(PAY_LABEL[status] || status)}</span>`;
}

function invoiceUrl(o, pdf = false) {
  if (!o.invoice_number) return "";
  return `/invoice/${encodeURIComponent(o.invoice_number)}${pdf ? "/pdf" : ""}${o.access_token ? `?t=${encodeURIComponent(o.access_token)}` : ""}`;
}

function orderUrl(o) {
  return `/order.html?no=${encodeURIComponent(o.order_number)}${o.access_token ? `&t=${encodeURIComponent(o.access_token)}` : ""}`;
}

/* ============================================================
   ACCOUNT PAGE
   ============================================================ */
async function initAccountPage() {
  const host = document.getElementById("accountContent");
  if (!host) return;
  const params = new URLSearchParams(location.search);
  if (params.get("reset")) return renderResetForm(host, params.get("reset"));
  if (!window.__me) return renderAuth(host, location.hash === "#register" ? "register" : "login");
  setMeta("My Account");
  renderAccountShell(host);
}

function renderAuth(host, mode) {
  setMeta(mode === "register" ? "Create account" : "Log in");
  host.innerHTML = `
    <div class="auth-wrap">
      <div class="card">
        <div class="auth-tabs" role="tablist">
          <button role="tab" class="${mode === "login" ? "active" : ""}" aria-selected="${mode === "login"}" data-mode="login">Log in</button>
          <button role="tab" class="${mode === "register" ? "active" : ""}" aria-selected="${mode === "register"}" data-mode="register">Create account</button>
        </div>
        <div id="authAlert" role="alert"></div>
        ${mode === "login" ? `
          <form id="authForm">
            <div class="field"><label for="auLogin">Mobile number or email</label><input id="auLogin" name="login" required autocomplete="username"></div>
            <div class="field"><label for="auPass">Password</label><input id="auPass" name="password" type="password" required autocomplete="current-password"></div>
            <button class="btn btn-primary btn-block btn-lg" type="submit">Log in</button>
            <p class="mt-2 muted" style="text-align:center"><a href="#" id="forgotLink">Forgot password?</a></p>
          </form>` : `
          <form id="authForm">
            <div class="field"><label for="auName">Full name</label><input id="auName" name="name" required autocomplete="name"></div>
            <div class="field"><label for="auPhone">Mobile number</label><input id="auPhone" name="phone" type="tel" required autocomplete="tel" placeholder="10-digit mobile"></div>
            <div class="field"><label for="auEmail">Email <span class="muted">(optional)</span></label><input id="auEmail" name="email" type="email" autocomplete="email"></div>
            <div class="field"><label for="auPass">Password</label><input id="auPass" name="password" type="password" required minlength="8" autocomplete="new-password">
              <span class="hint">At least 8 characters.</span></div>
            <button class="btn btn-primary btn-block btn-lg" type="submit">Create account</button>
          </form>`}
      </div>
      <p class="muted mt-2" style="text-align:center">Placed an order as a guest? <a href="/order.html">Track it here</a>.</p>
    </div>`;

  host.querySelectorAll(".auth-tabs button").forEach((b) => (b.onclick = () => renderAuth(host, b.dataset.mode)));
  document.getElementById("forgotLink")?.addEventListener("click", async (e) => {
    e.preventDefault();
    try {
      const res = await api("/account/forgot", { method: "POST", body: "{}" });
      document.getElementById("authAlert").innerHTML = `<div class="alert alert-info">${esc(res.message)}
        ${waNumber() ? `<br><a href="${waLink("Hello, I need help resetting my account password.")}" target="_blank" rel="noopener">Message us on WhatsApp</a>` : ""}</div>`;
    } catch (err) {
      toast(err.message, "error");
    }
  });
  document.getElementById("authForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setButtonLoading(btn, true);
    try {
      const body = Object.fromEntries(new FormData(e.target).entries());
      const res = await api(mode === "login" ? "/account/login" : "/account/register", { method: "POST", body: JSON.stringify(body) });
      toast(res.message || "Welcome!");
      await afterLogin();
    } catch (err) {
      document.getElementById("authAlert").innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
      setButtonLoading(btn, false);
    }
  });
}

async function afterLogin() {
  await loadMe();
  renderNav();
  if (new URLSearchParams(location.search).get("next") === "checkout") {
    navigateTo("/checkout.html");
    return;
  }
  history.replaceState(history.state, "", "/account.html#orders");
  initAccountPage();
}

function renderResetForm(host, token) {
  setMeta("Reset password");
  host.innerHTML = `
    <div class="auth-wrap"><div class="card">
      <h2>Choose a new password</h2>
      <div id="authAlert" role="alert"></div>
      <form id="resetForm">
        <div class="field"><label for="rpPass">New password</label><input id="rpPass" name="password" type="password" minlength="8" required autocomplete="new-password"></div>
        <button class="btn btn-primary btn-block" type="submit">Save password</button>
      </form>
    </div></div>`;
  document.getElementById("resetForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("button");
    setButtonLoading(btn, true);
    try {
      const res = await api("/account/reset", { method: "POST", body: JSON.stringify({ token, password: e.target.password.value }) });
      toast(res.message);
      await afterLogin();
    } catch (err) {
      document.getElementById("authAlert").innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
      setButtonLoading(btn, false);
    }
  });
}

function currentTab() {
  const h = location.hash.replace("#", "");
  return ACCOUNT_TABS.some(([k]) => k === h) ? h : "orders";
}

function renderAccountShell(host) {
  const me = window.__me;
  const tab = currentTab();
  host.innerHTML = `
    <div class="account-layout">
      <nav class="account-nav" aria-label="Account">
        <div class="who"><b>${esc(me.name)}</b><small class="muted">${esc(me.phone || me.email || "")}</small></div>
        ${ACCOUNT_TABS.map(([k, label, ico]) =>
          `<button data-tab="${k}" class="${k === tab ? "active" : ""}" ${k === tab ? 'aria-current="page"' : ""}>${icon(ico)} ${label}</button>`).join("")}
        <button id="logoutBtn">${icon("logout")} Log out</button>
      </nav>
      <section id="accountPanel" aria-live="polite"></section>
    </div>`;
  host.querySelectorAll("[data-tab]").forEach((b) => (b.onclick = () => {
    history.replaceState(history.state, "", "#" + b.dataset.tab);
    renderAccountShell(host);
  }));
  document.getElementById("logoutBtn").onclick = async () => {
    await api("/account/logout", { method: "POST" }).catch(() => {});
    await loadMe();
    renderNav();
    toast("Logged out");
    initAccountPage();
  };
  ({ orders: renderMyOrders, wishlist: renderWishlist, addresses: renderAddresses,
     profile: renderProfile, password: renderPassword })[tab]();
}

window.addEventListener("hashchange", () => {
  if (document.body.dataset.page === "account" && window.__me) {
    const host = document.getElementById("accountContent");
    if (host) renderAccountShell(host);
  }
});

async function renderMyOrders() {
  const panel = document.getElementById("accountPanel");
  panel.innerHTML = `<div class="card"><h2>My orders</h2><p class="loading"><span class="spinner"></span>Loading orders…</p></div>`;
  try {
    const orders = (await api("/account/orders")).data || [];
    panel.innerHTML = `<div class="card"><h2>My orders</h2>${orders.length ? orders.map((o) => `
      <div class="order-row">
        <div><span class="o-num">${esc(o.order_number)}</span><small>${fmtDate(o.created_at)}</small></div>
        <div>${o.item_count} item${o.item_count === 1 ? "" : "s"}<small>${money(o.grand_total)}</small></div>
        <div>${payPill(o.payment_status)}</div>
        <div>${statusPill(o)}</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <a class="btn btn-outline btn-sm" href="${orderUrl(o)}">View & track</a>
          ${o.invoice_number ? `<a class="btn btn-ghost btn-sm" href="${invoiceUrl(o)}" target="_blank" rel="noopener">${icon("receipt")} Invoice</a>` : ""}
        </div>
      </div>`).join("") : emptyState("box", "No orders yet", "Your orders will appear here.", `<a class="btn btn-primary" href="/products.html">Start shopping</a>`)}</div>`;
  } catch (err) {
    panel.innerHTML = `<div class="card">${emptyState("info", "Unable to load orders", err.message)}</div>`;
  }
}

async function renderWishlist() {
  const panel = document.getElementById("accountPanel");
  panel.innerHTML = `<div class="card"><h2>Wishlist</h2><div class="product-grid">${skeletonCards(3)}</div></div>`;
  try {
    const items = (await api("/account/wishlist")).data || [];
    window.__wishlist = new Set(items.map((p) => p.id));
    panel.innerHTML = `<div class="card"><h2>Wishlist</h2>${items.length
      ? `<div class="product-grid">${items.map(productCardHTML).join("")}</div>`
      : emptyState("heart", "Your wishlist is empty", "Tap the heart on any product to save it here.", `<a class="btn btn-primary" href="/products.html">Browse products</a>`)}</div>`;
  } catch (err) {
    panel.innerHTML = `<div class="card">${emptyState("info", "Unable to load wishlist", err.message)}</div>`;
  }
}

function onWishlistChanged() {
  if (document.body.dataset.page === "account" && currentTab() === "wishlist") renderWishlist();
}

async function renderAddresses() {
  const panel = document.getElementById("accountPanel");
  panel.innerHTML = `<div class="card"><h2>Saved addresses</h2><p class="loading"><span class="spinner"></span>Loading…</p></div>`;
  let list = [];
  try {
    list = (await api("/account/addresses")).data || [];
  } catch (err) {
    panel.innerHTML = `<div class="card">${emptyState("info", "Unable to load addresses", err.message)}</div>`;
    return;
  }
  const s = window.__settings;
  panel.innerHTML = `
    <div class="card">
      <h2>Saved addresses</h2>
      ${list.length ? list.map((a) => `
        <div class="order-row" style="grid-template-columns:1fr auto">
          <div><b>${esc(a.label || "Address")}</b> ${a.is_default ? '<span class="pill pill-blue">Default</span>' : ""}
            <small>${esc([a.name, a.phone].filter(Boolean).join(" · "))}</small>
            <small>${esc([a.address, a.city, a.state, a.pincode].filter(Boolean).join(", "))}</small></div>
          <div style="display:flex;gap:6px">
            ${a.is_default ? "" : `<button class="btn btn-ghost btn-sm" onclick="setDefaultAddress(${a.id})">Make default</button>`}
            <button class="btn btn-danger btn-sm" onclick="deleteAddress(${a.id})">Delete</button>
          </div>
        </div>`).join("") : `<p class="muted">No saved addresses yet.</p>`}
    </div>
    <div class="card">
      <h3>Add an address</h3>
      <div id="addrAlert"></div>
      <form id="addrForm" class="form-grid">
        <div class="field"><label for="adLabel">Label</label><input id="adLabel" name="label" placeholder="Home, Shop, Site…"></div>
        <div class="field"><label for="adPhone">Phone</label><input id="adPhone" name="phone" type="tel"></div>
        <div class="field span-2"><label for="adAddr">Address *</label><textarea id="adAddr" name="address" rows="2" required></textarea></div>
        <div class="field"><label for="adCity">City *</label><input id="adCity" name="city" required value="${esc(s.city || "")}"></div>
        <div class="field"><label for="adState">State</label><input id="adState" name="state" value="${esc(s.state || "")}"></div>
        <div class="field"><label for="adPin">PIN code</label><input id="adPin" name="pincode" inputmode="numeric" maxlength="6"></div>
        <div class="field" style="justify-content:end"><label class="check"><input type="checkbox" name="is_default" value="1"> Set as default</label></div>
        <div class="span-2"><button class="btn btn-primary" type="submit">Save address</button></div>
      </form>
    </div>`;
  document.getElementById("addrForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target).entries());
    body.is_default = !!body.is_default;
    try {
      await api("/account/addresses", { method: "POST", body: JSON.stringify(body) });
      toast("Address saved");
      renderAddresses();
    } catch (err) {
      document.getElementById("addrAlert").innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
    }
  });
}

async function setDefaultAddress(id) {
  try {
    const list = (await api("/account/addresses")).data || [];
    const a = list.find((x) => x.id === id);
    await api("/account/addresses/" + id, { method: "PUT", body: JSON.stringify({ ...a, is_default: true }) });
    renderAddresses();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function deleteAddress(id) {
  if (!(await confirmDialog({ title: "Delete this address?", confirm: "Delete", danger: true }))) return;
  try {
    await api("/account/addresses/" + id, { method: "DELETE" });
    toast("Address removed");
    renderAddresses();
  } catch (err) {
    toast(err.message, "error");
  }
}

function renderProfile() {
  const me = window.__me;
  const panel = document.getElementById("accountPanel");
  panel.innerHTML = `
    <div class="card">
      <h2>Profile</h2>
      <div id="profAlert"></div>
      <form id="profForm" class="form-grid">
        <div class="field span-2"><label for="pfName">Full name</label><input id="pfName" name="name" required value="${esc(me.name)}" autocomplete="name"></div>
        <div class="field"><label for="pfPhone">Mobile number</label><input id="pfPhone" name="phone" type="tel" required value="${esc(me.phone || "")}" autocomplete="tel"></div>
        <div class="field"><label for="pfEmail">Email</label><input id="pfEmail" name="email" type="email" value="${esc(me.email || "")}" autocomplete="email"></div>
        <div class="span-2"><button class="btn btn-primary" type="submit">Save changes</button></div>
      </form>
    </div>`;
  document.getElementById("profForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const res = await api("/account/profile", { method: "PUT", body: JSON.stringify(Object.fromEntries(new FormData(e.target).entries())) });
      window.__me = res.data;
      renderNav();
      toast("Profile updated");
    } catch (err) {
      document.getElementById("profAlert").innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
    }
  });
}

function renderPassword() {
  const panel = document.getElementById("accountPanel");
  panel.innerHTML = `
    <div class="card">
      <h2>Change password</h2>
      <div id="pwAlert"></div>
      <form id="pwForm" style="max-width:420px">
        <div class="field"><label for="pwCur">Current password</label><input id="pwCur" name="current_password" type="password" required autocomplete="current-password"></div>
        <div class="field"><label for="pwNew">New password</label><input id="pwNew" name="new_password" type="password" minlength="8" required autocomplete="new-password"></div>
        <button class="btn btn-primary" type="submit">Update password</button>
      </form>
    </div>`;
  document.getElementById("pwForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api("/account/password", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(e.target).entries())) });
      e.target.reset();
      toast("Password changed");
    } catch (err) {
      document.getElementById("pwAlert").innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
    }
  });
}

/* ============================================================
   ORDER PAGE — confirmation, tracking timeline, invoice
   ============================================================ */
async function initOrderPage() {
  const host = document.getElementById("orderContent");
  if (!host) return;
  const p = new URLSearchParams(location.search);
  const no = p.get("no");
  if (!no) return renderTrackForm(host);
  setMeta("Order " + no);
  host.innerHTML = `<p class="loading"><span class="spinner"></span>Loading your order…</p>`;
  try {
    const order = (await api(`/orders/view/${encodeURIComponent(no)}${p.get("t") ? "?t=" + encodeURIComponent(p.get("t")) : ""}`)).data;
    order.access_token = order.access_token || p.get("t") || "";
    renderOrder(host, order, p.get("new") === "1");
  } catch {
    host.innerHTML = emptyState("search", "Order not found", "Check the link, or track it with your order number and phone.",
      `<a class="btn btn-primary" href="/order.html">Track an order</a>`);
  }
}

function renderTrackForm(host) {
  setMeta("Track your order");
  const recent = guestOrders();
  host.innerHTML = `
    <div class="auth-wrap">
      <div class="card">
        <h2>Track your order</h2>
        <p class="muted">Enter the order number from your confirmation and the mobile number used at checkout.</p>
        <div id="trackAlert" role="alert"></div>
        <form id="trackForm">
          <div class="field"><label for="trNo">Order number</label><input id="trNo" name="order_number" required placeholder="ORD-2026-000001"></div>
          <div class="field"><label for="trPhone">Mobile number</label><input id="trPhone" name="phone" type="tel" required></div>
          <button class="btn btn-primary btn-block" type="submit">Track order</button>
        </form>
      </div>
      ${recent.length ? `<div class="card"><h3>Orders placed on this device</h3>
        ${recent.map((o) => `<div class="mini-line"><div><div class="ml-name">${esc(o.no)}</div><div class="ml-meta">${fmtDate(o.at)} · ${money(o.total)}</div></div>
          <a class="btn btn-outline btn-sm ml-total" href="/order.html?no=${encodeURIComponent(o.no)}&t=${encodeURIComponent(o.t)}">View</a></div>`).join("")}</div>` : ""}
      ${!window.__me ? `<p class="muted mt-2" style="text-align:center"><a href="/account.html">Log in</a> to see all your orders.</p>` : ""}
    </div>`;
  document.getElementById("trackForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("button");
    setButtonLoading(btn, true, "Searching…");
    try {
      const o = (await api("/orders/track", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(e.target).entries())) })).data;
      navigateTo(orderUrl(o));
    } catch (err) {
      document.getElementById("trackAlert").innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
      setButtonLoading(btn, false);
    }
  });
}

function timelineHTML(o) {
  if (o.status === "cancelled") {
    const when = (o.history || []).find((h) => h.status === "cancelled");
    return `<div class="cancelled-box">This order was cancelled${when ? " on " + fmtDate(when.created_at, true) : ""}.</div>`;
  }
  const steps = o.order_type === "pickup"
    ? [["pending", "Order placed"], ["confirmed", "Confirmed"], ["processing", "Processing"], ["ready_for_pickup", "Ready for pickup"], ["delivered", "Collected"]]
    : [["pending", "Order placed"], ["confirmed", "Confirmed"], ["processing", "Processing"], ["out_for_delivery", "Out for delivery"], ["delivered", "Delivered"]];
  const reached = Math.max(0, steps.findIndex(([k]) => k === o.status));
  const when = Object.fromEntries((o.history || []).map((h) => [h.status, h.created_at]));
  return `<ol class="timeline" style="--steps:${steps.length};list-style:none;padding:0" aria-label="Order progress">
    ${steps.map(([k, label], i) => `
      <li class="t-step ${i < reached || (i === reached && k === "delivered") ? "done" : ""} ${i === reached && k !== "delivered" ? "current" : ""}">
        <span class="t-dot">${i <= reached ? icon("check") : ""}</span>${label}
        <small>${when[k] ? fmtDate(when[k], true) : ""}</small>
      </li>`).join("")}
  </ol>`;
}

function renderOrder(host, o, isNew) {
  const s = window.__settings;
  const ship = o.shipping || {};
  host.innerHTML = `
    ${isNew ? `<div class="card success-hero">
      <div class="tick">${icon("check")}</div>
      <h1>Thank you! Your order is placed.</h1>
      <p class="muted">Order <b>${esc(o.order_number)}</b>${o.invoice_number ? ` · Invoice <b>${esc(o.invoice_number)}</b>` : ""}. We'll confirm it shortly${ship.phone ? " on " + esc(ship.phone) : ""}.</p>
      ${!window.__me ? `<p class="muted" style="font-size:.85rem">Bookmark this page or note your order number to track it later.</p>` : ""}
    </div>` : ""}

    <div class="card">
      <div class="card-title">
        <div><h2>Order ${esc(o.order_number)}</h2><span class="muted">Placed ${fmtDate(o.created_at, true)}</span></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">${statusPill(o)} ${payPill(o.payment_status)}</div>
      </div>
      ${timelineHTML(o)}
    </div>

    ${o.payment_method === "upi" && !["paid", "cash"].includes(o.payment_status) && s.upi_id ? `
      <div class="alert alert-info">Pay ${money(o.grand_total)} to UPI ID <b>${esc(s.upi_id)}</b> after we confirm your order, and mention ${esc(o.order_number)} in the note.</div>` : ""}

    <div class="split mt-2" style="align-items:start">
      <div class="card">
        <h3>Items</h3>
        <div class="table-scroll"><table class="items-table">
          <thead><tr><th>Product</th><th class="num">Qty</th><th class="num">Price</th><th class="num">Total</th></tr></thead>
          <tbody>${o.items.map((it) => `<tr>
            <td>${it.product_slug ? `<a href="/products/${encodeURIComponent(it.product_slug)}">${esc(it.product_name)}</a>` : esc(it.product_name)}
              ${it.sku ? `<br><small class="muted">SKU ${esc(it.sku)}</small>` : ""}</td>
            <td class="num">${it.quantity} ${esc(it.unit)}</td>
            <td class="num">${money(it.price)}${it.mrp > it.price ? `<br><small class="muted"><s>${money(it.mrp)}</s></small>` : ""}</td>
            <td class="num"><b>${money(it.subtotal)}</b></td></tr>`).join("")}</tbody>
        </table></div>
        <div class="summary mt-2" style="position:static">
          ${summaryHTML({ ...o, order_type: o.order_type, tax_enabled: o.tax > 0, tax_label: s.tax_label || "Tax", tax_inclusive: s.tax_inclusive === "1" })}
        </div>
      </div>
      <div class="card">
        <h3>${o.order_type === "pickup" ? "Store pickup" : "Delivery details"}</h3>
        <dl class="kv">
          <dt>Name</dt><dd>${esc(ship.name)}</dd>
          <dt>Phone</dt><dd>${esc(ship.phone)}</dd>
          ${ship.email ? `<dt>Email</dt><dd>${esc(ship.email)}</dd>` : ""}
          ${o.order_type === "delivery" ? `<dt>Address</dt><dd>${esc([ship.address, ship.city, ship.state, ship.pincode].filter(Boolean).join(", "))}</dd>`
            : `<dt>Pickup from</dt><dd>${esc(s.address || "Our store")}</dd>`}
          <dt>Payment</dt><dd>${esc(PAYMENT_INFO[o.payment_method]?.[0] || o.payment_method)}</dd>
          ${o.note ? `<dt>Instructions</dt><dd>${esc(o.note)}</dd>` : ""}
        </dl>
        ${o.invoice_number ? `<h3 class="mt-3">Invoice ${esc(o.invoice_number)}</h3>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <a class="btn btn-outline btn-sm" href="${invoiceUrl(o)}" target="_blank" rel="noopener">${icon("receipt")} View</a>
            <a class="btn btn-outline btn-sm" href="${invoiceUrl(o)}${o.access_token ? "&" : "?"}print=1" target="_blank" rel="noopener">${icon("printer")} Print</a>
            <a class="btn btn-outline btn-sm" href="${invoiceUrl(o, true)}" download data-no-router>${icon("download")} Download PDF</a>
          </div>` : ""}
        <div class="mt-3" style="display:flex;gap:8px;flex-wrap:wrap">
          ${waNumber() ? `<a class="btn btn-whatsapp btn-sm" target="_blank" rel="noopener" href="${waLink(`Hello, I have a question about my order ${o.order_number}.`)}">${icon("whatsapp")} Ask about this order</a>` : ""}
          ${o.status === "pending" ? `<button class="btn btn-danger btn-sm" onclick="cancelMyOrder(${esc(JSON.stringify(o.order_number))}, ${esc(JSON.stringify(o.access_token || ""))})">Cancel order</button>` : ""}
        </div>
      </div>
    </div>
    <p class="mt-2"><a href="/products.html">${icon("chevronLeft")} Continue shopping</a></p>`;
}

async function cancelMyOrder(no, token) {
  if (!(await confirmDialog({ title: "Cancel this order?", text: "This can't be undone.", confirm: "Cancel order", cancel: "Keep order", danger: true }))) return;
  try {
    await api(`/orders/${encodeURIComponent(no)}/cancel`, { method: "POST", body: JSON.stringify({ token }) });
    toast("Order cancelled");
    initOrderPage();
  } catch (err) {
    toast(err.message, "error");
  }
}
