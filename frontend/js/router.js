/* ================================================================
   router.js — smooth SPA-like page transitions
   ----------------------------------------------------------------
   Instead of reloading the browser on every link click, this file:
     1. Intercepts clicks on internal links
     2. Fetches the target HTML in the background
     3. Extracts only <main id="app">…</main>
     4. Fades out the old content, fades in the new
     5. Re-runs that page's init function
   The nav, footer, CSS and JS files are never re-downloaded.
   ================================================================ */

/* ---------- map every page file to its init + title ---------- */
const ROUTES = {
  "index.html": { init: "initHome", title: "Home" },
  "products.html": { init: "initProductsPage", title: "Products" },
  "product-details.html": {
    init: "initProductDetails",
    title: "Product Details",
  },
  "categories.html": { init: "initCategoriesPage", title: "Categories" },
  "gallery.html": { init: "initGalleryPage", title: "Gallery" },
  "about.html": { init: null, title: "About Us" },
  "contact.html": { init: "initContactPage", title: "Contact Us" },
  "cart.html": { init: "initCartPage", title: "Your Cart" },
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ----------------------------------------------------------------
   Top progress bar — thin blue line that slides across while loading
   ---------------------------------------------------------------- */
function ensureProgressBar() {
  if (document.getElementById("navProgress")) return;
  const bar = document.createElement("div");
  bar.id = "navProgress";
  document.body.appendChild(bar);
}

function showProgress() {
  const bar = document.getElementById("navProgress");
  if (!bar) return;
  bar.style.transition = "none";
  bar.style.width = "0%";
  bar.style.opacity = "1";
  requestAnimationFrame(() => {
    bar.style.transition = "width .4s ease, opacity .4s ease";
    bar.style.width = "70%";
  });
}

function finishProgress() {
  const bar = document.getElementById("navProgress");
  if (!bar) return;
  bar.style.width = "100%";
  setTimeout(() => {
    bar.style.opacity = "0";
    setTimeout(() => {
      bar.style.width = "0%";
    }, 300);
  }, 150);
}

/* ----------------------------------------------------------------
   Swap the <main id="app"> content with a smooth fade
   ---------------------------------------------------------------- */
async function swapContent(newHtml, newPage) {
  const app = document.getElementById("app");
  if (!app) return;

  app.style.transition = "opacity .18s ease, transform .18s ease";
  app.style.opacity = "0";
  app.style.transform = "translateY(10px)";

  await sleep(180);

  app.innerHTML = newHtml;
  document.body.dataset.page = newPage;

  void app.offsetHeight;

  app.style.opacity = "1";
  app.style.transform = "translateY(0)";

  window.scrollTo({ top: 0, behavior: "instant" });
}

/* ----------------------------------------------------------------
   Main navigation function
   ---------------------------------------------------------------- */
async function navigateTo(href, pushState = true) {
  if (!href) return;
  const [pathOnly] = href.split("?");
  const path = pathOnly || "index.html";
  const route = ROUTES[path] || ROUTES["index.html"];

  showProgress();

  try {
    const res = await fetch(href, { cache: "no-store" });
    if (!res.ok) throw new Error("Page not found: " + href);
    const html = await res.text();

    const parsed = new DOMParser().parseFromString(html, "text/html");
    const newMain = parsed.getElementById("app");
    const content = newMain ? newMain.innerHTML : parsed.body.innerHTML;
    const newPage = parsed.body.dataset.page || "home";

    await swapContent(content, newPage);

    document.title = parsed.title || route.title;

    if (pushState) {
      history.pushState({ href }, "", href);
    }

    if (route.init && typeof window[route.init] === "function") {
      requestAnimationFrame(() => {
        try {
          window[route.init]();
        } catch (err) {
          console.error("Init failed for", route.init, err);
        }
      });
    }

    if (typeof renderNav === "function") renderNav();
    if (typeof renderFooter === "function") renderFooter();
    if (typeof applyWhatsappLinks === "function") applyWhatsappLinks();
    if (typeof updateCartCount === "function") updateCartCount();
  } catch (err) {
    console.error(err);
    const app = document.getElementById("app");
    if (app)
      app.innerHTML = `<p class="empty">Unable to load page. Please try again.</p>`;
  } finally {
    finishProgress();
  }
}

/* ----------------------------------------------------------------
   Intercept all internal link clicks
   ---------------------------------------------------------------- */
document.addEventListener("click", (e) => {
  const link = e.target.closest("a");
  if (!link) return;
  if (link.target === "_blank") return;
  if (link.hasAttribute("download")) return;

  const href = link.getAttribute("href");
  if (!href) return;

  if (/^(https?:|mailto:|tel:|#|javascript:)/i.test(href)) return;
  if (!/\.html(\?|$)/.test(href)) return;

  e.preventDefault();
  navigateTo(href, true);
});

/* ----------------------------------------------------------------
   Browser back / forward
   ---------------------------------------------------------------- */
window.addEventListener("popstate", (e) => {
  const href =
    (e.state && e.state.href) ||
    location.pathname.split("/").pop() + location.search ||
    "index.html";
  navigateTo(href, false);
});

/* ----------------------------------------------------------------
   Make sure the progress bar element exists on first load
   ---------------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", ensureProgressBar);
