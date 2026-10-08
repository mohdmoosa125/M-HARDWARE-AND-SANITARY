/* ================================================================
   gallery.js — logic for the Gallery page
   ================================================================ */

let galleryCategory = "";

async function initGalleryPage() {
  await buildGalleryFilters();
  await loadGallery();
}

async function buildGalleryFilters() {
  const host = document.getElementById("galleryFilters");
  if (!host) return;

  try {
    const res = await api("/gallery/categories");
    const cats = res.data || [];
    host.innerHTML =
      `<button class="chip active" onclick="setGalleryCat('')">All</button>` +
      cats
        .map(
          (c) =>
            `<button class="chip" onclick="setGalleryCat('${esc(c)}')">${esc(c)}</button>`,
        )
        .join("");
  } catch {
    host.innerHTML = "";
  }
}

function setGalleryCat(cat) {
  galleryCategory = cat;
  document.querySelectorAll("#galleryFilters .chip").forEach((b) => {
    const match = b.textContent.trim() === (cat || "All");
    b.classList.toggle("active", match);
  });
  loadGallery();
}

async function loadGallery() {
  const host = document.getElementById("galleryGrid");
  if (!host) return;

  host.innerHTML = `<p class="loading"><span class="spinner"></span>Loading gallery…</p>`;
  try {
    const url = galleryCategory
      ? `/gallery?category=${encodeURIComponent(galleryCategory)}`
      : "/gallery";
    const res = await api(url);
    const items = res.data || [];
    host.innerHTML = items.length
      ? items
          .map(
            (g) => `
          <img src="${imgSrc(g.image)}" alt="${esc(g.title || "")}"
               loading="lazy" onerror="this.src=PLACEHOLDER">`,
          )
          .join("")
      : `<p class="empty">No images in this category yet.</p>`;
  } catch {
    host.innerHTML = `<p class="empty">Unable to load gallery. Please try again.</p>`;
  }
}
