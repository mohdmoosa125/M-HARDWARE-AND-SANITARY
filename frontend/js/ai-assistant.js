/* ================================================================
   ai-assistant.js — floating AI chat widget (Tailwind version)
   ================================================================ */

function initAIAssistant() {
  if (document.getElementById("aiFab")) return;

  const fab = document.createElement("button");
  fab.id = "aiFab";
  fab.title = "Ask AI";
  fab.textContent = "🤖";
  fab.className = [
    "fixed bottom-6 right-6 z-50",
    "w-16 h-16 rounded-full",
    "bg-gradient-to-br from-[#0f4c81] to-[#1c7bbd]",
    "text-white text-3xl flex items-center justify-center",
    "shadow-2xl shadow-[#0f4c81]/40",
    "hover:scale-110 active:scale-95 transition-transform duration-200",
    "cursor-pointer",
  ].join(" ");

  const win = document.createElement("div");
  win.id = "aiWindow";
  win.className = [
    "fixed bottom-24 right-6 z-40",
    "w-[380px] max-w-[calc(100vw-32px)]",
    "h-[540px] max-h-[calc(100vh-140px)]",
    "bg-white rounded-3xl overflow-hidden",
    "shadow-2xl border border-slate-200",
    "hidden flex-col",
  ].join(" ");

  win.innerHTML = `
    <div class="bg-gradient-to-r from-[#0f4c81] to-[#1c7bbd] text-white px-5 py-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-full bg-white/15 flex items-center justify-center text-xl">🤖</div>
        <div>
          <strong style="font-family:'Poppins',sans-serif" class="text-sm">Store Assistant</strong>
          <p class="text-[11px] opacity-80 flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block"></span>
            Online now
          </p>
        </div>
      </div>
      <button id="aiClose"
              class="w-8 h-8 rounded-full hover:bg-white/20 transition text-2xl leading-none flex items-center justify-center">
        ×
      </button>
    </div>

    <div id="aiBody" class="flex-1 overflow-y-auto p-4 bg-slate-50 space-y-3 scroll-smooth">
      <div class="bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-slate-700 max-w-[85%] shadow-sm leading-relaxed">
        Hello! 👋 I'm the M Hardware assistant.
        <br>Tell me what you're looking for — for example
        <span class="font-semibold text-[#0f4c81]">"1 inch CPVC pipe"</span>
        or <span class="font-semibold text-[#0f4c81]">"bathroom tiles"</span>.
      </div>
    </div>

    <form id="aiForm" class="flex gap-2 p-3 border-t border-slate-200 bg-white">
      <input id="aiInput" placeholder="Type your question…" autocomplete="off"
             class="flex-1 px-4 py-2.5 rounded-full border border-slate-200 bg-slate-50
                    text-sm text-slate-800 placeholder-slate-400
                    focus:outline-none focus:ring-2 focus:ring-[#0f4c81]/40 focus:bg-white
                    transition">
      <button type="submit" aria-label="Send"
              class="w-11 h-11 rounded-full bg-[#0f4c81] hover:bg-[#0a3559]
                     text-white flex items-center justify-center
                     transition active:scale-95 shadow-md">
        ➤
      </button>
    </form>
  `;

  document.body.appendChild(fab);
  document.body.appendChild(win);

  const body = document.getElementById("aiBody");
  const input = document.getElementById("aiInput");

  fab.addEventListener("click", () => {
    win.classList.toggle("hidden");
    win.classList.toggle("flex");
    if (!win.classList.contains("hidden")) input.focus();
  });
  document.getElementById("aiClose").addEventListener("click", () => {
    win.classList.add("hidden");
    win.classList.remove("flex");
  });

  document.getElementById("aiForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    addMessage("user", text);
    input.value = "";

    const typing = addMessage("bot", "", true);

    try {
      const res = await api("/ai/chat", {
        method: "POST",
        body: JSON.stringify({ message: text }),
      });
      typing.remove();
      addMessage("bot", res.data.reply, false, res.data.products);
    } catch (err) {
      typing.remove();
      addMessage(
        "bot",
        "Sorry, I couldn't reach the store right now. Please try again or contact us directly.",
      );
    }
  });

  function addMessage(role, text, isTyping = false, products = null) {
    const div = document.createElement("div");

    if (role === "user") {
      div.className = [
        "ml-auto max-w-[85%] px-4 py-2.5 rounded-2xl rounded-br-sm",
        "bg-[#0f4c81] text-white text-sm shadow-sm whitespace-pre-wrap",
      ].join(" ");
    } else {
      div.className = [
        "max-w-[85%] px-4 py-3 rounded-2xl rounded-bl-sm",
        "bg-white border border-slate-200 text-sm text-slate-700 shadow-sm whitespace-pre-wrap leading-relaxed",
      ].join(" ");
    }

    if (isTyping) {
      div.innerHTML = `
        <span class="inline-flex gap-1 items-center">
          <span class="w-2 h-2 rounded-full bg-slate-400 animate-bounce"></span>
          <span class="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style="animation-delay:.15s"></span>
          <span class="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style="animation-delay:.3s"></span>
        </span>`;
    } else {
      div.textContent = text;
    }

    if (products && products.length) {
      const wrap = document.createElement("div");
      wrap.className = "mt-3 space-y-2";

      products.forEach((p) => {
        window.__productCache[p.id] = p;
        const a = document.createElement("a");
        a.href = "product-details.html?id=" + p.id;
        a.className = [
          "flex gap-3 items-center p-2 rounded-xl",
          "bg-slate-50 hover:bg-[#0f4c81]/5",
          "border border-slate-200 hover:border-[#0f4c81]/30",
          "transition group",
        ].join(" ");
        a.innerHTML = `
          <img src="${imgSrc(p.image)}" onerror="this.src=PLACEHOLDER" alt=""
               class="w-12 h-12 object-cover rounded-lg bg-white flex-shrink-0">
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-slate-800 truncate group-hover:text-[#0f4c81]">
              ${esc(p.name)}
            </p>
            <p class="text-xs text-slate-500">
              ${money(p.final_price)} / ${esc(p.unit || "piece")}
            </p>
          </div>
          <span class="text-[#0f4c81] opacity-0 group-hover:opacity-100 transition">→</span>
        `;
        wrap.appendChild(a);
      });

      div.appendChild(wrap);
    }

    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
    return div;
  }
}
