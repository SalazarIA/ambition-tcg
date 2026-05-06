(function () {
    "use strict";

    let socket = null;
    let latestState = null;
    let hasCanonicalState = false;
    let bootTries = 0;

    const CANONICAL_SCHEMA = "ambitionz_arena_clean_v50";

    function $(id) {
        return document.getElementById(id);
    }

    function text(id, value) {
        const el = $(id);
        if (el) el.textContent = value;
    }

    function setMessage(value) {
        text("az48-message", value);
    }

    function arr(value) {
        return Array.isArray(value) ? value : [];
    }

    function num(value, fallback = 0) {
        const n = Number(value);
        return Number.isFinite(n) ? n : fallback;
    }

    function str(value, fallback = "") {
        if (value === undefined || value === null || value === "") return fallback;
        return String(value);
    }

    function esc(value) {
        return str(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function isCanonical(payload) {
        return payload && payload.schema === CANONICAL_SCHEMA && payload.me && payload.enemy;
    }

    function normalizeCard(card, index = 0) {
        card = card || {};

        const type = str(card.type || "Monster");
        const isMonster = type.toLowerCase() === "monster";

        const power = num(card.power || card.attack || card.display_stat || card.value || 0);
        const value = num(card.value || card.display_stat || card.power || card.attack || 0);
        const stat = num(card.display_stat || (isMonster ? power : value) || card.cost || 1, 1);

        return {
            id: str(card.id || card.card_id || card.runtime_id || card.name || ("card-" + index)),
            name: str(card.name || card.id || ("Card " + (index + 1))),
            type,
            element: str(card.element || "Neutral"),
            rarity: str(card.rarity || "Common"),
            sigil: str(card.sigil || "None"),
            cost: num(card.cost || card.energy_cost || 1, 1),
            stat,
            statLabel: str(card.combat_label || (isMonster ? "PWR" : "VAL")),
        };
    }

    function normalizeField(field) {
        field = field || {};

        return {
            trap: field.trap || null,
            monster: field.monster || null,
            spell: field.spell || null,
        };
    }

    function renderCard(card, options = {}) {
        const c = normalizeCard(card);
        const typeClass = "type-" + c.type.toLowerCase().replaceAll(" ", "-");
        const playable = options.playable ? " playable" : "";
        const field = options.field ? " az48-field-card" : "";

        return [
            '<button type="button" class="az48-card ' + typeClass + playable + field + '" data-card-id="' + esc(c.id) + '">',
            '<span class="az48-cost">E ' + esc(c.cost) + '</span>',
            '<span class="az48-rarity">' + esc(c.rarity) + '</span>',
            '<div class="az48-art"><span>' + esc(c.element.slice(0, 2).toUpperCase()) + '</span></div>',
            '<strong class="az48-name">' + esc(c.name) + '</strong>',
            '<div class="az48-tags"><span>' + esc(c.type) + '</span><span>' + esc(c.sigil) + '</span></div>',
            '<span class="az48-power">' + esc(c.statLabel) + ' ' + esc(c.stat) + '</span>',
            '</button>'
        ].join("");
    }

    function fieldCard(card, label) {
        if (!card) return '<article class="az48-slot">' + esc(label) + '</article>';
        return renderCard(card, { field: true });
    }

    function setVisible(id, visible) {
        const el = $(id);
        if (el) el.style.display = visible ? "" : "none";
    }

    function render(payload) {
        if (!isCanonical(payload)) {
            console.warn("[Ambitionz V51] ignored non-canonical state", payload);
            return;
        }

        hasCanonicalState = true;
        latestState = payload;
        window.__ambitionzArena48State = payload;

        const state = payload;
        const me = state.me || {};
        const enemy = state.enemy || {};
        const legal = state.legal_actions || {};
        const playable = arr(legal.playable_card_ids).map(String);
        const hand = arr(me.hand);

        const phase = str(state.phase || "start");

        setVisible("az48-start", Boolean(legal.show_start || legal.can_start || phase === "start" || !hand.length));
        setVisible("az48-strike", Boolean(legal.show_intents || legal.can_choose_intent));
        setVisible("az48-guard", Boolean(legal.show_intents || legal.can_choose_intent));
        setVisible("az48-focus", Boolean(legal.show_intents || legal.can_choose_intent));
        setVisible("az48-ready", Boolean(legal.show_ready || legal.can_ready));

        text("az48-mode", str(state.mode || "training"));
        text("az48-round", num(state.round || 1, 1));
        text("az48-phase", phase);
        text("az48-message", str(state.message || "Choose your action."));

        text("az48-me-name", str(me.name || "You"));
        text("az48-me-hp", num(me.hp || 3600, 3600));
        text("az48-me-energy", num(me.energy || 0));
        text("az48-me-max-energy", num(me.max_energy || me.energy || 0));
        text("az48-me-ambition", num(me.ambition || 0));

        text("az48-enemy-name", str(enemy.name || "Opponent"));
        text("az48-enemy-hp", num(enemy.hp || 3600, 3600));
        text("az48-enemy-energy", num(enemy.energy || 0));
        text("az48-enemy-max-energy", num(enemy.max_energy || enemy.energy || 0));
        text("az48-enemy-hand", num(enemy.hand_count || 0));

        const meField = normalizeField(me.field);
        const enemyField = normalizeField(enemy.field);

        const enemyFieldEl = $("az48-enemy-field");
        if (enemyFieldEl) {
            enemyFieldEl.innerHTML = [
                fieldCard(enemyField.trap, "Enemy Trap"),
                fieldCard(enemyField.monster, "Enemy Monster"),
                fieldCard(enemyField.spell, "Enemy Spell"),
            ].join("");
        }

        const meFieldEl = $("az48-me-field");
        if (meFieldEl) {
            meFieldEl.innerHTML = [
                fieldCard(meField.trap, "Trap Slot"),
                fieldCard(meField.monster, "Monster Slot"),
                fieldCard(meField.spell, "Spell Slot"),
            ].join("");
        }

        text("az48-hand-count", hand.length + " cards");

        const handEl = $("az48-hand");

        if (handEl) {
            if (!hand.length) {
                handEl.innerHTML = '<div class="az48-empty">No cards in hand. Press Start.</div>';
            } else {
                handEl.innerHTML = hand.map((card, index) => {
                    const c = normalizeCard(card, index);
                    return renderCard(c, { playable: playable.includes(String(c.id)) });
                }).join("");
            }
        }
    }

    function emit(name, payload) {
        if (!socket || !socket.connected) {
            setMessage("Socket not connected yet. Wait one second.");
            console.warn("[Ambitionz V51] socket not connected", name);
            return false;
        }

        socket.emit(name, payload || {});
        console.debug("[Ambitionz V51 emit]", name, payload || {});
        return true;
    }

    function startTraining() {
        setMessage("Starting training...");
        emit("az48_start_training", {});
    }

    function requestState() {
        emit("az48_request_state", {});
    }

    function setIntent(intent) {
        setMessage(intent + " selected.");
        emit("az48_set_intent", { intent });
    }

    function ready() {
        setMessage("Ready sent.");
        emit("az48_declare_ready", {});
    }

    function playCard(id) {
        setMessage("Playing card...");
        emit("az48_play_card", { card_id: id });
    }

    function bindSocketEvents() {
        socket.on("connect", () => {
            setMessage("Connected. Press Start.");
            console.debug("[Ambitionz V51] connected", socket.id);
            requestState();
        });

        socket.on("connect_error", (error) => {
            setMessage("Socket connection error.");
            console.error("[Ambitionz V51] connect_error", error);
        });

        socket.on("disconnect", () => {
            setMessage("Disconnected. Reconnecting...");
        });

        socket.on("az48_state", (payload) => {
            console.debug("[Ambitionz V51 canonical]", payload);
            render(payload);
        });

        socket.on("battle_log", (payload) => {
            if (typeof payload === "string") {
                setMessage(payload);
            } else if (payload && payload.message) {
                setMessage(payload.message);
            }
        });

        if (typeof socket.onAny === "function") {
            socket.onAny((eventName, payload) => {
                if (eventName === "az48_state") return;
                console.debug("[Ambitionz V51 ignored event]", eventName, payload);
            });
        }
    }

    function bindClicks() {
        document.addEventListener("click", (event) => {
            const card = event.target.closest(".az48-card[data-card-id]");
            if (card && card.closest("#az48-hand")) {
                playCard(card.dataset.cardId);
                return;
            }

            if (event.target.closest("#az48-start")) {
                startTraining();
                return;
            }

            if (event.target.closest("#az48-strike")) {
                setIntent("Strike");
                return;
            }

            if (event.target.closest("#az48-guard")) {
                setIntent("Guard");
                return;
            }

            if (event.target.closest("#az48-focus")) {
                setIntent("Focus");
                return;
            }

            if (event.target.closest("#az48-ready")) {
                ready();
            }
        });
    }

    function boot() {
        bootTries += 1;

        if (typeof window.io === "undefined") {
            setMessage("Loading Socket.IO...");

            if (bootTries < 80) {
                window.setTimeout(boot, 100);
            } else {
                setMessage("Socket.IO failed to load.");
            }

            return;
        }

        socket = window.io({
            transports: ["websocket", "polling"],
            reconnection: true,
        });

        window.AmbitionzArena48 = {
            render,
            startTraining,
            requestState,
            setIntent,
            ready,
            playCard,
            get socket() {
                return socket;
            },
            get state() {
                return latestState;
            },
        };

        bindSocketEvents();
        bindClicks();

        setMessage("Connecting...");
    }

    document.addEventListener("DOMContentLoaded", boot);
})();