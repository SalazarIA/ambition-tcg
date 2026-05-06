/* =========================================================
   Ambitionz Arena App V1
   Renders canonical `match_state` without DOM-reading overlays.
   Legacy engine remains loaded until replacement is stable.
   ========================================================= */

(function () {
    const isArenaRoute = () => window.location.pathname === "/training" || window.location.pathname === "/arena";

    if (!isArenaRoute()) return;

    const state = {
        socket: null,
        match: null,
        selectedIntent: null,
        selectedCardId: null,
        booted: false,
    };

    const $ = (selector) => document.querySelector(selector);

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function createAppShell() {
        if ($(".az-arena-app")) return;

        document.body.classList.add("az-arena-app-enabled");

        const app = document.createElement("main");
        app.className = "az-arena-app";
        app.innerHTML = [
            '<header class="az-arena-app-top az-arena-app-shell">',
            '  <div class="az-arena-app-title">',
            '    <span class="az-arena-app-kicker" id="az-mode">Arena</span>',
            '    <h1 id="az-title">Ambitionz</h1>',
            '  </div>',
            '  <div class="az-arena-app-phase" id="az-phase">Connecting</div>',
            '  <a class="az-arena-app-back" href="/">Back</a>',
            '</header>',

            '<section class="az-arena-app-message az-arena-app-shell" id="az-message">Waiting for match state...</section>',

            '<section class="az-arena-app-score">',
            '  <article class="az-arena-player az-arena-app-shell">',
            '    <div class="az-arena-player-head"><span>You</span><strong id="az-me-name">Player</strong></div>',
            '    <div class="az-arena-stat-row">',
            '      <div class="az-arena-stat">HP <strong id="az-me-hp">3600</strong></div>',
            '      <div class="az-arena-stat">EN <strong id="az-me-energy">0/0</strong></div>',
            '      <div class="az-arena-stat">AMB <strong id="az-me-ambition">0</strong></div>',
            '      <div class="az-arena-stat">Intent <strong id="az-me-intent">None</strong></div>',
            '    </div>',
            '  </article>',
            '  <article class="az-arena-round az-arena-app-shell">',
            '    <div><strong id="az-round">1</strong><span>Round</span></div>',
            '  </article>',
            '  <article class="az-arena-player az-arena-app-shell">',
            '    <div class="az-arena-player-head"><span>Enemy</span><strong id="az-enemy-name">Opponent</strong></div>',
            '    <div class="az-arena-stat-row">',
            '      <div class="az-arena-stat">HP <strong id="az-enemy-hp">3600</strong></div>',
            '      <div class="az-arena-stat">EN <strong id="az-enemy-energy">0/0</strong></div>',
            '      <div class="az-arena-stat">AMB <strong id="az-enemy-ambition">0</strong></div>',
            '      <div class="az-arena-stat">Hand <strong id="az-enemy-hand">0</strong></div>',
            '    </div>',
            '  </article>',
            '</section>',

            '<section class="az-arena-board az-arena-app-shell">',
            '  <div class="az-arena-field" id="az-enemy-field"></div>',
            '  <div class="az-arena-divider">Battlefield</div>',
            '  <div class="az-arena-field" id="az-me-field"></div>',
            '</section>',

            '<section class="az-arena-hand az-arena-app-shell">',
            '  <div class="az-arena-hand-head">',
            '    <h2>Your Hand</h2>',
            '    <span id="az-hand-count">0 cards</span>',
            '  </div>',
            '  <div class="az-arena-hand-row" id="az-hand"></div>',
            '</section>',

            '<nav class="az-arena-actions">',
            '  <button type="button" data-action="Strike">Strike</button>',
            '  <button type="button" data-action="Guard">Guard</button>',
            '  <button type="button" data-action="Focus">Focus</button>',
            '  <button type="button" class="primary" data-action="Ready">Ready</button>',
            '</nav>'
        ].join("");

        document.body.prepend(app);
    }

    function setText(selector, value) {
        const el = $(selector);
        if (el) el.textContent = String(value ?? "");
    }

    function renderCard(card, options = {}) {
        if (!card) {
            return '<div class="az-arena-slot az-arena-empty">' + escapeHtml(options.emptyLabel || "Empty") + '</div>';
        }

        const playable = options.playableCardIds && options.playableCardIds.includes(card.id);
        const playableClass = options.inHand
            ? playable ? "is-playable" : "is-unplayable"
            : "";

        return [
            '<button type="button" class="az-arena-card ' + playableClass + '" data-card-id="' + escapeHtml(card.id) + '" ' + (options.inHand ? "" : "disabled") + '>',
            '  <div class="az-arena-card-cost">' + escapeHtml(card.cost ?? 0) + '</div>',
            '  <strong>' + escapeHtml(card.name || "Card") + '</strong>',
            '  <span>' + escapeHtml(card.type || "Card") + ' · ' + escapeHtml(card.element || "Neutral") + '</span>',
            '</button>'
        ].join("");
    }

    function renderField(selector, field, enemy = false) {
        const el = $(selector);
        if (!el) return;

        field = field || {};

        el.innerHTML = [
            renderCard(field.monster, { emptyLabel: enemy ? "Enemy Monster" : "Monster Slot" }),
            renderCard(field.spell, { emptyLabel: enemy ? "Enemy Spell" : "Spell Slot" }),
            renderCard(field.trap, { emptyLabel: enemy ? "Enemy Trap" : "Trap Slot" }),
        ].join("");
    }

    function renderHand(match) {
        const handEl = $("#az-hand");
        const countEl = $("#az-hand-count");

        if (!handEl) return;

        const hand = (match.me && match.me.hand) || [];
        const playable = (match.legal_actions && match.legal_actions.playable_card_ids) || [];

        if (countEl) {
            countEl.textContent = hand.length + " cards";
        }

        if (!hand.length) {
            handEl.innerHTML = '<div class="az-arena-slot az-arena-empty">No cards in hand. Start the match or wait for sync.</div>';
            return;
        }

        handEl.innerHTML = hand.map((card) => renderCard(card, {
            inHand: true,
            playableCardIds: playable,
        })).join("");
    }

    function render(match) {
        if (!match || match.schema !== "ambitionz_match_v1") return;

        state.match = match;

        const me = match.me || {};
        const enemy = match.enemy || {};

        setText("#az-mode", match.mode || "Arena");
        setText("#az-title", window.location.pathname === "/training" ? "Training" : "Arena");
        setText("#az-phase", match.phase || "Battle");
        setText("#az-message", match.message || "Choose your move.");
        setText("#az-round", match.round || 1);

        setText("#az-me-name", me.name || "Player");
        setText("#az-me-hp", me.hp ?? 3600);
        setText("#az-me-energy", (me.energy ?? 0) + "/" + (me.max_energy ?? 0));
        setText("#az-me-ambition", me.ambition ?? 0);
        setText("#az-me-intent", me.intent || state.selectedIntent || "None");

        setText("#az-enemy-name", enemy.name || "Opponent");
        setText("#az-enemy-hp", enemy.hp ?? 3600);
        setText("#az-enemy-energy", (enemy.energy ?? 0) + "/" + (enemy.max_energy ?? 0));
        setText("#az-enemy-ambition", enemy.ambition ?? 0);
        setText("#az-enemy-hand", enemy.hand_count ?? 0);

        renderField("#az-enemy-field", enemy.field || {}, true);
        renderField("#az-me-field", me.field || {}, false);
        renderHand(match);

        updateActions();
    }

    function updateActions() {
        document.querySelectorAll(".az-arena-actions button").forEach((btn) => {
            btn.classList.remove("active");

            if (btn.dataset.action === state.selectedIntent) {
                btn.classList.add("active");
            }
        });
    }

    function emit(event, payload) {
        const socket = state.socket || window.socket;

        if (!socket || !socket.emit) {
            console.warn("[ArenaApp] socket unavailable", event, payload);
            setText("#az-message", "Socket not connected yet.");
            return;
        }

        socket.emit(event, payload || {});
    }

    function bindActions() {
        document.addEventListener("click", (event) => {
            const actionBtn = event.target.closest(".az-arena-actions button");

            if (actionBtn) {
                const action = actionBtn.dataset.action;

                if (["Strike", "Guard", "Focus"].includes(action)) {
                    state.selectedIntent = action;
                    updateActions();
                    emit("set_intent", { intent: action });
                    return;
                }

                if (action === "Ready") {
                    emit("declare_ready", {});
                    return;
                }
            }

            const cardBtn = event.target.closest("#az-hand .az-arena-card");

            if (cardBtn) {
                const cardId = cardBtn.dataset.cardId;

                if (cardBtn.classList.contains("is-unplayable")) {
                    setText("#az-message", "Not enough energy for this card.");
                    return;
                }

                state.selectedCardId = cardId;
                emit("play_card", { card_id: cardId });
            }
        });
    }

    function connectSocket() {
        const start = () => {
            const socket = window.socket;

            if (!socket || !socket.on || !socket.emit) {
                return false;
            }

            state.socket = socket;

            socket.on("match_state", (payload) => {
                console.debug("[ArenaApp] match_state", payload);
                render(payload);
            });

            socket.on("action_error", (payload) => {
                console.warn("[ArenaApp] action_error", payload);
                setText("#az-message", payload && payload.message ? payload.message : "Action failed.");
            });

            if (window.location.pathname === "/training") {
                socket.emit("start_training", {});
            }

            socket.emit("request_match_state", {});

            return true;
        };

        let tries = 0;
        const timer = setInterval(() => {
            tries += 1;

            if (start() || tries > 24) {
                clearInterval(timer);
            }
        }, 250);
    }

    function boot() {
        if (state.booted) return;

        state.booted = true;

        createAppShell();
        bindActions();
        connectSocket();

        setText("#az-message", "Connecting to match state...");
    }

    document.addEventListener("DOMContentLoaded", boot);

    window.AmbitionzArenaApp = {
        render,
        state,
        requestState: () => emit("request_match_state", {}),
    };
})();
