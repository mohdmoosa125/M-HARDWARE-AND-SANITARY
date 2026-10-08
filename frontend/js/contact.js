/* ================================================================
   contact.js — logic for the Contact page
   ================================================================ */

function initContactPage() {
  const s = window.__settings || {};

  const addr = document.getElementById("cAddress");
  if (addr) addr.textContent = "📍 " + (s.address || "");

  const hrs = document.getElementById("cHours");
  if (hrs) hrs.textContent = s.opening_hours || "";

  const phone = document.getElementById("cPhone");
  if (phone) {
    phone.textContent = s.phone || "";
    phone.href = "tel:" + (s.phone || "");
  }

  const wa = document.getElementById("cWhatsapp");
  if (wa) {
    wa.href = "https://wa.me/" + (s.whatsapp || "");
    wa.target = "_blank";
  }

  const mail = document.getElementById("cEmail");
  if (mail) {
    mail.textContent = s.email || "";
    mail.href = "mailto:" + (s.email || "");
  }

  const map = document.getElementById("cMap");
  if (map && s.google_maps) {
    map.innerHTML = `
      <a class="btn btn-outline btn-block" target="_blank" rel="noopener" href="${s.google_maps}">
        📍 Open in Google Maps
      </a>`;
  }

  const form = document.getElementById("contactForm");
  if (form && !form._bound) {
    form._bound = true;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const box = document.getElementById("contactAlert");
      const payload = Object.fromEntries(new FormData(form).entries());
      try {
        const res = await api("/contact", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        box.innerHTML = `<div class="alert alert-success">${esc(res.message)}</div>`;
        form.reset();
      } catch (err) {
        box.innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
      }
    });
  }
}
