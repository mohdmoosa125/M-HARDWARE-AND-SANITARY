/* ================================================================
   ai-assistant.js — floating AI shopping assistant / agent
   ----------------------------------------------------------------
   Answers come from /api/ai/chat, which only uses real catalog data.
   When the assistant proposes an action (e.g. add 20 bags of cement
   to the cart) it is shown as a card with Confirm / No thanks — the
   cart only changes after the customer confirms. The assistant never
   places orders or takes payments.
   ================================================================ */

const AI_SUGGESTIONS = [
  "Which pipe is best for bathroom plumbing?",
  "I need a tap under ₹1000",
  "Which drill should I buy?",
  "How many tiles for a 10x12 ft room?",
  "What fittings do I need for a wash basin?",
];

const aiState = { open: false, lastProductIds: [], busy: false };

function initAIAssistant() {
  if (document.getElementById("aiFab")) return;
  const fab = document.createElement("button");
  fab.id = "aiFab";
  fab.className = "ai-fab";
  fab.setAttribute("aria-label", "Open AI shopping assistant");
  fab.setAttribute("aria-expanded", "false");
  fab.innerHTML = `${icon("sparkle")}<span class="ai-label">Ask AI</span>`;
  fab.title = "Drag to move · Shift+Arrow keys to move";
  fab.onclick = () => {
    if (aiDrag.moved) { aiDrag.moved = false; return; }   // a drag is not a click
    aiState.open ? closeAI() : openAI();
  };
  document.body.appendChild(fab);
  makeFabMovable(fab);
}

/* ---------- movable launcher (mouse, touch, keyboard) ---------- */
const AI_POS_KEY = "aiFabPos";
const aiDrag = { active: false, moved: false, dx: 0, dy: 0, sx: 0, sy: 0 };

function placeFab(fab, x, y) {
  const m = 8;
  const maxX = window.innerWidth - fab.offsetWidth - m;
  const maxY = window.innerHeight - fab.offsetHeight - m;
  x = Math.min(Math.max(m, x), Math.max(m, maxX));
  y = Math.min(Math.max(m, y), Math.max(m, maxY));
  Object.assign(fab.style, { left: x + "px", top: y + "px", right: "auto", bottom: "auto" });
  positionAIPanel();
  return { x, y };
}

function saveFabPos(pos) {
  try { sessionStorage.setItem(AI_POS_KEY, JSON.stringify(pos)); } catch {}
}

function makeFabMovable(fab) {
  try {
    const saved = JSON.parse(sessionStorage.getItem(AI_POS_KEY) || "null");
    if (saved) requestAnimationFrame(() => placeFab(fab, saved.x, saved.y));
  } catch {}

  fab.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    const r = fab.getBoundingClientRect();
    Object.assign(aiDrag, { active: true, moved: false, dx: e.clientX - r.left, dy: e.clientY - r.top, sx: e.clientX, sy: e.clientY });
    fab.setPointerCapture(e.pointerId);
  });
  fab.addEventListener("pointermove", (e) => {
    if (!aiDrag.active) return;
    if (!aiDrag.moved && Math.hypot(e.clientX - aiDrag.sx, e.clientY - aiDrag.sy) < 6) return;
    aiDrag.moved = true;
    fab.classList.add("dragging");
    e.preventDefault();
    placeFab(fab, e.clientX - aiDrag.dx, e.clientY - aiDrag.dy);
  });
  const end = (e) => {
    if (!aiDrag.active) return;
    aiDrag.active = false;
    fab.classList.remove("dragging");
    if (fab.hasPointerCapture?.(e.pointerId)) fab.releasePointerCapture(e.pointerId);
    if (aiDrag.moved) saveFabPos({ x: fab.offsetLeft, y: fab.offsetTop });
  };
  fab.addEventListener("pointerup", end);
  fab.addEventListener("pointercancel", end);

  fab.addEventListener("keydown", (e) => {
    const step = { ArrowLeft: [-20, 0], ArrowRight: [20, 0], ArrowUp: [0, -20], ArrowDown: [0, 20] }[e.key];
    if (!step || !e.shiftKey) return;
    e.preventDefault();
    saveFabPos(placeFab(fab, fab.offsetLeft + step[0], fab.offsetTop + step[1]));
  });
  window.addEventListener("resize", () => {
    if (fab.style.left) placeFab(fab, fab.offsetLeft, fab.offsetTop);
  });
}

/* Keep the open chat panel next to the launcher (desktop/tablet only; phones use full screen). */
function positionAIPanel() {
  const panel = document.getElementById("aiPanel");
  const fab = document.getElementById("aiFab");
  if (!panel || !fab) return;
  if (window.innerWidth <= 640 || !fab.style.left) {
    Object.assign(panel.style, { left: "", top: "", right: "", bottom: "" });
    return;
  }
  const f = fab.getBoundingClientRect(), m = 8, gap = 10;
  const w = panel.offsetWidth || 400, h = panel.offsetHeight || 600;
  let x = f.right - w;
  if (x < m) x = f.left;
  x = Math.min(Math.max(m, x), window.innerWidth - w - m);
  let y = f.top - h - gap;
  if (y < m) y = f.bottom + gap;
  y = Math.min(Math.max(m, y), window.innerHeight - h - m);
  Object.assign(panel.style, { left: x + "px", top: y + "px", right: "auto", bottom: "auto" });
}

function buildAIPanel() {
  const panel = document.createElement("section");
  panel.id = "aiPanel";
  panel.className = "ai-panel";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", "AI shopping assistant");
  panel.innerHTML = `
    <div class="ai-head">
      <span class="ai-ava">${icon("sparkle")}</span>
      <div><b>Shopping assistant</b><small>Answers from our live catalog · never places orders</small></div>
      <button id="aiClose" aria-label="Close assistant">${icon("x")}</button>
    </div>
    <div class="ai-body" id="aiBody" aria-live="polite"></div>
    <div class="ai-suggest" id="aiSuggest">
      ${AI_SUGGESTIONS.map((q) => `<button type="button">${esc(q)}</button>`).join("")}
    </div>
    <form class="ai-form" id="aiForm">
      <label class="sr-only" for="aiInput">Message</label>
      <input id="aiInput" placeholder="e.g. basin under ₹5000, 20 bags of cement…" autocomplete="off" maxlength="500">
      <button type="submit" aria-label="Send">${icon("send")}</button>
    </form>
    <div class="ai-note">General guidance only — confirm technical choices with your plumber or engineer.</div>`;
  document.body.appendChild(panel);

  document.getElementById("aiClose").onclick = closeAI;
  document.getElementById("aiForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = document.getElementById("aiInput");
    const text = input.value.trim();
    if (text) {
      input.value = "";
      askAI(text);
    }
  });
  panel.querySelectorAll("#aiSuggest button").forEach((b) => (b.onclick = () => askAI(b.textContent)));
  panel.addEventListener("keydown", (e) => e.key === "Escape" && closeAI());

  addAIMessage("bot", "Hello! 👋 I can find products, compare them, check prices and stock, estimate tiles, and add items to your cart after you confirm. What do you need?");
  return panel;
}

function openAI(question) {
  initAIAssistant();
  let panel = document.getElementById("aiPanel");
  if (!panel) panel = buildAIPanel();
  panel.classList.remove("hidden");
  positionAIPanel();
  aiState.open = true;
  document.getElementById("aiFab")?.setAttribute("aria-expanded", "true");
  document.getElementById("aiInput").focus();
  if (question) askAI(question);
}

function closeAI() {
  document.getElementById("aiPanel")?.classList.add("hidden");
  aiState.open = false;
  const fab = document.getElementById("aiFab");
  fab?.setAttribute("aria-expanded", "false");
  fab?.focus();
}

async function askAI(text) {
  if (aiState.busy) return;
  aiState.busy = true;
  document.getElementById("aiSuggest")?.classList.add("hidden");
  addAIMessage("user", text);
  const typing = addAIMessage("bot", "", { typing: true });
  try {
    const res = await api("/ai/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, context: { product_ids: aiState.lastProductIds } }),
    });
    typing.remove();
    const d = res.data;
    if (d.products && d.products.length) aiState.lastProductIds = d.products.map((p) => p.id);
    addAIMessage("bot", d.reply, d);
  } catch (err) {
    typing.remove();
    addAIMessage("bot", "Sorry, I couldn't reach the store right now. Please try again, or contact us directly.");
  } finally {
    aiState.busy = false;
  }
}

function addAIMessage(role, text, data = {}) {
  const body = document.getElementById("aiBody");
  const div = document.createElement("div");
  div.className = `ai-msg ${role}`;
  if (data.typing) {
    div.innerHTML = `<span class="ai-typing" aria-label="Assistant is typing"><span></span><span></span><span></span></span>`;
  } else {
    div.textContent = text;
  }

  if (data.products && data.products.length) {
    const wrap = document.createElement("div");
    wrap.className = "ai-products";
    wrap.innerHTML = data.products.slice(0, 6).map((p) => {
      window.__productCache[p.id] = p;
      return `<a class="ai-prod" href="${productUrl(p)}">
        <img src="${imgSrc(p.image)}" alt="" loading="lazy" onerror="this.src=PLACEHOLDER">
        <span><span class="ap-name">${esc(p.name)}</span><br>
        <span class="ap-meta">${priceText(p)} / ${esc(p.unit || "piece")} · ${stockText(p)}</span></span></a>`;
    }).join("");
    div.appendChild(wrap);
  }

  if (data.comparison && data.comparison.rows) {
    const c = data.comparison;
    const box = document.createElement("div");
    box.className = "ai-compare";
    box.innerHTML = `<table><tr><th></th>${c.products.map((n) => `<th>${esc(n)}</th>`).join("")}</tr>
      ${c.rows.map((r) => `<tr><th>${esc(r.label)}</th>${r.values.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("")}</table>
      ${data.compare_ids ? `<a href="/compare.html?ids=${data.compare_ids.join(",")}" style="font-size:.8rem;font-weight:600">Open full comparison →</a>` : ""}`;
    div.appendChild(box);
  }

  if (data.action) div.appendChild(actionCard(data.action, data.products || []));

  body.appendChild(div);
  body.scrollTop = body.scrollHeight;
  return div;
}

function actionCard(action, products) {
  const card = document.createElement("div");
  card.className = "ai-action";
  if (action.type === "navigate") {
    card.innerHTML = `<div class="row"><a class="btn btn-primary btn-sm" href="${esc(action.url)}">${esc(action.label || "Open")}</a></div>`;
    return card;
  }
  if (action.type !== "add_to_cart") return card;
  card.innerHTML = `<p>${esc(action.label)}</p>
    <div class="row">
      <button class="btn btn-primary btn-sm" data-ok>Confirm — add to cart</button>
      <button class="btn btn-outline btn-sm" data-no>No thanks</button>
    </div>`;
  card.querySelector("[data-ok]").onclick = async () => {
    const btns = card.querySelectorAll("button");
    btns.forEach((b) => (b.disabled = true));
    try {
      const p = products.find((x) => x.id === action.product_id) || (await getProduct(action.product_id));
      if (addToCart(p, action.quantity)) {
        card.innerHTML = `<p>✓ Added ${action.quantity} × ${esc(action.name)} to your cart.</p>
          <div class="row"><a class="btn btn-primary btn-sm" href="/cart.html">View cart</a>
          <a class="btn btn-outline btn-sm" href="/checkout.html">Checkout</a></div>`;
      } else {
        btns.forEach((b) => (b.disabled = false));
      }
    } catch {
      card.innerHTML = `<p>Sorry, I couldn't add that item. Please try again from the product page.</p>`;
    }
  };
  card.querySelector("[data-no]").onclick = () => {
    card.innerHTML = `<p>No problem — nothing was added.</p>`;
  };
  return card;
}
