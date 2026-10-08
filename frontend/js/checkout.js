/* ============================================================
   checkout.js — checkout page. Sends ONLY product ids + quantities
   and customer details; the server prices the order.
   ============================================================ */

const GUEST_ORDERS_KEY = "mh_orders_v1";
let checkoutState = { orderType: "delivery", quote: null, addresses: [] };

function rememberGuestOrder(order) {
  try {
    const list = JSON.parse(localStorage.getItem(GUEST_ORDERS_KEY)) || [];
    list.unshift({ no: order.order_number, t: order.access_token, at: order.created_at, total: order.grand_total });
    localStorage.setItem(GUEST_ORDERS_KEY, JSON.stringify(list.slice(0, 20)));
  } catch {}
}

function guestOrders() {
  try {
    return JSON.parse(localStorage.getItem(GUEST_ORDERS_KEY)) || [];
  } catch {
    return [];
  }
}

const PAYMENT_INFO = {
  cod: ["Cash on Delivery / Pay at Store", "Pay in cash or UPI when you receive or collect your order."],
  upi: ["UPI (manual)", "We confirm your order first, then you pay to our UPI ID. Payment is marked paid after we receive it."],
  online: ["Online payment", "Card / net banking."],
};

async function initCheckoutPage() {
  setMeta("Checkout");
  const host = document.getElementById("checkoutContent");
  if (!host) return;
  if (!getCart().length) {
    host.innerHTML = emptyState("cart", "Your cart is empty", "Add products to your cart before checking out.",
      `<a class="btn btn-primary" href="/products.html">Shop products</a>`);
    return;
  }
  host.innerHTML = `<p class="loading"><span class="spinner"></span>Preparing checkout…</p>`;

  try {
    checkoutState.quote = await quoteCart(checkoutState.orderType);
  } catch (err) {
    host.innerHTML = emptyState("info", "Unable to load checkout", err.message,
      `<button class="btn btn-primary" onclick="initCheckoutPage()">Try again</button>`);
    return;
  }
  const q = checkoutState.quote;
  if (!q.delivery_options.includes(checkoutState.orderType)) checkoutState.orderType = q.delivery_options[0] || "delivery";
  checkoutState.addresses = [];
  const me = window.__me;
  if (me) {
    try {
      checkoutState.addresses = (await api("/account/addresses")).data || [];
    } catch {}
  }
  const s = window.__settings;
  const def = checkoutState.addresses.find((a) => a.is_default) || checkoutState.addresses[0];

  host.innerHTML = `
    <form id="checkoutForm" class="checkout-layout" novalidate>
      <div>
        ${!me ? `<div class="alert alert-info">Have an account? <a href="/account.html?next=checkout">Log in</a> to see this order in your order history. You can also check out as a guest.</div>` : ""}
        <section class="card">
          <div class="step-title"><span class="n">1</span><h2>Contact details</h2></div>
          <div class="form-grid">
            <div class="field"><label for="coName">Full name *</label>
              <input id="coName" name="name" required minlength="2" autocomplete="name" value="${esc(me?.name || "")}"></div>
            <div class="field"><label for="coPhone">Mobile number *</label>
              <input id="coPhone" name="phone" type="tel" required inputmode="tel" pattern="[+0-9 ]{10,15}" autocomplete="tel" value="${esc(me?.phone || "")}" placeholder="10-digit mobile"></div>
            <div class="field span-2"><label for="coEmail">Email <span class="muted">(optional)</span></label>
              <input id="coEmail" name="email" type="email" autocomplete="email" value="${esc(me?.email || "")}"></div>
          </div>
        </section>

        <section class="card">
          <div class="step-title"><span class="n">2</span><h2>Delivery method</h2></div>
          <div class="choices">
            ${q.delivery_options.includes("delivery") ? `<label class="choice"><input type="radio" name="order_type" value="delivery">
              <span><b>Home delivery</b><small>${esc(s.delivery_note || "Delivered to your address.")}</small></span></label>` : ""}
            ${q.delivery_options.includes("pickup") ? `<label class="choice"><input type="radio" name="order_type" value="pickup">
              <span><b>Store pickup</b><small>Collect from our store${s.address ? ": " + esc(s.address) : ""}. Free.</small></span></label>` : ""}
          </div>
          <div id="addressBlock">
            ${checkoutState.addresses.length ? `<div class="saved-addr">${checkoutState.addresses.map((a) => `
              <label class="choice"><input type="radio" name="saved_addr" value="${a.id}" ${def && def.id === a.id ? "checked" : ""}>
                <span><b>${esc(a.label || "Address")}</b><small>${esc([a.address, a.city, a.state, a.pincode].filter(Boolean).join(", "))}</small></span></label>`).join("")}
              <label class="choice"><input type="radio" name="saved_addr" value="new" ${def ? "" : "checked"}><span><b>Use a new address</b></span></label>
            </div>` : ""}
            <div class="form-grid" id="addrFields">
              <div class="field span-2"><label for="coAddress">Address *</label>
                <textarea id="coAddress" name="address" rows="2" autocomplete="street-address" placeholder="House / shop no., street, area, landmark">${esc(def?.address || "")}</textarea></div>
              <div class="field"><label for="coCity">City *</label><input id="coCity" name="city" autocomplete="address-level2" value="${esc(def?.city || s.city || "")}"></div>
              <div class="field"><label for="coState">State</label><input id="coState" name="state" autocomplete="address-level1" value="${esc(def?.state || s.state || "")}"></div>
              <div class="field"><label for="coPin">PIN code *</label><input id="coPin" name="pincode" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="postal-code" value="${esc(def?.pincode || "")}"></div>
              ${me ? `<div class="field" style="justify-content:end"><label class="check"><input type="checkbox" id="coSaveAddr" ${checkoutState.addresses.length ? "" : "checked"}> Save this address</label></div>` : ""}
            </div>
          </div>
          <div class="field"><label for="coNote">Delivery instructions <span class="muted">(optional)</span></label>
            <textarea id="coNote" name="note" rows="2" placeholder="e.g. call before delivery, unload at site gate"></textarea></div>
        </section>

        <section class="card">
          <div class="step-title"><span class="n">3</span><h2>Payment</h2></div>
          <div class="choices">
            ${["cod", "upi", "online"].map((m) => {
              const on = q.payment_options.includes(m);
              if (!on && m === "upi") return "";
              return `<label class="choice ${on ? "" : "disabled"}"><input type="radio" name="payment_method" value="${m}" ${on ? "" : "disabled"} ${m === q.payment_options[0] ? "checked" : ""}>
                <span><b>${PAYMENT_INFO[m][0]}${on ? "" : " — coming soon"}</b><small>${on ? PAYMENT_INFO[m][1] : "Online payments are not available yet."}</small></span></label>`;
            }).join("")}
          </div>
          ${!q.payment_options.length ? `<div class="alert alert-error">No payment method is available right now. Please contact the store.</div>` : ""}
        </section>
      </div>

      <aside class="card summary" aria-label="Order summary">
        <h3>Order summary</h3>
        <div id="coLines"></div>
        <div id="coTotals"></div>
        <div id="coAlert" class="mt-1" role="alert"></div>
        <button class="btn btn-primary btn-block btn-lg mt-1" type="submit" id="placeOrderBtn">Place order ${icon("arrowRight")}</button>
        <p class="note">${q.payment_options.includes("online") ? "" : "No payment is taken online. "}Final prices are calculated by our server, and your invoice is generated as soon as the order is placed.</p>
        <a class="btn btn-ghost btn-block" href="/cart.html">${icon("chevronLeft")} Back to cart</a>
      </aside>
    </form>`;

  const form = document.getElementById("checkoutForm");
  form.querySelectorAll('input[name="order_type"]').forEach((r) => {
    r.checked = r.value === checkoutState.orderType;
    r.onchange = () => {
      checkoutState.orderType = r.value;
      refreshCheckoutSummary();
    };
  });
  form.querySelectorAll('input[name="saved_addr"]').forEach((r) => (r.onchange = fillSavedAddress));
  form.addEventListener("submit", placeOrder);
  renderCheckoutSummary();
  toggleAddressBlock();
}

function fillSavedAddress() {
  const sel = document.querySelector('input[name="saved_addr"]:checked');
  const a = checkoutState.addresses.find((x) => String(x.id) === sel?.value);
  const set = (id, v) => (document.getElementById(id).value = v || "");
  if (a) {
    set("coAddress", a.address);
    set("coCity", a.city);
    set("coState", a.state);
    set("coPin", a.pincode);
  } else {
    ["coAddress", "coPin"].forEach((id) => set(id, ""));
  }
}

function toggleAddressBlock() {
  document.getElementById("addressBlock")?.classList.toggle("hidden", checkoutState.orderType === "pickup");
}

async function refreshCheckoutSummary() {
  toggleAddressBlock();
  document.getElementById("coTotals").innerHTML = `<p class="loading"><span class="spinner"></span>Updating…</p>`;
  try {
    checkoutState.quote = await quoteCart(checkoutState.orderType);
  } catch (err) {
    document.getElementById("coAlert").innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
  }
  renderCheckoutSummary();
}

function renderCheckoutSummary() {
  const q = checkoutState.quote;
  document.getElementById("coLines").innerHTML = q.lines.map((l) => `
    <div class="mini-line"><img src="${imgSrc(l.image)}" alt="" onerror="this.src=PLACEHOLDER">
      <div><div class="ml-name">${esc(l.name)}</div><div class="ml-meta">${l.quantity} × ${money(l.price)} / ${esc(l.unit)}</div></div>
      <div class="ml-total">${money(l.subtotal)}</div></div>`).join("");
  document.getElementById("coTotals").innerHTML = `<hr style="border:0;border-top:1px solid var(--line);margin:10px 0">` + summaryHTML(q);
  const alertBox = document.getElementById("coAlert");
  alertBox.innerHTML = q.problems.length
    ? `<div class="alert alert-error">${q.problems.map((p) => esc(p.message)).join("<br>")} <a href="/cart.html">Update cart</a></div>` : "";
  document.getElementById("placeOrderBtn").disabled = !q.ok || !q.payment_options.length;
}

function checkoutErrors(data) {
  if (data.name.trim().length < 2) return ["coName", "Please enter your full name."];
  if (!/^\+?\d{10,13}$/.test(data.phone.replace(/[\s\-()]/g, ""))) return ["coPhone", "Please enter a valid 10-digit mobile number."];
  if (data.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(data.email)) return ["coEmail", "Please enter a valid email address."];
  if (data.order_type === "delivery") {
    if (data.address.trim().length < 5) return ["coAddress", "Please enter your delivery address."];
    if (!data.city.trim()) return ["coCity", "Please enter your city."];
    if (!/^\d{6}$/.test(data.pincode.trim())) return ["coPin", "Please enter a valid 6-digit PIN code."];
  }
  if (!data.payment_method) return [null, "Please choose a payment method."];
  return null;
}

async function placeOrder(e) {
  e.preventDefault();
  const form = e.target;
  const fd = Object.fromEntries(new FormData(form).entries());
  const data = {
    name: fd.name || "", phone: fd.phone || "", email: fd.email || "",
    address: fd.address || "", city: fd.city || "", state: fd.state || "", pincode: fd.pincode || "",
    note: fd.note || "", order_type: checkoutState.orderType, payment_method: fd.payment_method || "",
  };
  const alertBox = document.getElementById("coAlert");
  const problem = checkoutErrors(data);
  if (problem) {
    alertBox.innerHTML = `<div class="alert alert-error">${esc(problem[1])}</div>`;
    if (problem[0]) document.getElementById(problem[0])?.focus();
    return;
  }
  const btn = document.getElementById("placeOrderBtn");
  setButtonLoading(btn, true, "Placing order…");
  alertBox.innerHTML = "";
  try {
    const res = await api("/orders", {
      method: "POST",
      body: JSON.stringify({ ...data, items: getCart().map((i) => ({ product_id: i.id, quantity: i.quantity })) }),
    });
    const order = res.data;
    rememberGuestOrder(order);
    if (window.__me && data.order_type === "delivery" && document.getElementById("coSaveAddr")?.checked) {
      api("/account/addresses", { method: "POST", body: JSON.stringify({ ...data, label: "Home" }) }).catch(() => {});
    }
    saveCart([]);
    navigateTo(`/order.html?no=${encodeURIComponent(order.order_number)}&t=${encodeURIComponent(order.access_token)}&new=1`);
  } catch (err) {
    alertBox.innerHTML = `<div class="alert alert-error">${esc(err.message || "Order could not be created. Please try again.")}</div>`;
    setButtonLoading(btn, false);
    refreshCheckoutSummary();
  }
}
