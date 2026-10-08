/* ============================================================
   cart.js — persistent cart (localStorage) + cart page
   The browser keeps only product ids and quantities (plus a name/
   image for display). Every price shown on the cart page comes from
   the server's /api/orders/quote — never from the browser.
   ============================================================ */

const CART_KEY = "mh_cart_v1";

function getCart() {
  try {
    const raw = JSON.parse(localStorage.getItem(CART_KEY)) || [];
    return raw.filter((i) => i && Number.isInteger(i.id) && i.quantity > 0);
  } catch {
    return [];
  }
}

function saveCart(cart) {
  try {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
  } catch {
    toast("Your browser blocked saving the cart. Please allow site storage.", "error");
  }
  updateCartCount();
}

function cartCount() {
  return getCart().reduce((sum, i) => sum + i.quantity, 0);
}

function updateCartCount() {
  const count = cartCount();
  document.querySelectorAll("[data-cart-count]").forEach((el) => {
    el.textContent = count > 99 ? "99+" : count;
    el.style.display = count ? "inline-flex" : "none";
  });
}

function addToCart(product, quantity = 1, { silent = false } = {}) {
  quantity = Math.max(1, parseInt(quantity, 10) || 1);
  if (!product.in_stock && product.in_stock !== undefined) {
    toast(`${product.name} is out of stock.`, "error");
    return false;
  }
  const cart = getCart();
  const existing = cart.find((i) => i.id === product.id);
  const already = existing ? existing.quantity : 0;
  const max = Number.isInteger(product.stock) ? product.stock : Infinity;
  if (already + quantity > max) {
    if (already >= max) {
      toast(`You already have all ${max} available in your cart.`, "error");
      return false;
    }
    quantity = max - already;
    toast(`Only ${max} available — added ${quantity}.`, "error");
  }
  if (existing) {
    existing.quantity += quantity;
  } else {
    cart.push({ id: product.id, quantity, name: product.name, image: product.image, unit: product.unit || "piece" });
  }
  saveCart(cart);
  if (!silent) toast(`${product.name} added to cart`, "success", { href: "/cart.html", label: "View cart" });
  return true;
}

async function getProduct(id) {
  if (window.__productCache[id]) return window.__productCache[id];
  const res = await api("/products/" + id);
  window.__productCache[id] = res.data;
  return res.data;
}

async function addToCartById(id, quantity = 1) {
  try {
    addToCart(await getProduct(id), quantity);
  } catch {
    toast("Unable to add item to cart. Please try again.", "error");
  }
}

async function buyNow(id, quantity = 1) {
  try {
    const p = await getProduct(id);
    const inCart = getCart().find((i) => i.id === id);
    if (inCart || addToCart(p, quantity, { silent: true })) navigateTo("/checkout.html");
  } catch {
    toast("Product unavailable. Please try again.", "error");
  }
}

function removeFromCart(id) {
  saveCart(getCart().filter((i) => i.id !== id));
  renderCartPage();
}

function setQuantity(id, qty, max) {
  qty = Math.max(1, parseInt(qty, 10) || 1);
  if (max && qty > max) {
    qty = max;
    toast(`Only ${max} available.`, "error");
  }
  const cart = getCart();
  const item = cart.find((i) => i.id === id);
  if (item) item.quantity = qty;
  saveCart(cart);
  renderCartPageDebounced();
}

async function clearCart() {
  if (!(await confirmDialog({ title: "Clear your cart?", text: "All items will be removed.", confirm: "Clear cart", danger: true }))) return;
  saveCart([]);
  renderCartPage();
}

/* ---------- server-priced quote ---------- */
async function quoteCart(orderType = "delivery") {
  const cart = getCart();
  if (!cart.length) return null;
  const res = await api("/orders/quote", {
    method: "POST",
    body: JSON.stringify({ items: cart.map((i) => ({ product_id: i.id, quantity: i.quantity })), order_type: orderType }),
  });
  return res.data;
}

function summaryHTML(q, { showDelivery = true } = {}) {
  return `
    <div class="row"><span>Subtotal (MRP)</span><span>${money(q.subtotal)}</span></div>
    ${q.discount ? `<div class="row"><span>Discount</span><span class="neg">− ${money(q.discount)}</span></div>` : ""}
    ${q.tax_enabled && q.tax ? `<div class="row"><span>${esc(q.tax_label)}${q.tax_inclusive ? " (included)" : ""}</span><span>${money(q.tax)}</span></div>` : ""}
    ${showDelivery ? `<div class="row"><span>${q.order_type === "pickup" ? "Store pickup" : "Delivery"}</span><span>${q.delivery_fee ? money(q.delivery_fee) : "Free"}</span></div>` : ""}
    <div class="row total"><span>Grand total</span><span>${money(q.grand_total)}</span></div>`;
}

/* ============================================================
   CART PAGE
   ============================================================ */
function initCartPage() {
  setMeta("Your Cart");
  renderCartPage();
}

const renderCartPageDebounced = debounce(() => renderCartPage(), 250);

async function renderCartPage() {
  const host = document.getElementById("cartContent");
  if (!host) return;
  const cart = getCart();
  updateCartCount();

  if (!cart.length) {
    host.innerHTML = emptyState("cart", "Your cart is empty", "Browse our catalog and add the products you need.",
      `<a class="btn btn-primary" href="/products.html">Shop products</a>`);
    return;
  }

  if (!host.querySelector(".cart-layout")) {
    host.innerHTML = `<div class="cart-layout"><div class="cart-lines">${skeletonCards(1)}</div><div class="card"><div class="skeleton sk-line w80"></div></div></div>`;
  }

  let q;
  try {
    q = await quoteCart();
  } catch (err) {
    host.innerHTML = emptyState("info", "Unable to load your cart", err.message,
      `<button class="btn btn-primary" onclick="renderCartPage()">Try again</button>`);
    return;
  }

  const problems = Object.fromEntries((q.problems || []).map((p) => [p.product_id, p.message]));
  const missing = cart.filter((i) => !q.lines.some((l) => l.product_id === i.id));

  host.innerHTML = `
    <div class="cart-layout">
      <div>
        <div class="cart-lines">
          <div class="cart-head"><span>${q.item_count} item${q.item_count === 1 ? "" : "s"}</span>
            <button class="btn btn-ghost btn-sm" onclick="clearCart()">${icon("trash")} Clear cart</button></div>
          ${q.lines.map((l) => `
            <div class="cart-line">
              <a href="${productUrl(l)}"><img src="${imgSrc(l.image)}" alt="${esc(l.name)}" loading="lazy" onerror="this.src=PLACEHOLDER"></a>
              <div class="cl-info">
                <a class="cl-name" href="${productUrl(l)}">${esc(l.name)}</a>
                <div class="cl-meta">${money(l.price)} / ${esc(l.unit)}${l.mrp > l.price ? ` · <s>${money(l.mrp)}</s>` : ""}${l.sku ? ` · SKU ${esc(l.sku)}` : ""}</div>
                ${problems[l.product_id] ? `<div class="cl-problem">${esc(problems[l.product_id])}</div>` : ""}
              </div>
              <div class="qty sm" role="group" aria-label="Quantity for ${esc(l.name)}">
                <button aria-label="Decrease" ${l.quantity <= 1 ? "disabled" : ""} onclick="setQuantity(${l.product_id}, ${l.quantity - 1})">${icon("minus")}</button>
                <input type="number" min="1" ${l.stock ? `max="${l.stock}"` : ""} value="${l.quantity}" aria-label="Quantity"
                       onchange="setQuantity(${l.product_id}, this.value, ${l.stock || 0})">
                <button aria-label="Increase" ${l.quantity >= l.stock ? "disabled" : ""} onclick="setQuantity(${l.product_id}, ${l.quantity + 1}, ${l.stock || 0})">${icon("plus")}</button>
              </div>
              <div class="cl-total">${money(l.subtotal)}</div>
              <button class="btn btn-ghost btn-icon cl-rm" aria-label="Remove ${esc(l.name)}" onclick="removeFromCart(${l.product_id})">${icon("trash")}</button>
            </div>`).join("")}
          ${missing.map((i) => `
            <div class="cart-line">
              <img src="${imgSrc(i.image)}" alt="" onerror="this.src=PLACEHOLDER">
              <div class="cl-info"><span class="cl-name">${esc(i.name || "Product")}</span>
                <div class="cl-problem">${esc(problems[i.id] || "This product is no longer available.")}</div></div>
              <span></span><span></span>
              <button class="btn btn-ghost btn-icon cl-rm" aria-label="Remove" onclick="removeFromCart(${i.id})">${icon("trash")}</button>
            </div>`).join("")}
        </div>
        <a class="btn btn-ghost mt-2" href="/products.html">${icon("chevronLeft")} Continue shopping</a>
      </div>

      <aside class="card summary" aria-label="Order summary">
        <h3>Order summary</h3>
        ${summaryHTML(q)}
        <p class="note">${q.delivery_options.includes("pickup") ? "Free store pickup available at checkout. " : ""}Prices are confirmed by our server at checkout.</p>
        ${q.problems.length ? `<div class="alert alert-error mt-1">Please fix the highlighted items before checkout.</div>` : ""}
        <a class="btn btn-primary btn-block btn-lg ${q.ok ? "" : "disabled"}" href="/checkout.html"
           ${q.ok ? "" : 'aria-disabled="true" onclick="return false"'}>Proceed to checkout ${icon("arrowRight")}</a>
        ${waNumber() ? `<button class="btn btn-whatsapp btn-block" onclick="sendCartOnWhatsapp()">${icon("whatsapp")} Send cart on WhatsApp</button>` : ""}
      </aside>
    </div>`;
}

async function sendCartOnWhatsapp() {
  try {
    const q = await quoteCart();
    if (!q) return;
    const me = window.__me;
    let text = `Hello ${window.__settings.business_name || ""}, I would like to order:\n\n`;
    if (me) text += `Customer: ${me.name}${me.phone ? " (" + me.phone + ")" : ""}\n\n`;
    q.lines.forEach((l, i) => {
      text += `${i + 1}. ${l.name}${l.sku ? " [" + l.sku + "]" : ""} — ${l.quantity} ${l.unit} × ${money(l.price)} = ${money(l.subtotal)}\n`;
    });
    text += `\n*Total: ${money(q.grand_total)}*\n\nPlease confirm availability.`;
    window.open(waLink(text), "_blank", "noopener");
  } catch (err) {
    toast(err.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", updateCartCount);
window.addEventListener("storage", (e) => e.key === CART_KEY && updateCartCount());
