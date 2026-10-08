/* ============================================================
   categories.js — renders category boxes on home & category pages
   ============================================================ */

function categoryBoxHTML(cat) {
  const count = cat.product_count !== undefined ? cat.product_count : "";
  return `
    <a class="category-box" href="products.html?category=${encodeURIComponent(cat.slug)}">
      <div class="cat-img">
        <img src="${imgSrc(cat.image)}" alt="${esc(cat.name)}" loading="lazy"
             onerror="this.src=PLACEHOLDER">
      </div>
      <div class="cat-body">
        <h3>${esc(cat.name)}</h3>
        ${count !== "" ? `<small>${count} product${count === 1 ? "" : "s"}</small>` : ""}
        <div class="cat-link">View Products →</div>
      </div>
    </a>`;
}

async function initHome() {
  const host = document.getElementById("homeCategories");
  if (host) {
    try {
      const res = await api("/categories?tree=1");
      const cats = (res.data || []).slice(0, 6);
      host.innerHTML = cats.length
        ? cats.map(categoryBoxHTML).join("")
        : `<p class="empty">No categories added yet.</p>`;
    } catch (err) {
      host.innerHTML = `<p class="empty">Unable to load categories. Please try again.</p>`;
    }
  }

  await loadProductStrip("dealProducts", "?discount=1&sort=discount&limit=4");
  await loadProductStrip("featuredProducts", "?featured=1&limit=4");
  await loadProductStrip("latestProducts", "?sort=newest&limit=4");
}

async function loadProductStrip(containerId, query) {
  const host = document.getElementById(containerId);
  if (!host) return;
  try {
    const res = await api("/products" + query);
    const items = res.data || [];
    items.forEach((p) => (window.__productCache[p.id] = p));
    host.innerHTML = items.length
      ? items.map(productCardHTML).join("")
      : `<p class="empty">No products found.</p>`;
  } catch (err) {
    host.innerHTML = `<p class="empty">Unable to load products. Please try again.</p>`;
  }
}

async function initCategoriesPage() {
  const host = document.getElementById("allCategories");
  if (!host) return;
  host.innerHTML = `<p class="loading"><span class="spinner"></span>Loading categories…</p>`;

  try {
    const res = await api("/categories?tree=1");
    const cats = res.data || [];
    if (!cats.length) {
      host.innerHTML = `<p class="empty">No categories available yet.</p>`;
      return;
    }

    host.innerHTML = cats
      .map(
        (cat) => `
      <div class="category-block mb-2">
        <div class="section-head">
          <h2>${esc(cat.name)}</h2>
          <a class="link-more" href="products.html?category=${encodeURIComponent(cat.slug)}">
            View all ${esc(cat.name)} →
          </a>
        </div>
        <div class="category-grid">
          ${
            cat.children && cat.children.length
              ? cat.children.map(categoryBoxHTML).join("")
              : categoryBoxHTML(cat)
          }
        </div>
      </div>
    `,
      )
      .join("");
  } catch (err) {
    host.innerHTML = `<p class="empty">Unable to load categories. Please try again.</p>`;
  }
}
