(function () {
    "use strict";

    let socket = null;
    let latestState = null;
    let hasCanonicalState = false;
    let bootTries = 0;

    const CANONICAL_SCHEMA = "ambitionz_arena_clean_v50";

    const AZ48_NO_PLAYABLE_HELP = "No playable card with current energy. Press Ready to resolve the round.";

    const PAGE_KIND = document.body ? document.body.getAttribute("data-page-kind") : "arena";
    const ID_ALIASES = {
        "az48-ready": ["ready-btn"],
        "az48-hand": ["hand"],
        "az48-round": ["round-label"],
        "az48-phase": ["phase-label"],
        "az48-me-name": ["my-name"],
        "az48-enemy-name": ["enemy-name"],
        "az48-me-hp": ["my-hp"],
        "az48-enemy-hp": ["enemy-hp"],
    };

    function $(id) {
        const direct = document.getElementById(id);
        if (direct) return direct;

        const aliases = ID_ALIASES[id] || [];
        for (const alias of aliases) {
            const el = document.getElementById(alias);
            if (el) return el;
        }

        return null;
    }

    function elements(id) {
        const ids = [id].concat(ID_ALIASES[id] || []);
        const seen = new Set();
        return ids
            .map((candidate) => document.getElementById(candidate))
            .filter((el) => {
                if (!el || seen.has(el)) return false;
                seen.add(el);
                return true;
            });
    }

    function text(id, value) {
        elements(id).forEach((el) => {
            el.textContent = value;
        });
    }

    function setMessage(value) {
        text("az48-message", value);
    }

    function appendLog(value) {
        const log = document.getElementById("battle-log");
        if (!log || !value) return;

        const line = document.createElement("div");
        line.textContent = value;
        log.appendChild(line);

        while (log.children.length > 8) {
            log.removeChild(log.firstElementChild);
        }
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

        const showStart = PAGE_KIND === "training" && Boolean(legal.show_start || legal.can_start || phase === "start" || !hand.length);
        const showIntents = Boolean(legal.show_intents || legal.can_choose_intent);
        const showReady = Boolean(legal.show_ready || legal.can_ready);

        setVisible("az48-start", showStart);
        setVisible("az48-strike", showIntents);
        setVisible("az48-guard", showIntents);
        setVisible("az48-focus", showIntents);
        setVisible("az48-ready", showReady);
        document.body.classList.toggle("az48-has-actions", showStart || showIntents || showReady);

        text("az48-mode", str(state.mode || "training"));
        text("az48-round", num(state.round || 1, 1));
        text("az48-phase", phase);
        text("az48-message", str(state.message || "Choose your action."));

        text("az48-me-name", str(me.name || "You"));
        text("az48-me-hp", num(me.hp || 3600, 3600));
        text("az48-me-energy", num(me.energy || 0));
        text("az48-me-max-energy", num(me.max_energy || me.energy || 0));
        text("az48-me-ambition", num(me.ambition || 0));
        text("my-deck", num(me.deck_count || 0));
        text("my-ready", me.ready ? "Ready" : "Not ready");

        text("az48-enemy-name", str(enemy.name || "Opponent"));
        text("az48-enemy-hp", num(enemy.hp || 3600, 3600));
        text("az48-enemy-energy", num(enemy.energy || 0));
        text("az48-enemy-max-energy", num(enemy.max_energy || enemy.energy || 0));
        text("az48-enemy-hand", num(enemy.hand_count || 0));
        text("enemy-deck", num(enemy.deck_count || 0));
        text("enemy-ready", enemy.ready ? "Ready" : "Not ready");

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
        const hand = arr((latestState && latestState.me && latestState.me.hand) || []);
        const index = hand.findIndex((card, cardIndex) => normalizeCard(card, cardIndex).id === String(id));

        if (index < 0) {
            setMessage("Card is no longer in hand.");
            return;
        }

        setMessage("Playing card...");
        emit("az48_play_card", { card_id: id, card_index: index });
    }

    function joinQueue() {
        if (PAGE_KIND === "training") {
            startTraining();
            return;
        }

        setMessage("Searching for opponent...");
        emit("join_queue", {});
    }

    function joinBotMatch() {
        setMessage("Starting bot duel...");
        emit("join_bot_match", {});
    }

    function joinPrivateRoom() {
        const input = $("private-room-code");
        const code = str(input && input.value).trim().toUpperCase().replace(/\s+/g, "");

        if (!code || code.length !== 5) {
            setMessage("Enter a valid 5-character private room code.");
            appendLog("Invalid private room code.");
            return;
        }

        setMessage("Joining private room " + code + "...");
        emit("join_private_room", { code });
    }

    function cancelQueue() {
        setMessage("Cancelling match search...");
        emit("cancel_queue", {});
    }

    function bindSocketEvents() {
        socket.on("connect", () => {
            setMessage(PAGE_KIND === "training" ? "Connected. Press Start." : "Connected. Choose how to find a duel.");
            console.debug("[Ambitionz V51] connected", socket.id);
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

        socket.on("arena_state_update", (payload) => {
            if (isCanonical(payload)) render(payload);
        });

        socket.on("battle_log", (payload) => {
            const message = typeof payload === "string" ? payload : (payload && (payload.message || payload.msg));

            if (message) {
                setMessage(message);
                appendLog(message);
            }
        });

        socket.on("queue_status", (payload) => {
            const message = payload && payload.msg ? payload.msg : "Queue updated.";
            setMessage(message);
            appendLog(message);
        });

        socket.on("match_found", (payload) => {
            const message = payload && payload.msg ? payload.msg : "Match found. Duel started.";
            setMessage(message);
            appendLog(message);
        });

        socket.on("matchmaking_status", (payload) => {
            if (!payload || !payload.status) return;
            if (payload.status === "searching") setMessage("Searching for opponent...");
            if (payload.status === "fallback") setMessage("No player found. Bot duel started.");
            if (payload.status === "matched") setMessage("Match found.");
            if (payload.status === "cancelled") setMessage("Search cancelled.");
            if (payload.status === "error") setMessage("Matchmaking failed. Try again.");
        });

        socket.on("action_error", (payload) => {
            const message = payload && payload.message ? payload.message : "Action failed.";
            setMessage(message);
            appendLog(message);
        });

        socket.on("game_over", (payload) => {
            const message = "Game Over: " + str(payload && payload.result, "Unknown");
            setMessage(message);
            appendLog(message);
        });

        socket.on("opponent_left", (payload) => {
            const message = payload && payload.msg ? payload.msg : "Opponent left.";
            setMessage(message);
            appendLog(message);
        });

        socket.on("presence_update", (payload) => {
            if (!payload) return;
            window.__ambitionzArenaPresence = payload;
        });

        socket.on("match_state", (payload) => {
            if (typeof payload === "string") {
                appendLog(payload);
            } else if (payload && payload.message && !hasCanonicalState) {
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
            const startBtn = event.target.closest("#az48-start, #join-queue-btn, [data-az48-action='start-training']");
            if (startBtn) {
                event.preventDefault();
                startTraining();
                return;
            }

            const strikeBtn = event.target.closest("#az48-strike");
            if (strikeBtn) {
                event.preventDefault();
                setIntent("Strike");
                return;
            }

            const guardBtn = event.target.closest("#az48-guard");
            if (guardBtn) {
                event.preventDefault();
                setIntent("Guard");
                return;
            }

            const focusBtn = event.target.closest("#az48-focus");
            if (focusBtn) {
                event.preventDefault();
                setIntent("Focus");
                return;
            }

            const readyBtn = event.target.closest("#az48-ready, #ready-btn");
            if (readyBtn) {
                event.preventDefault();
                ready();
                return;
            }

            const card = event.target.closest("#az48-hand .az48-card[data-card-id]");
            if (card) {
                event.preventDefault();

                const cardIsPlayable =
                    card.classList.contains("is-playable") ||
                    card.classList.contains("playable") ||
                    card.classList.contains("az48-playable");

                if (!cardIsPlayable) {
                    setMessage("This card cannot be played now. Choose another action or press Ready.");
                    return;
                }

                playCard(card.dataset.cardId);
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
            joinQueue,
            joinBotMatch,
            joinPrivateRoom,
            cancelQueue,
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


// ARENA_PLAY_CARD_AZ48_FIX_V56


// ARENA_PLAY_CARD_AZ48_FIX_V57


// ARENA_PLAY_CARD_ID_FIX_V58
