/* ================================================================
   router.js — smooth SPA-like page transitions
   ----------------------------------------------------------------
   Instead of reloading the browser on every link click, this file:
     1. Intercepts clicks on internal links (*.html and /products/<slug>)
     2. Fetches the target HTML in the background
     3. Extracts only <main id="app">…</main>
     4. Fades out the old content, fades in the new
     5. Re-runs that page's init function (PAGE_INITS in app.js)
   The header, footer, CSS and JS files are never re-downloaded.
   ================================================================ */

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ROUTABLE = /^\/?([\w-]+\.html|products\/[^/?#]+)(\?[^#]*)?(#.*)?$/;

/* ---------- top progress bar ---------- */
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
    setTimeout(() => (bar.style.width = "0%"), 300);
  }, 150);
}

/* ---------- swap <main id="app"> with a short fade ---------- */
async function swapContent(newHtml, newPage) {
  const app = document.getElementById("app");
  if (!app) return;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduce) {
    app.style.transition = "opacity .15s ease, transform .15s ease";
    app.style.opacity = "0";
    app.style.transform = "translateY(8px)";
    await sleep(150);
  }
  app.innerHTML = newHtml;
  document.body.dataset.page = newPage;
  void app.offsetHeight;
  app.style.opacity = "1";
  app.style.transform = "translateY(0)";
}

/* ---------- main navigation ---------- */
let navToken = 0;

async function navigateTo(href, pushState = true) {
  if (!href) return;
  const url = new URL(href, location.origin);
  const token = ++navToken;
  showProgress();
  try {
    const res = await fetch(url.pathname + url.search, { cache: "no-store" });
    if (!res.ok && res.status !== 404) throw new Error("Page not found");
    const html = await res.text();
    if (token !== navToken) return;            // a newer click won

    const parsed = new DOMParser().parseFromString(html, "text/html");
    const newMain = parsed.getElementById("app");
    if (!newMain) throw new Error("Bad page");
    const newPage = parsed.body.dataset.page || "home";

    if (pushState) history.pushState({ href: url.pathname + url.search + url.hash }, "", url.pathname + url.search + url.hash);
    await swapContent(newMain.innerHTML, newPage);

    document.title = parsed.title || document.title;
    const desc = parsed.querySelector('meta[name="description"]');
    if (desc) setMeta(null, desc.content);

    if (url.hash && document.querySelector(url.hash)) {
      document.querySelector(url.hash).scrollIntoView();
    } else {
      window.scrollTo({ top: 0, behavior: "instant" });
    }

    renderNav();
    renderFooter();
    applyWhatsappLinks();
    runPageInit(newPage);
    if (typeof renderCompareBar === "function") renderCompareBar();
    document.getElementById("app")?.focus({ preventScroll: true });
  } catch (err) {
    console.error(err);
    location.href = url.href;                  // fall back to a normal page load
  } finally {
    finishProgress();
  }
}

/* ---------- intercept internal link clicks ---------- */
document.addEventListener("click", (e) => {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  const link = e.target.closest("a");
  if (!link || link.target === "_blank" || link.hasAttribute("download") || link.dataset.noRouter !== undefined) return;
  const href = link.getAttribute("href");
  if (!href || /^(https?:|mailto:|tel:|#|javascript:)/i.test(href)) return;
  if (!ROUTABLE.test(href)) return;

  const target = new URL(href, location.origin);
  if (target.pathname === location.pathname && target.search === location.search && target.hash) return;
  e.preventDefault();
  navigateTo(href, true);
});

/* ---------- browser back / forward ---------- */
window.addEventListener("popstate", (e) => {
  const href = (e.state && e.state.href) || location.pathname + location.search;
  navigateTo(href, false);
});

document.addEventListener("DOMContentLoaded", () => {
  ensureProgressBar();
  history.replaceState({ href: location.pathname + location.search + location.hash }, "");
});
