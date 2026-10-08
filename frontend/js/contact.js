/* ================================================================
   contact.js — Contact + About pages (values come from settings)
   ================================================================ */

function initContactPage() {
  setMeta("Contact Us", "Call, WhatsApp or visit M Hardware & Sanitary in Bhopal.");
  const s = window.__settings || {};
  const host = document.getElementById("contactDetails");
  if (host) {
    const item = (ico, label, value) => (value ? `
      <div class="contact-item"><span class="c-ico">${icon(ico)}</span>
        <div><small>${label}</small>${value}</div></div>` : "");
    const mapsQuery = encodeURIComponent(`${s.business_name || ""} ${s.address || "Bhopal"}`);
    const directions = s.google_maps && /^https?:\/\//.test(s.google_maps)
      ? s.google_maps : `https://www.google.com/maps/search/?api=1&query=${mapsQuery}`;
    host.innerHTML = `
      <h2>${esc(s.business_name || "M Hardware & Sanitary")}</h2>
      ${flag("demo_mode") ? `<div class="alert alert-warn">Demo store: these contact details are placeholders until the owner updates them in Admin → Settings.</div>` : ""}
      ${item("pin", "Location", esc(s.address || "Bhopal, Madhya Pradesh"))}
      ${item("phone", "Phone", s.phone ? `<a href="${telLink()}">${esc(s.phone)}</a>` : "")}
      ${item("whatsapp", "WhatsApp", waNumber() ? `<a href="${waLink("Hello!")}" target="_blank" rel="noopener">+${esc(waNumber())}</a>` : "")}
      ${item("mail", "Email", s.email ? `<a href="mailto:${esc(s.email)}">${esc(s.email)}</a>` : "")}
      ${item("clock", "Business hours", esc(s.opening_hours || ""))}
      <div class="contact-actions">
        ${s.phone ? `<a class="btn btn-primary" href="${telLink()}">${icon("phone")} Call</a>` : ""}
        ${waNumber() ? `<a class="btn btn-whatsapp" href="${waLink("Hello, I have a question about your products.")}" target="_blank" rel="noopener">${icon("whatsapp")} WhatsApp</a>` : ""}
        <a class="btn btn-outline" href="${esc(directions)}" target="_blank" rel="noopener">${icon("pin")} Get directions</a>
        ${s.email ? `<a class="btn btn-outline" href="mailto:${esc(s.email)}">${icon("mail")} Email</a>` : ""}
      </div>
      <div class="map-box" id="cMap">${s.google_maps && s.google_maps.includes("/maps/embed")
        ? `<iframe src="${esc(s.google_maps)}" loading="lazy" referrerpolicy="no-referrer-when-downgrade" title="Store location map"></iframe>`
        : `<span>${icon("pin")} Map not configured yet.<br>The store can add a Google Maps embed link in Admin → Settings.</span>`}</div>`;
  }

  const form = document.getElementById("contactForm");
  if (form && !form._bound) {
    form._bound = true;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const box = document.getElementById("contactAlert");
      const btn = form.querySelector('button[type="submit"]');
      setButtonLoading(btn, true, "Sending…");
      try {
        const res = await api("/contact", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form).entries())) });
        box.innerHTML = `<div class="alert alert-success">${esc(res.message || "Message sent. We will get back to you soon.")}</div>`;
        form.reset();
      } catch (err) {
        box.innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
      } finally {
        setButtonLoading(btn, false);
      }
    });
  }
}

async function initAboutPage() {
  setMeta("About Us", "M Hardware & Sanitary — hardware, sanitary, plumbing and tiles in Bhopal.");
  const host = document.getElementById("aboutCategories");
  if (!host) return;
  try {
    const cats = await loadCategoryTree();
    host.innerHTML = cats.map((c) => `<a class="chip" href="/products.html?category=${encodeURIComponent(c.slug)}">${esc(c.name)}</a>`).join("");
  } catch {
    host.innerHTML = "";
  }
}
