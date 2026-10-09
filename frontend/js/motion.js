/* ============================================================
   motion.js — "Workshop Bold · In Motion" animation layer
   ------------------------------------------------------------
   Pure enhancement: the site works the same without it.
   · intro: hero headline word-by-word reveal
   · scroll reveal for sections/cards (works on content rendered later)
   · hero particle field + parallax on the hero tiles
   · count-up stats, card tilt, magnetic CTAs, click ripple
   · desktop-only cursor ring that grows on interactive elements
   Everything is skipped when the visitor prefers reduced motion.
   ============================================================ */

(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  document.documentElement.classList.toggle("motion-ok", !reduce);
  if (reduce) return;

  /* ---------- scroll reveal ---------- */
  const REVEAL = ".section-head, .category-card, .product-card, .steps li, .feature, .trust-row > div, " +
                 ".ai-promo, .cta-band, .masonry figure, .page-hero h1, .card, .stat";
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      e.target.classList.add("in");
      io.unobserve(e.target);
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

  function tagReveal(root = document) {
    root.querySelectorAll(REVEAL).forEach((el) => {
      if (el.dataset.rv) return;
      el.dataset.rv = "1";
      const sib = el.parentElement ? [...el.parentElement.children].indexOf(el) : 0;
      el.style.setProperty("--rv-delay", `${Math.min(sib, 7) * 70}ms`);
      el.classList.add("rv");
      io.observe(el);
    });
  }

  /* ---------- hero headline: word-by-word intro ---------- */
  function splitHeadline() {
    const h = document.querySelector(".hero h1");
    if (!h || h.dataset.split) return;
    h.dataset.split = "1";
    h.setAttribute("aria-label", h.textContent.replace(/\s+/g, " ").trim());
    let i = 0;
    const wrap = (node) => {
      [...node.childNodes].forEach((n) => {
        if (n.nodeType === 3) {
          const frag = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach((w) => {
            if (!w) return;
            if (/^\s+$/.test(w)) { frag.append(w); return; }
            const s = document.createElement("span");
            s.className = "w";
            s.setAttribute("aria-hidden", "true");
            s.style.setProperty("--i", i++);
            s.textContent = w;
            frag.append(s);
          });
          n.replaceWith(frag);
        } else if (n.nodeType === 1) wrap(n);
      });
    };
    wrap(h);
    requestAnimationFrame(() => h.classList.add("split-in"));
  }

  /* ---------- hero particles (canvas, paused off-screen) ---------- */
  function heroParticles() {
    const hero = document.querySelector(".hero");
    if (!hero || hero.querySelector(".hero-fx")) return;
    const c = document.createElement("canvas");
    c.className = "hero-fx";
    c.setAttribute("aria-hidden", "true");
    hero.prepend(c);
    const ctx = c.getContext("2d");
    let w, h, dots, raf, visible = true;
    const resize = () => {
      const r = hero.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1);
      w = r.width; h = r.height;
      c.width = w * dpr; c.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const n = Math.round(Math.min(60, w / 22));
      dots = Array.from({ length: n }, () => ({
        x: Math.random() * w, y: Math.random() * h, r: Math.random() * 1.8 + .6,
        vx: (Math.random() - .5) * .25, vy: -(Math.random() * .35 + .08), o: Math.random() * .5 + .2,
        hot: Math.random() < .22,
      }));
    };
    let last = 0;
    const tick = (t) => {
      raf = visible ? requestAnimationFrame(tick) : 0;
      if (t - last < 33) return;              // ~30fps is plenty for slow drift
      last = t;
      ctx.clearRect(0, 0, w, h);
      for (const hot of [false, true]) {      // two batched paths instead of one per dot
        ctx.beginPath();
        for (const d of dots) {
          if (d.hot !== hot) continue;
          d.x += d.vx * 2; d.y += d.vy * 2;
          if (d.y < -6) { d.y = h + 6; d.x = Math.random() * w; }
          if (d.x < -6) d.x = w + 6; else if (d.x > w + 6) d.x = -6;
          ctx.moveTo(d.x + d.r, d.y);
          ctx.arc(d.x, d.y, d.r, 0, 6.283);
        }
        ctx.fillStyle = hot ? "rgba(255,107,26,.55)" : "rgba(147,180,255,.45)";
        ctx.fill();
      }
    };
    new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      if (visible && !raf) raf = requestAnimationFrame(tick);
    }).observe(hero);
    addEventListener("resize", resize, { passive: true });
    resize();
    raf = requestAnimationFrame(tick);
  }

  /* ---------- parallax: hero copy drifts slower than the tiles ---------- */
  let parallaxBound = false;
  function parallax() {
    if (parallaxBound) return;
    parallaxBound = true;
    let ticking = false;
    addEventListener("scroll", () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        ticking = false;
        const y = scrollY;
        const hero = document.querySelector(".hero");
        if (!hero || y > hero.offsetHeight) return;
        document.querySelectorAll(".hero-tile").forEach((t, i) =>
          t.style.setProperty("--py", `${-y * (0.06 + (i % 2) * 0.05)}px`));
        hero.querySelector(".hero-grid > div")?.style.setProperty("transform", `translateY(${y * 0.12}px)`);
      });
    }, { passive: true });
  }

  /* ---------- count-up numbers ---------- */
  function countUps(root = document) {
    root.querySelectorAll("[data-count]:not([data-counted])").forEach((el) => {
      el.dataset.counted = "1";
      const target = Number(el.dataset.count) || 0;
      new IntersectionObserver(([e], obs) => {
        if (!e.isIntersecting) return;
        obs.disconnect();
        const t0 = performance.now(), dur = 1300;
        const step = (t) => {
          const p = Math.min(1, (t - t0) / dur), eased = 1 - Math.pow(1 - p, 3);
          el.textContent = Math.round(target * eased).toLocaleString("en-IN");
          if (p < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      }).observe(el);
    });
  }

  /* ---------- click ripple on every button ---------- */
  document.addEventListener("pointerdown", (e) => {
    const b = e.target.closest(".btn");
    if (!b) return;
    const r = b.getBoundingClientRect(), s = document.createElement("span");
    s.className = "ripple";
    s.style.left = `${e.clientX - r.left}px`;
    s.style.top = `${e.clientY - r.top}px`;
    b.appendChild(s);
    setTimeout(() => s.remove(), 600);
  });

  /* ---------- desktop-only: tilt, magnetic CTAs, cursor ring ---------- */
  if (finePointer) {
    document.addEventListener("pointermove", (e) => {
      const card = e.target.closest(".product-card, .category-card, .hero-tile");
      if (card) {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
        card.style.setProperty("--rx", `${(-y * 6).toFixed(2)}deg`);
        card.style.setProperty("--ry", `${(x * 6).toFixed(2)}deg`);
        card.classList.add("tilting");
      }
      const mag = e.target.closest(".hero .btn, .how-cta .btn, .cta-actions .btn");
      if (mag) {
        const r = mag.getBoundingClientRect();
        mag.style.setProperty("--mx", `${((e.clientX - r.left) / r.width - .5) * 10}px`);
        mag.style.setProperty("--my", `${((e.clientY - r.top) / r.height - .5) * 8}px`);
      }
    }, { passive: true });
    document.addEventListener("pointerout", (e) => {
      const card = e.target.closest(".product-card, .category-card, .hero-tile");
      if (card && !card.contains(e.relatedTarget)) {
        card.classList.remove("tilting");
        card.style.removeProperty("--rx"); card.style.removeProperty("--ry");
      }
      const mag = e.target.closest(".btn");
      if (mag && !mag.contains(e.relatedTarget)) { mag.style.removeProperty("--mx"); mag.style.removeProperty("--my"); }
    });

    const ring = document.createElement("div");
    ring.className = "cursor-ring";
    ring.setAttribute("aria-hidden", "true");
    document.body.appendChild(ring);
    let tx = -100, ty = -100, cx = -100, cy = -100;
    document.addEventListener("pointermove", (e) => {
      tx = e.clientX; ty = e.clientY;
      ring.classList.toggle("hot", !!e.target.closest("a, button, input, select, textarea, label, [role=button]"));
    }, { passive: true });
    document.addEventListener("pointerdown", () => ring.classList.add("press"));
    document.addEventListener("pointerup", () => ring.classList.remove("press"));
    document.documentElement.addEventListener("pointerleave", () => ring.classList.add("gone"));
    document.documentElement.addEventListener("pointerenter", () => ring.classList.remove("gone"));
    (function follow() {
      cx += (tx - cx) * .2; cy += (ty - cy) * .2;
      ring.style.transform = `translate(${cx}px, ${cy}px)`;
      requestAnimationFrame(follow);
    })();
  }

  /* ---------- boot + keep up with content rendered later / SPA navigation ---------- */
  function run() {
    splitHeadline();
    heroParticles();
    parallax();
    tagReveal();
    countUps();
  }
  let pending = false;
  new MutationObserver(() => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => { pending = false; run(); });
  }).observe(document.body, { childList: true, subtree: true });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
  else run();
  // Safety net: on a slow device, never leave intro content invisible.
  setTimeout(() => document.documentElement.classList.add("intro-done"), 3000);
})();
