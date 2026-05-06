/* =========================================================
   Ambitionz Arena State Bridge V8
   Real state synchronization layer between game.js and Arena V7 UI.
   ========================================================= */

(function () {
    const isBattlePage = () => window.location.pathname === "/training" || window.location.pathname === "/arena";

    if (!isBattlePage()) return;

    const bridge = {
        latestState: null,
        latestPayload: null,
        hand: [],
        myField: {},
        enemyField: {},
        selectedIntent: "Strike",
        selectedCardId: null,
        diagnostics: {
            stateUpdates: 0,
            handRenders: 0,
            cardClicks: 0,
            lastError: null,
        },
    };

    function qs(selector) {
        return document.querySelector(selector);
    }

    function qsa(selector) {
        return Array.prototype.slice.call(document.querySelectorAll(selector));
    }

    function log() {
        try {
            console.debug("[ArenaStateBridge]", ...arguments);
        } catch (err) {}
    }

    function normalizeCard(raw, index) {
        if (!raw) return null;

        const card = Object.assign({}, raw);
        const id = card.id || card.card_id || card.slug || card.name || ("hand-" + index);
        const name = card.name || card.title || ("Card " + (index + 1));
        const type = card.type || card.card_type || "Monster";
        const cost = Number(card.cost ?? card.energy_cost ?? card.energy ?? 1);
        const power = Number(card.power ?? card.attack ?? card.value ?? 0);
        const element = card.element || "Neutral";
        const rarity = card.rarity || "Common";
        const sigil = card.sigil || "None";
        const role = card.role || "Balancer";
        const effect = card.effect || card.description || "";

        return {
            raw: raw,
            id: String(id),
            name: String(name),
            type: String(type),
            cost: Number.isFinite(cost) ? cost : 1,
            power: Number.isFinite(power) ? power : 0,
            element: String(element),
            rarity: String(rarity),
            sigil: String(sigil),
            role: String(role),
            effect: String(effect),
            index: index,
        };
    }

    function findDeepArrayByNames(obj, names) {
        if (!obj || typeof obj !== "object") return null;

        for (const name of names) {
            if (Array.isArray(obj[name])) return obj[name];
        }

        for (const key of Object.keys(obj)) {
            const value = obj[key];

            if (value && typeof value === "object") {
                const found = findDeepArrayByNames(value, names);
                if (found) return found;
            }
        }

        return null;
    }

    function findDeepObjectByNames(obj, names) {
        if (!obj || typeof obj !== "object") return null;

        for (const name of names) {
            if (obj[name] && typeof obj[name] === "object" && !Array.isArray(obj[name])) {
                return obj[name];
            }
        }

        for (const key of Object.keys(obj)) {
            const value = obj[key];

            if (value && typeof value === "object") {
                const found = findDeepObjectByNames(value, names);
                if (found) return found;
            }
        }

        return null;
    }

    function inferHandFromPayload(payload) {
        if (!payload) return [];

        const direct =
            payload.hand ||
            payload.my_hand ||
            payload.player_hand ||
            payload.cards_in_hand ||
            payload.current_hand;

        if (Array.isArray(direct)) return direct;

        const candidates = [
            "hand",
            "my_hand",
            "player_hand",
            "cards_in_hand",
            "current_hand",
        ];

        const found = findDeepArrayByNames(payload, candidates);
        return Array.isArray(found) ? found : [];
    }

    function inferPlayerState(payload) {
        if (!payload) return {};

        return (
            payload.me ||
            payload.player ||
            payload.current_player ||
            payload.my_state ||
            payload.p1 ||
            findDeepObjectByNames(payload, ["me", "player", "current_player", "my_state", "p1"]) ||
            {}
        );
    }

    function inferEnemyState(payload) {
        if (!payload) return {};

        return (
            payload.enemy ||
            payload.opponent ||
            payload.enemy_state ||
            payload.p2 ||
            findDeepObjectByNames(payload, ["enemy", "opponent", "enemy_state", "p2"]) ||
            {}
        );
    }

    function emitBridgeEvent(name, detail) {
        window.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
    }

    function updateFromState(payload) {
        bridge.latestPayload = payload;
        bridge.latestState = payload;
        bridge.diagnostics.stateUpdates += 1;

        const hand = inferHandFromPayload(payload).map(normalizeCard).filter(Boolean);
        bridge.hand = hand;

        const me = inferPlayerState(payload);
        const enemy = inferEnemyState(payload);

        bridge.myField = me.field || me.board || me.zones || {};
        bridge.enemyField = enemy.field || enemy.board || enemy.zones || {};

        renderStats(me, enemy, payload);
        renderHand(hand);
        renderField(me, enemy);
        updateStatusText(payload, hand);

        emitBridgeEvent("ambitionz:state_synced", {
            payload,
            hand,
            me,
            enemy,
            diagnostics: bridge.diagnostics,
        });

        log("state synced", {
            hand: hand.length,
            stateUpdates: bridge.diagnostics.stateUpdates,
        });
    }

    function compactHp(value) {
        const n = Number(String(value ?? "").replace(/\D/g, ""));

        if (!Number.isFinite(n)) return value || "36";
        if (n >= 100) return String(Math.round(n / 100));

        return String(n);
    }

    function setText(selector, value) {
        const el = qs(selector);
        if (!el) return;

        if (value !== undefined && value !== null && String(value).trim() !== "") {
            el.textContent = String(value);
        }
    }

    function renderStats(me, enemy, payload) {
        if (me) {
            setText("#az-v7-my-name", me.name || me.username || me.player_name);
            setText("#az-v7-my-hp", compactHp(me.hp ?? me.health));
            setText("#az-v7-my-energy", formatEnergy(me));
        }

        if (enemy) {
            setText("#az-v7-enemy-name", enemy.name || enemy.username || enemy.player_name || "Opponent");
            setText("#az-v7-enemy-hp", compactHp(enemy.hp ?? enemy.health));
            setText("#az-v7-enemy-energy", formatEnergy(enemy));
        }

        setText("#az-v7-phase", payload.phase || payload.turn_phase || payload.status || "Battle");
        setText("#az-v7-round", payload.round ? ("Round " + payload.round) : payload.round_label);
    }

    function formatEnergy(player) {
        if (!player) return null;

        const energy = player.energy ?? player.current_energy;
        const max = player.max_energy ?? player.energy_max;

        if (energy !== undefined && max !== undefined) return energy + "/" + max;
        if (energy !== undefined) return String(energy);

        return null;
    }

    function rarityClass(rarity) {
        return "rarity-" + String(rarity || "common").toLowerCase().replace(/\s+/g, "-");
    }

    function typeClass(type) {
        return "type-" + String(type || "monster").toLowerCase().replace(/\s+/g, "-");
    }

    function makeHandCard(card, index) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "az-v7-hand-card az-real-card " + rarityClass(card.rarity) + " " + typeClass(card.type);
        btn.dataset.cardId = card.id;
        btn.dataset.cardName = card.name;
        btn.dataset.cardType = card.type;
        btn.dataset.cardCost = String(card.cost);
        btn.style.setProperty("--rot", ((index - Math.min(2, bridge.hand.length / 2)) * 4) + "deg");
        btn.style.setProperty("--lift", Math.abs(index - 2) * 2 + "px");

        btn.innerHTML = [
            '<div class="cost">' + escapeHtml(card.cost) + '</div>',
            '<strong>' + escapeHtml(card.name) + '</strong>',
            '<span>' + escapeHtml(card.type) + ' · ' + escapeHtml(card.element) + '</span>',
            '<em>' + escapeHtml(card.sigil) + '</em>'
        ].join("");

        btn.addEventListener("click", function () {
            selectCard(card, btn);
        });

        return btn;
    }

    function renderHand(hand) {
        const handEl = qs("#az-v7-hand");
        if (!handEl) return;

        bridge.diagnostics.handRenders += 1;

        if (!hand || !hand.length) {
            handEl.innerHTML = '<div class="az-v7-hand-card az-empty-real-hand"><div class="cost">0</div><strong>No cards visible</strong><span>Start duel or wait for sync</span></div>';
            return;
        }

        handEl.innerHTML = "";

        hand.slice(0, 8).forEach(function (card, index) {
            handEl.appendChild(makeHandCard(card, index));
        });
    }

    function makeBoardCard(card, label) {
        const normalized = normalizeCard(card || {}, 0) || {
            name: label || "Empty",
            cost: 0,
            type: "Slot",
            power: 0,
            rarity: "Common",
        };

        const el = document.createElement("div");
        el.className = "az-v7-board-card az-real-board-card " + rarityClass(normalized.rarity) + " " + typeClass(normalized.type);
        el.innerHTML = [
            '<div class="cost">' + escapeHtml(normalized.cost || 0) + '</div>',
            '<strong>' + escapeHtml(normalized.name || label || "Empty") + '</strong>',
            '<div class="atk">' + escapeHtml(normalized.power || 0) + '</div>',
            '<div class="hp">' + escapeHtml(normalized.type === "Monster" ? (normalized.power || 0) : "·") + '</div>'
        ].join("");
        return el;
    }

    function extractZoneCard(player, names) {
        if (!player || typeof player !== "object") return null;

        for (const name of names) {
            if (player[name]) {
                if (Array.isArray(player[name])) return player[name][0] || null;
                return player[name];
            }
        }

        const field = player.field || player.board || player.zones;

        if (field && typeof field === "object") {
            for (const name of names) {
                if (field[name]) {
                    if (Array.isArray(field[name])) return field[name][0] || null;
                    return field[name];
                }
            }
        }

        return null;
    }

    function renderField(me, enemy) {
        const myLane = qs("#az-v7-your-lane");
        const enemyLane = qs("#az-v7-enemy-lane");

        if (myLane) {
            const monster = extractZoneCard(me, ["monster", "monster_zone", "active_monster", "creature"]);
            const spell = extractZoneCard(me, ["spell", "spell_zone", "trap", "trap_zone", "support"]);

            myLane.innerHTML = "";
            myLane.appendChild(makeBoardCard(monster, "Monster Slot"));
            myLane.appendChild(makeBoardCard(spell, "Tactic Slot"));
        }

        if (enemyLane) {
            const monster = extractZoneCard(enemy, ["monster", "monster_zone", "active_monster", "creature"]);
            const spell = extractZoneCard(enemy, ["spell", "spell_zone", "trap", "trap_zone", "support"]);

            enemyLane.innerHTML = "";
            enemyLane.appendChild(makeBoardCard(monster, "Hidden"));
            enemyLane.appendChild(makeBoardCard(spell, "Set Zone"));
        }
    }

    function updateStatusText(payload, hand) {
        const mode = qs(".az-v7-mode");

        if (mode) {
            if (!hand || !hand.length) {
                mode.textContent = "Waiting for hand";
            } else if (!bridge.selectedIntent) {
                mode.textContent = "Choose intent";
            } else {
                mode.textContent = bridge.selectedIntent + " ready";
            }
        }
    }

    function selectCard(card, btn) {
        bridge.selectedCardId = card.id;
        bridge.diagnostics.cardClicks += 1;

        qsa(".az-v7-hand-card").forEach(function (el) {
            el.classList.remove("is-selected-real-card");
        });

        btn.classList.add("is-selected-real-card");

        showHint("Selected " + card.name, card.type + " · Cost " + card.cost);

        const clickedOld = clickOriginalCard(card);

        if (!clickedOld) {
            bridge.diagnostics.lastError = "Could not find original card button for " + card.id;
            log("original card not found", card);
        }

        emitBridgeEvent("ambitionz:card_selected", {
            card,
            clickedOld,
            diagnostics: bridge.diagnostics,
        });
    }

    function clickOriginalCard(card) {
        const selectors = [
            '#my-hand [data-card-id="' + cssEscape(card.id) + '"]',
            '#my-hand button[data-card-id="' + cssEscape(card.id) + '"]',
            '#my-hand [data-card-name="' + cssEscape(card.name) + '"]',
        ];

        for (const selector of selectors) {
            const el = qs(selector);
            if (el) {
                el.click();
                return true;
            }
        }

        const oldButtons = qsa("#my-hand button, #my-hand [role='button'], #my-hand article, #my-hand .card");
        const byText = oldButtons.find(function (el) {
            return (el.textContent || "").toLowerCase().includes(card.name.toLowerCase());
        });

        if (byText) {
            byText.click();
            return true;
        }

        return false;
    }

    function showHint(title, copy) {
        if (window.AmbitionzArenaFeedback && window.AmbitionzArenaFeedback.showRoundBanner) {
            window.AmbitionzArenaFeedback.showRoundBanner(title, copy || "");
            return;
        }

        log(title, copy);
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function cssEscape(value) {
        if (window.CSS && window.CSS.escape) return window.CSS.escape(String(value));
        return String(value).replaceAll('"', '\\"');
    }

    function patchSocket() {
        const tryPatch = function () {
            if (!window.socket || !window.socket.on || window.socket.__azBridgePatched) return false;

            window.socket.__azBridgePatched = true;

            const originalOn = window.socket.on.bind(window.socket);

            window.socket.on = function (eventName, handler) {
                if (eventName === "game_state_update") {
                    const wrapped = function (payload) {
                        try {
                            updateFromState(payload);
                        } catch (err) {
                            bridge.diagnostics.lastError = String(err && err.message || err);
                            console.error("[ArenaStateBridge] failed to sync game_state_update", err);
                        }

                        return handler.apply(this, arguments);
                    };

                    return originalOn(eventName, wrapped);
                }

                return originalOn(eventName, handler);
            };

            window.socket.on("game_state_update", function (payload) {
                updateFromState(payload);
            });

            window.socket.on("arena_state_update", function (payload) {
                updateFromState(payload);
            });

            log("socket patched");
            return true;
        };

        let attempts = 0;

        const timer = setInterval(function () {
            attempts += 1;

            if (tryPatch() || attempts > 20) {
                clearInterval(timer);
            }
        }, 250);
    }

    function patchWindowHooks() {
        window.AmbitionzArenaStateBridge = {
            updateFromState,
            getState: function () {
                return bridge;
            },
            renderHand,
            renderField,
            diagnostics: bridge.diagnostics,
        };

        window.addEventListener("ambitionz:manual_state_update", function (event) {
            updateFromState(event.detail || {});
        });
    }

    function inferFromDomFallback() {
        const oldHand = qs("#my-hand");
        if (!oldHand) return;

        const oldCards = qsa("#my-hand button, #my-hand [data-card-id], #my-hand article, #my-hand .card");

        if (!oldCards.length) return;

        const cards = oldCards.map(function (el, index) {
            return normalizeCard({
                id: el.dataset.cardId || el.dataset.id || ("dom-" + index),
                name: (el.dataset.cardName || el.textContent || "Card").trim().replace(/\s+/g, " ").slice(0, 40),
                type: el.dataset.cardType || "Monster",
                cost: el.dataset.cardCost || el.dataset.cost || 1,
                element: el.dataset.element || "Neutral",
                rarity: el.dataset.rarity || "Common",
                sigil: el.dataset.sigil || "None",
            }, index);
        }).filter(Boolean);

        if (cards.length) {
            bridge.hand = cards;
            renderHand(cards);
            updateStatusText({}, cards);
            log("DOM fallback rendered", cards.length);
        }
    }

    function bindIntentState() {
        document.addEventListener("click", function (event) {
            const btn = event.target.closest("[data-v7-action]");
            if (!btn) return;

            const action = btn.dataset.v7Action;

            if (["strike", "guard", "focus"].includes(action)) {
                bridge.selectedIntent = action.charAt(0).toUpperCase() + action.slice(1);
                updateStatusText(bridge.latestPayload || {}, bridge.hand);
            }
        });
    }

    function boot() {
        patchWindowHooks();
        patchSocket();
        bindIntentState();

        setTimeout(inferFromDomFallback, 1200);
        setInterval(inferFromDomFallback, 1800);

        log("booted");
    }

    document.addEventListener("DOMContentLoaded", boot);
})();
