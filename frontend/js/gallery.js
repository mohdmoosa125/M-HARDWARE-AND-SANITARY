/* ================================================================
   gallery.js — masonry gallery with category chips + lightbox
   ================================================================ */

let galleryCategory = "";
let galleryItems = [];

async function initGalleryPage() {
  setMeta("Gallery", "Photos of our store, products and projects.");
  galleryCategory = new URLSearchParams(location.search).get("category") || "";
  await buildGalleryFilters();
  await loadGallery();
}

async function buildGalleryFilters() {
  const host = document.getElementById("galleryFilters");
  if (!host) return;
  try {
    const cats = (await api("/gallery/categories")).data || [];
    host.innerHTML = ["", ...cats].map((c) =>
      `<button class="chip ${c === galleryCategory ? "active" : ""}" data-cat="${esc(c)}" aria-pressed="${c === galleryCategory}">${esc(c || "All")}</button>`).join("");
    host.querySelectorAll("button").forEach((b) => (b.onclick = () => setGalleryCat(b.dataset.cat)));
  } catch {
    host.innerHTML = "";
  }
}

function setGalleryCat(cat) {
  galleryCategory = cat;
  document.querySelectorAll("#galleryFilters .chip").forEach((b) => {
    b.classList.toggle("active", b.dataset.cat === cat);
    b.setAttribute("aria-pressed", String(b.dataset.cat === cat));
  });
  loadGallery();
}

async function loadGallery() {
  const host = document.getElementById("galleryGrid");
  if (!host) return;
  host.innerHTML = Array.from({ length: 8 }, (_, i) =>
    `<figure><div class="skeleton" style="height:${180 + (i % 3) * 60}px;border-radius:0"></div></figure>`).join("");
  try {
    const url = galleryCategory ? `/gallery?category=${encodeURIComponent(galleryCategory)}` : "/gallery";
    galleryItems = (await api(url)).data || [];
    host.innerHTML = galleryItems.length
      ? galleryItems.map((g, i) => `
          <figure tabindex="0" role="button" aria-label="Open ${esc(g.title || "image")}" data-i="${i}">
            <img src="${imgSrc(g.image)}" alt="${esc(g.title || g.category || "Gallery image")}" loading="lazy" decoding="async" onerror="this.src=PLACEHOLDER">
            ${g.title ? `<figcaption>${esc(g.title)}</figcaption>` : ""}
          </figure>`).join("")
      : `<div style="column-span:all">${emptyState("grid", "No images here yet", "Try another category.")}</div>`;
    host.querySelectorAll("figure[data-i]").forEach((f) => {
      const open = () => openLightbox(+f.dataset.i, galleryItems.map((g) => g.image), galleryItems.map((g) => g.title || g.category || ""));
      f.onclick = open;
      f.onkeydown = (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), open());
    });
  } catch {
    host.innerHTML = `<div style="column-span:all">${emptyState("info", "Unable to load gallery", "Please try again.")}</div>`;
  }
}
