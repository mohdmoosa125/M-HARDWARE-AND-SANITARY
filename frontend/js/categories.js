/* ============================================================
   categories.js — category cards (home + categories page)
   ============================================================ */

/* Fallback one-liners when a category has no description in the admin */
const CATEGORY_BLURBS = {
  sanitary: "Wash basins, toilets, urinals, cisterns and bathroom accessories.",
  pipes: "PVC, CPVC and UPVC pipes for water supply and drainage.",
  fittings: "Elbows, tees, couplers, valves and brass fittings.",
  hardware: "Screws, hinges, locks, handles, bolts and fasteners.",
  tiles: "Floor, wall, bathroom, kitchen and designer tiles.",
  tools: "Hand tools, measuring tools and tool kits.",
  machines: "Drills, grinders, cutters, pumps and power tools.",
  "construction-materials": "Cement, adhesives, sealants and site accessories.",
  accessories: "Installation accessories and everyday hardware.",
};

function categoryCardHTML(cat) {
  const count = cat.product_count;
  const desc = cat.description || CATEGORY_BLURBS[cat.slug] || "";
  return `
    <a class="category-card" href="/products.html?category=${encodeURIComponent(cat.slug)}">
      <div class="cat-img"><img src="${imgSrc(cat.image)}" alt="" loading="lazy" decoding="async" onerror="this.src=PLACEHOLDER"></div>
      <div class="cat-body">
        <h3>${esc(cat.name)}</h3>
        ${desc ? `<p>${esc(desc)}</p>` : ""}
        <div class="cat-foot">
          <span>${count !== undefined ? `${count} product${count === 1 ? "" : "s"}` : ""}</span>
          <b>Explore ${icon("arrowRight")}</b>
        </div>
      </div>
    </a>`;
}

let __categoryTree = null;
async function loadCategoryTree() {
  if (!__categoryTree) {
    const res = await api("/categories?tree=1");
    __categoryTree = (res.data || []).filter((c) => c.is_active !== false);
  }
  return __categoryTree;
}

async function initCategoriesPage() {
  setMeta("All Categories", "Browse sanitary ware, pipes, fittings, hardware, tiles, tools and machines.");
  const host = document.getElementById("allCategories");
  if (!host) return;
  host.innerHTML = `<div class="category-grid">${Array.from({ length: 8 }, () =>
    `<div class="sk-card"><div class="skeleton" style="aspect-ratio:4/3;border-radius:0"></div><div class="sk-lines"><div class="skeleton sk-line w60"></div></div></div>`).join("")}</div>`;
  try {
    const cats = await loadCategoryTree();
    if (!cats.length) {
      host.innerHTML = emptyState("box", "No categories yet", "Categories added by the store will appear here.");
      return;
    }
    host.innerHTML = `<div class="category-grid">${cats.map(categoryCardHTML).join("")}</div>` +
      cats.filter((c) => c.children && c.children.length).map((cat) => `
        <div class="cat-block mt-3">
          <div class="section-head">
            <div><h2>${esc(cat.name)}</h2><p>${esc(cat.description || CATEGORY_BLURBS[cat.slug] || "")}</p></div>
            <a class="link-more" href="/products.html?category=${encodeURIComponent(cat.slug)}">View all ${icon("arrowRight")}</a>
          </div>
          <div class="chips">
            ${cat.children.filter((c) => c.is_active !== false).map((c) =>
              `<a class="chip" href="/products.html?category=${encodeURIComponent(c.slug)}">${esc(c.name)}</a>`).join("")}
          </div>
        </div>`).join("");
  } catch {
    host.innerHTML = emptyState("info", "Unable to load categories", "Please try again.",
      `<button class="btn btn-primary" onclick="initCategoriesPage()">Retry</button>`);
  }
}
