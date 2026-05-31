/* K3: Deck Builder — frontend interativo.
 *
 * Carrega catálogo de cartas do endpoint /api/rebirth/catalog (já existe)
 * ou via window.REBIRTH_CATALOG quando injetado pelo template (não está
 * agora; pegamos via API mesmo). Filtros aplicam em memória. Salva deck
 * via POST /api/rebirth/decks. Botão Ativar dispara POST /activate.
 */
(function () {
    const state = {
        catalog: [],
        filtered: [],
        filters: { element: "", rarity: "", cost: "", keyword: "" },
        currentDeck: {}, // { card_id: copies }
        deckName: "Meu Deck",
    };

    const els = {};
    const KEYWORD_LABELS = {
        RUSH: "Investida", BURST: "Detonação", LIFESTEAL: "Drenar",
        TAUNT: "Provocar", SHIELD: "Escudo", PIERCE: "Perfurar",
        REGEN: "Regenerar", EXECUTE: "Executar",
    };

    function csrfFetch(url, opts) {
        const headers = Object.assign({}, (opts && opts.headers) || {});
        headers["Content-Type"] = "application/json";
        headers["X-Rebirth-CSRF"] = window.REBIRTH_CSRF || "";
        return fetch(url, Object.assign({ credentials: "same-origin" }, opts, { headers }));
    }

    async function loadCatalog() {
        try {
            const r = await fetch("/api/rebirth/catalog", { credentials: "same-origin" });
            if (!r.ok) throw new Error("catalog fetch failed");
            const data = await r.json();
            state.catalog = data.catalog || data.cards || [];
        } catch (e) {
            console.error("[deck-builder] catalog load failed", e);
            state.catalog = [];
        }
    }

    function applyFilters() {
        const f = state.filters;
        state.filtered = state.catalog.filter(c => {
            if (f.element && c.element !== f.element) return false;
            if (f.rarity && c.rarity !== f.rarity) return false;
            if (f.cost) {
                const cost = Number(c.cost || 0);
                if (f.cost === "5") {
                    if (cost < 5) return false;
                } else if (cost !== Number(f.cost)) {
                    return false;
                }
            }
            if (f.keyword && !(c.keywords || []).includes(f.keyword)) return false;
            return true;
        });
    }

    function renderCatalog() {
        applyFilters();
        els.catalogCount.textContent = state.filtered.length;
        if (!state.filtered.length) {
            els.catalogGrid.innerHTML = '<p class="rb-deck-empty">Nenhuma carta corresponde aos filtros.</p>';
            return;
        }
        els.catalogGrid.innerHTML = state.filtered.map(c => {
            const copies = state.currentDeck[c.id] || 0;
            const kws = (c.keywords || []).map(k =>
                `<span class="rb-kw-tag rb-kw-${k.toLowerCase()}">${KEYWORD_LABELS[k] || k}</span>`
            ).join("");
            const cost = c.cost || 0;
            const atk = c.attack || 0;
            const grd = c.guard || 0;
            return `
                <button type="button" class="rb-deck-card" data-card-id="${c.id}"
                        ${copies >= 3 ? 'disabled' : ''}>
                    <header>
                        <b class="rb-deck-cost">${cost}</b>
                        <strong>${escapeHtml(c.name)}</strong>
                    </header>
                    <div class="rb-deck-card-meta">
                        <span>${escapeHtml(c.element || "—")} · ${escapeHtml((c.rarity || "").toLowerCase())}</span>
                        <span>${atk} ATK / ${grd} GRD</span>
                    </div>
                    <div class="rb-deck-card-kws">${kws}</div>
                    ${copies > 0 ? `<span class="rb-deck-copies-badge">x${copies}</span>` : ''}
                </button>
            `;
        }).join("");
    }

    function renderCurrentDeck() {
        const ids = Object.keys(state.currentDeck);
        const total = ids.reduce((s, id) => s + state.currentDeck[id], 0);
        els.deckSize.textContent = total;
        els.deckSize.parentElement.classList.toggle("is-full", total === 30);
        els.deckSize.parentElement.classList.toggle("is-invalid", total > 30);

        if (!ids.length) {
            els.deckList.innerHTML = '<p class="rb-deck-empty">Clique numa carta do catálogo pra adicionar.</p>';
            return;
        }
        // Ordena por custo, depois nome
        const enriched = ids.map(id => {
            const card = state.catalog.find(c => c.id === id);
            return { id, copies: state.currentDeck[id], card };
        }).filter(e => e.card)
          .sort((a, b) => (a.card.cost || 0) - (b.card.cost || 0) || a.card.name.localeCompare(b.card.name));

        els.deckList.innerHTML = enriched.map(e => `
            <div class="rb-deck-line" data-card-id="${e.id}">
                <b>${e.card.cost || 0}</b>
                <span>${escapeHtml(e.card.name)}</span>
                <span class="rb-deck-line-element">${escapeHtml(e.card.element || "")}</span>
                <span class="rb-deck-line-copies">x${e.copies}</span>
                <button type="button" class="rb-deck-line-remove" data-remove-id="${e.id}" aria-label="Remover">×</button>
            </div>
        `).join("");
    }

    function addCard(cardId) {
        const total = Object.values(state.currentDeck).reduce((a, b) => a + b, 0);
        if (total >= 30) {
            showResult("Deck cheio (30 cartas). Remova alguma antes de adicionar.", false);
            return;
        }
        const cur = state.currentDeck[cardId] || 0;
        if (cur >= 3) {
            showResult("Máximo 3 cópias por carta.", false);
            return;
        }
        state.currentDeck[cardId] = cur + 1;
        renderCatalog();
        renderCurrentDeck();
        showResult("");
    }

    function removeCard(cardId) {
        if (!state.currentDeck[cardId]) return;
        state.currentDeck[cardId] -= 1;
        if (state.currentDeck[cardId] <= 0) delete state.currentDeck[cardId];
        renderCatalog();
        renderCurrentDeck();
        showResult("");
    }

    function showResult(msg, ok = true) {
        if (!els.result) return;
        els.result.textContent = msg || "";
        els.result.style.color = ok ? "var(--rb-text)" : "var(--rb-red)";
    }

    async function saveDeck() {
        if (!window.REBIRTH_IS_AUTH) {
            showResult("Entre/cadastre pra salvar decks.", false);
            return;
        }
        const total = Object.values(state.currentDeck).reduce((a, b) => a + b, 0);
        if (total !== 30) {
            showResult(`Deck precisa ter 30 cartas (atual: ${total}).`, false);
            return;
        }
        const name = (els.nameInput.value || state.deckName).trim() || "Deck";
        try {
            const r = await csrfFetch("/api/rebirth/decks", {
                method: "POST",
                body: JSON.stringify({ name, cards: state.currentDeck }),
            });
            const data = await r.json();
            if (data && data.ok) {
                showResult(`Deck "${name}" salvo. Recarregando…`);
                setTimeout(() => window.location.reload(), 800);
            } else {
                showResult((data.error && data.error.message) || "Falha ao salvar.", false);
            }
        } catch (e) {
            showResult("Erro de rede ao salvar deck.", false);
        }
    }

    async function deleteDeck(deckId) {
        if (!confirm("Excluir esse deck?")) return;
        try {
            const r = await csrfFetch(`/api/rebirth/decks/${deckId}`, { method: "DELETE" });
            if (r.ok) window.location.reload();
        } catch (e) { /* silent */ }
    }

    async function activateDeck(deckId) {
        try {
            const r = await csrfFetch(`/api/rebirth/decks/${deckId}/activate`, { method: "POST" });
            if (r.ok) window.location.reload();
        } catch (e) { /* silent */ }
    }

    function loadDeckInto(deckId) {
        const d = (window.REBIRTH_DECKS_SAVED || []).find(x => x.id === deckId);
        if (!d) return;
        state.currentDeck = Object.assign({}, d.cards);
        state.deckName = d.name;
        els.nameInput.value = d.name;
        renderCatalog();
        renderCurrentDeck();
        showResult(`Deck "${d.name}" carregado na bancada.`);
    }

    function escapeHtml(s) {
        return String(s == null ? "" : s).replace(/[&<>"']/g, m => (
            { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]
        ));
    }

    function bind() {
        els.catalogGrid = document.querySelector("[data-catalog-grid]");
        els.catalogCount = document.querySelector("[data-catalog-count]");
        els.deckList = document.querySelector("[data-deck-list]");
        els.deckSize = document.querySelector("[data-deck-size]");
        els.nameInput = document.querySelector("[data-deck-name]");
        els.result = document.querySelector("[data-deck-result]");

        document.querySelectorAll("[data-filter]").forEach(sel => {
            sel.addEventListener("change", (e) => {
                state.filters[e.target.dataset.filter] = e.target.value;
                renderCatalog();
            });
        });
        if (els.catalogGrid) {
            els.catalogGrid.addEventListener("click", (e) => {
                const btn = e.target.closest("[data-card-id]");
                if (btn && !btn.disabled) addCard(btn.dataset.cardId);
            });
        }
        if (els.deckList) {
            els.deckList.addEventListener("click", (e) => {
                const rm = e.target.closest("[data-remove-id]");
                if (rm) removeCard(rm.dataset.removeId);
            });
        }
        document.querySelector("[data-deck-save]").addEventListener("click", saveDeck);
        document.querySelector("[data-deck-clear]").addEventListener("click", () => {
            state.currentDeck = {};
            renderCatalog();
            renderCurrentDeck();
            showResult("Bancada limpa.");
        });
        document.querySelectorAll("[data-deck-delete]").forEach(b =>
            b.addEventListener("click", () => deleteDeck(Number(b.dataset.deckDelete)))
        );
        document.querySelectorAll("[data-deck-activate]").forEach(b =>
            b.addEventListener("click", () => activateDeck(Number(b.dataset.deckActivate)))
        );
        document.querySelectorAll("[data-deck-load]").forEach(b =>
            b.addEventListener("click", () => loadDeckInto(Number(b.dataset.deckLoad)))
        );
    }

    async function init() {
        bind();
        await loadCatalog();
        renderCatalog();
        renderCurrentDeck();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
