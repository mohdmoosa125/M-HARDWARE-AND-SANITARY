/* ============================================================
   search.js — global header search with live suggestions
   (name, SKU, brand, category, description, material)
   ============================================================ */

function goToSearch(q) {
  q = (q || "").trim();
  if (!q) return;
  hideSuggest();
  if (document.body.dataset.page === "products" && typeof loadProducts === "function") {
    productsState.filters.q = q;
    productsState.page = 1;
    loadProducts();
    return;
  }
  navigateTo("/products.html?q=" + encodeURIComponent(q));
}

function hideSuggest() {
  const box = document.getElementById("searchSuggest");
  if (box) {
    box.classList.add("hidden");
    box.innerHTML = "";
  }
  document.getElementById("globalSearch")?.setAttribute("aria-expanded", "false");
}

function initHeaderSearch() {
  const form = document.getElementById("globalSearchForm");
  const input = document.getElementById("globalSearch");
  const box = document.getElementById("searchSuggest");
  if (!form || !input || !box) return;
  let active = -1;
  let lastQ = "";

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const links = box.querySelectorAll("a");
    if (active >= 0 && links[active]) {
      links[active].click();
      return;
    }
    goToSearch(input.value);
  });

  const suggest = debounce(async () => {
    const q = input.value.trim();
    lastQ = q;
    if (q.length < 2) return hideSuggest();
    try {
      const res = await api(`/products?q=${encodeURIComponent(q)}&limit=6&sort=featured`);
      if (q !== lastQ) return;              // user kept typing
      const items = res.data || [];
      active = -1;
      box.innerHTML = items.length
        ? items.map((p) => {
            window.__productCache[p.id] = p;
            return `<a href="${productUrl(p)}" role="option">
              <img src="${imgSrc(p.image)}" alt="" loading="lazy" onerror="this.src=PLACEHOLDER">
              <span><span class="s-name">${esc(p.name)}</span>
              <span class="s-meta">${priceText(p)} · ${stockText(p)}${p.sku ? " · " + esc(p.sku) : ""}</span></span></a>`;
          }).join("") + `<a class="s-all" href="/products.html?q=${encodeURIComponent(q)}">See all results for “${esc(q)}”</a>`
        : `<div class="s-empty">No products match “${esc(q)}”. Try a simpler word like “tap” or “pipe”, or <a href="#" onclick="hideSuggest();openAI(${esc(JSON.stringify(q))});return false;">ask our AI assistant</a>.</div>`;
      box.classList.remove("hidden");
      input.setAttribute("aria-expanded", "true");
    } catch {
      hideSuggest();
    }
  }, 250);

  input.addEventListener("input", suggest);
  input.addEventListener("keydown", (e) => {
    const links = [...box.querySelectorAll("a")];
    if (!links.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      active = (active + (e.key === "ArrowDown" ? 1 : -1) + links.length) % links.length;
      links.forEach((a, i) => a.classList.toggle("active", i === active));
    } else if (e.key === "Escape") {
      hideSuggest();
    }
  });
  box.addEventListener("click", (e) => {
    if (e.target.closest("a")) setTimeout(hideSuggest, 0);
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".header-search")) hideSuggest();
  });
}
