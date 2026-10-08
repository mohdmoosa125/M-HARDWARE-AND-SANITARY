/* ============================================================
   home.js — homepage sections (all product data from the API)
   ============================================================ */

async function initHome() {
  setMeta(null, "Quality hardware, sanitary, plumbing, tiles, tools and machines in Bhopal. Trusted products, expert guidance and reliable service.");
  renderTrustRow();
  await Promise.all([
    loadHomeCategories(),
    loadHeroCollage(),
    loadProductStrip("featuredProducts", "?featured=1&sort=featured&limit=8"),
    loadProductStrip("dealProducts", "?discount=1&sort=discount&limit=4"),
    loadProductStrip("latestProducts", "?sort=newest&limit=4"),
  ]);
}

function renderTrustRow() {
  const host = document.getElementById("trustRow");
  if (!host) return;
  const s = window.__settings;
  const items = [
    s.pickup_enabled !== "0" && ["store", "Store pickup", `Collect from our ${esc(s.city || "Bhopal")} store`],
    s.delivery_enabled !== "0" && ["truck", "Home delivery", "Delivery charges shown at checkout"],
    s.payment_cod_enabled !== "0" && ["shield", "Pay on delivery", "Cash / pay at store, no online payment needed"],
    ["sparkle", "Expert guidance", "Ask our AI assistant or call us"],
  ].filter(Boolean);
  host.innerHTML = items.map(([ico, title, text]) =>
    `<div><span class="t-ico">${icon(ico)}</span><span><b>${title}</b><small>${text}</small></span></div>`).join("");
}

async function loadHeroCollage() {
  const host = document.getElementById("heroCollage");
  if (!host) return;
  try {
    const items = ((await api("/products?featured=1&sort=featured&limit=12")).data || [])
      .sort((a, b) => (b.image_status === "ready") - (a.image_status === "ready"))
      .slice(0, 4);
    if (!items.length) {
      host.remove();
      return;
    }
    host.innerHTML = items.map((p) => {
      window.__productCache[p.id] = p;
      return `<a class="hero-tile" href="${productUrl(p)}">
        <img src="${imgSrc(p.image)}" alt="${esc(p.name)}" onerror="this.src=PLACEHOLDER">
        <div><b>${esc(p.name)}</b>${money(p.final_price)}</div></a>`;
    }).join("");
  } catch {
    host.remove();
  }
}

async function loadHomeCategories() {
  const host = document.getElementById("homeCategories");
  if (!host) return;
  host.innerHTML = Array.from({ length: 8 }, () =>
    `<div class="sk-card"><div class="skeleton" style="aspect-ratio:4/3;border-radius:0"></div><div class="sk-lines"><div class="skeleton sk-line w60"></div><div class="skeleton sk-line w80"></div></div></div>`).join("");
  try {
    const all = await loadCategoryTree();
    const featured = all.filter((c) => c.featured);
    const cats = (featured.length >= 4 ? featured : all).slice(0, 8);
    host.innerHTML = cats.length ? cats.map(categoryCardHTML).join("")
      : emptyState("box", "No categories yet", "Categories added by the store will appear here.");
  } catch {
    host.innerHTML = emptyState("info", "Unable to load categories", "Please refresh the page.");
  }
}

async function loadProductStrip(containerId, query) {
  const host = document.getElementById(containerId);
  if (!host) return;
  host.innerHTML = skeletonCards(4);
  try {
    const items = (await api("/products" + query)).data || [];
    if (!items.length) {
      host.closest("section")?.classList.add("hidden");
      return;
    }
    host.innerHTML = items.map(productCardHTML).join("");
  } catch {
    host.innerHTML = emptyState("info", "Unable to load products", "Please refresh the page.");
  }
}
