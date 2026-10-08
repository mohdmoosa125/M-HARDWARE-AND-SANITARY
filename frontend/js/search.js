/* ============================================================
   search.js — global product search
   ============================================================ */

function goToSearch(event) {
  event.preventDefault();
  const input = document.getElementById("globalSearch");
  const q = input ? input.value.trim() : "";
  if (!q) return;
  window.location.href = "products.html?q=" + encodeURIComponent(q);
}
