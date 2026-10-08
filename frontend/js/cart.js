/* ============================================================
   cart.js — localStorage shopping cart
   ============================================================ */

const CART_KEY = "mh_cart_v1";

function getCart() {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY)) || [];
  } catch {
    return [];
  }
}

function saveCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
  updateCartCount();
}

function updateCartCount() {
  const count = getCart().reduce((sum, i) => sum + i.quantity, 0);
  document.querySelectorAll("[data-cart-count]").forEach((el) => {
    el.textContent = count;
    el.style.display = count ? "inline-flex" : "none";
  });
}

function addToCartById(id) {
  const p = window.__productCache[id];
  if (!p) {
    alert("Product information is still loading. Please try again.");
    return;
  }
  addToCart(p);
}

function addToCart(product, quantity = 1) {
  const cart = getCart();
  const existing = cart.find((i) => i.id === product.id);

  if (existing) {
    existing.quantity += quantity;
  } else {
    cart.push({
      id: product.id,
      name: product.name,
      price: product.final_price,
      image: product.image,
      unit: product.unit || "piece",
      quantity,
    });
  }

  saveCart(cart);
  showToast(`${product.name} added to cart`);
}

function removeFromCart(id) {
  saveCart(getCart().filter((i) => i.id !== id));
  renderCartPage();
}

function setQuantity(id, qty) {
  qty = Math.max(1, parseInt(qty) || 1);
  const cart = getCart();
  const item = cart.find((i) => i.id === id);
  if (item) item.quantity = qty;
  saveCart(cart);
  renderCartPage();
}

function clearCart() {
  saveCart([]);
  renderCartPage();
}

function cartTotal() {
  return getCart().reduce((sum, i) => sum + i.price * i.quantity, 0);
}

function showToast(message) {
  let toast = document.getElementById("mhToast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "mhToast";
    toast.style.cssText = `
      position:fixed;left:50%;bottom:26px;transform:translateX(-50%) translateY(20px);
      background:#0f4c81;color:#fff;padding:11px 22px;border-radius:999px;
      font-size:.9rem;z-index:10000;opacity:0;transition:.3s;pointer-events:none;
      box-shadow:0 8px 24px rgba(15,76,129,.35);`;
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateX(-50%) translateY(0)";
  });
  clearTimeout(toast._t);
  toast._t = setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(-50%) translateY(20px)";
  }, 2200);
}

/* ============================================================
   CART PAGE
   ============================================================ */
function initCartPage() {
  renderCartPage();
  updateCartCount();
}

function renderCartPage() {
  const host = document.getElementById("cartContent");
  if (!host) return;

  const cart = getCart();

  if (!cart.length) {
    host.innerHTML = `
      <p class="empty">Your cart is empty.<br><br>
        <a class="btn btn-primary" href="products.html">Browse Products</a>
      </p>`;
    return;
  }

  host.innerHTML = `
    <table class="cart-table">
      <thead>
        <tr><th>Product</th><th>Price</th><th>Qty</th><th>Subtotal</th><th></th></tr>
      </thead>
      <tbody>
        ${cart
          .map(
            (i) => `
          <tr>
            <td data-label="Product">
              <div style="display:flex;align-items:center;gap:12px">
                <img class="cart-item-img" src="${imgSrc(i.image)}"
                     onerror="this.src=PLACEHOLDER" alt="">
                <div>
                  <a href="product-details.html?id=${i.id}"><b>${esc(i.name)}</b></a><br>
                  <small style="color:var(--muted)">per ${esc(i.unit)}</small>
                </div>
              </div>
            </td>
            <td data-label="Price">${money(i.price)}</td>
            <td data-label="Qty">
              <input class="qty-input" type="number" min="1" value="${i.quantity}"
                     onchange="setQuantity(${i.id}, this.value)">
            </td>
            <td data-label="Subtotal"><b>${money(i.price * i.quantity)}</b></td>
            <td><button class="btn btn-sm btn-outline" onclick="removeFromCart(${i.id})">✕</button></td>
          </tr>`,
          )
          .join("")}
      </tbody>
    </table>

    <div class="cart-summary">
      <div class="row"><span>Items</span><span>${cart.reduce((s, i) => s + i.quantity, 0)}</span></div>
      <div class="row total"><span>Total</span><span>${money(cartTotal())}</span></div>

      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:16px">
        <button class="btn btn-outline" onclick="clearCart()">Clear Cart</button>
        <button class="btn btn-accent" onclick="checkoutWhatsapp()">💬 Order on WhatsApp</button>
        <button class="btn btn-primary" onclick="checkoutOrder()">✅ Place Order</button>
      </div>
    </div>`;
}

function checkoutWhatsapp() {
  const cart = getCart();
  if (!cart.length) return;

  const number = (window.__settings.whatsapp || "").replace(/\D/g, "");
  let text = "Hello, I would like to order:\n\n";
  cart.forEach((i, idx) => {
    text += `${idx + 1}. ${i.name} — ${i.quantity} ${i.unit} × ${money(i.price)}\n`;
  });
  text += `\n*Total: ${money(cartTotal())}*\n\nPlease confirm availability.`;
  window.open(
    `https://wa.me/${number}?text=${encodeURIComponent(text)}`,
    "_blank",
  );
}

async function checkoutOrder() {
  const cart = getCart();
  if (!cart.length) return;

  const name = prompt("Your name:");
  if (!name) return;
  const phone = prompt("Your phone number:");
  if (!phone) return;
  const address = prompt("Delivery address (optional):") || "";

  try {
    const res = await api("/orders", {
      method: "POST",
      body: JSON.stringify({
        name,
        phone,
        address,
        items: cart.map((i) => ({ product_id: i.id, quantity: i.quantity })),
      }),
    });
    alert(res.message);
    clearCart();
  } catch (err) {
    alert("Could not place the order: " + err.message);
  }
}

document.addEventListener("DOMContentLoaded", updateCartCount);
