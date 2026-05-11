(function () {
    "use strict";

    let socket = null;
    let latestState = null;
    let hasCanonicalState = false;
    let bootTries = 0;
    let previewCardId = null;

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

    function playSound(name, payload) {
        try {
            if (window.AmbitionzSound && typeof window.AmbitionzSound.play === "function") {
                window.AmbitionzSound.play(name, payload || {});
            }
        } catch (error) {
            console.debug("[Ambitionz V51 sound skipped]", error);
        }
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

    function adapter() {
        return window.AmbitionzArenaRendererAdapter || null;
    }

    function normalizeCard(card, index = 0) {
        if (adapter()) {
            return adapter().normalizeCard(card, index);
        }

        card = card || {};

        const type = str(card.type || "Monster");
        const isMonster = type.toLowerCase() === "monster";

        const power = num(card.power || card.attack || card.display_stat || card.value || 0);
        const value = num(card.value || card.display_stat || card.power || card.attack || 0);
        const stat = num(card.display_stat || (isMonster ? power : value) || card.cost || 1, 1);

        return {
            id: str(card.id || card.card_id || card.runtime_id || card.name || ("card-" + index)),
            cardId: str(card.card_id || card.id || ""),
            instanceId: str(card.instance_id || ""),
            name: str(card.name || card.id || ("Card " + (index + 1))),
            type,
            element: str(card.element || "Neutral"),
            rarity: str(card.rarity || "Common"),
            sigil: str(card.sigil || "None"),
            cost: num(card.cost || card.energy_cost || 1, 1),
            stat,
            statLabel: str(card.combat_label || (isMonster ? "PWR" : "VAL")),
            artUrl: "/static/img/cards/elemental/neutral.svg",
            elementCss: "element-neutral",
            typeCss: "type-" + type.toLowerCase().replaceAll(" ", "-"),
            rarityCss: "rarity-common",
            colors: {
                primary: "#9ea7b7",
                secondary: "#d9deea",
                accent: "#f4f7ff",
            },
            effect: str(card.effect || card.description || ""),
            preview: str(card.preview || card.effect_summary || card.effect || card.description || ""),
            disabledReason: str(card.disabled_reason || ""),
            playable: Boolean(card.playable),
            isMonster,
            lane: str(card.lane || ""),
        };
    }

    function normalizeField(field) {
        field = field || {};
        const lanes = field.lanes || field.board || {};

        return {
            trap: field.trap || null,
            monster: field.monster || null,
            spell: field.spell || null,
            lanes: {
                left: lanes.left || null,
                center: lanes.center || null,
                right: lanes.right || null,
            },
        };
    }

    function renderCard(card, options = {}) {
        const c = normalizeCard(card);
        const typeClass = c.typeCss || ("type-" + c.type.toLowerCase().replaceAll(" ", "-"));
        const elementClass = c.elementCss || "element-neutral";
        const rarityClass = c.rarityCss || "rarity-common";
        const playable = options.playable ? " playable" : "";
        const locked = options.disabledReason ? " is-locked" : "";
        const field = options.field ? " az48-field-card" : "";
        const colors = c.colors || {};
        const style = [
            "--az-card-primary:" + esc(colors.primary || "#9ea7b7"),
            "--az-card-secondary:" + esc(colors.secondary || "#d9deea"),
            "--az-card-accent:" + esc(colors.accent || "#f4f7ff"),
            "--az-card-art-image:url('" + esc(c.artUrl || "/static/img/cards/elemental/neutral.svg") + "')",
        ].join(";");

        const title = options.disabledReason || c.preview || c.effect || c.name;

        return [
            '<button type="button" class="az48-card az48-card-v2 ' + typeClass + ' ' + elementClass + ' ' + rarityClass + playable + (options.playable ? " is-playable az48-playable" : "") + locked + field + '" data-card-id="' + esc(c.id) + '" data-card-preview="' + esc(c.preview || c.effect || "") + '" data-disabled-reason="' + esc(options.disabledReason || "") + '" title="' + esc(title) + '" style="' + style + '">',
            '<span class="az48-card-sheen" aria-hidden="true"></span>',
            '<span class="az48-cost">E ' + esc(c.cost) + '</span>',
            '<span class="az48-rarity">' + esc(c.rarity) + '</span>',
            '<div class="az48-art"><span class="az48-art-image" aria-hidden="true"></span><span class="az48-art-glow" aria-hidden="true"></span></div>',
            '<strong class="az48-name">' + esc(c.name) + '</strong>',
            '<p class="az48-effect">' + esc(c.effect || c.role || c.kind || "") + '</p>',
            '<p class="az48-card-preview-line">' + esc(c.preview || "") + '</p>',
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

    function isStartPhase(phase) {
        const key = String(phase || "").toLowerCase();
        return key === "start" || key === "created";
    }

    function emptyHandMessage(state, legal) {
        const phase = String((state && state.phase) || "").toLowerCase();
        const me = (state && state.me) || {};

        if (isStartPhase(phase) || legal.can_start || legal.show_start) {
            return "No cards yet. Press Start.";
        }

        if (legal.can_ready || legal.show_ready) {
            return "No cards in hand. Choose an intent, then press Ready.";
        }

        if (num(me.deck_count || 0) <= 0) {
            return "Deck empty. Use intents and Unleash to finish the duel.";
        }

        return "No playable cards right now. Resolve the round to draw again.";
    }


    function ensureClarityPanel() {
        let panel = document.getElementById("az48-clarity-panel");
        if (panel) return panel;

        const app =
            document.querySelector(".az48-arena") ||
            document.querySelector(".az-arena-app") ||
            document.querySelector("main") ||
            document.body;

        panel = document.createElement("section");
        panel.id = "az48-clarity-panel";
        panel.className = "az48-clarity-panel";
        panel.innerHTML = [
            '<div class="az48-clarity-card az48-turn-card">',
            '<span>Next</span>',
            '<strong id="az48-next-action">Start</strong>',
            '<p id="az48-turn-hint">Press Start to begin.</p>',
            '</div>',
            '<div class="az48-clarity-card az48-preview-card">',
            '<span>Card Preview</span>',
            '<strong id="az48-card-preview-name">No card selected</strong>',
            '<p id="az48-card-preview-text">Hover a card to preview its effect.</p>',
            '</div>',
            '<div class="az48-clarity-card az48-timeline-card">',
            '<span>Timeline</span>',
            '<strong id="az48-round-result">No round yet</strong>',
            '<ol id="az48-event-lines"></ol>',
            '<details class="az48-help-drawer"><summary>?</summary><ul id="az48-help-lines"></ul></details>',
            '</div>'
        ].join("");

        const hand = $("az48-hand");
        if (hand && hand.parentNode) {
            hand.parentNode.insertBefore(panel, hand);
        } else {
            app.appendChild(panel);
        }

        return panel;
    }

    function setList(id, values) {
        const el = document.getElementById(id);
        if (!el) return;

        const list = arr(values).filter(Boolean);
        if (!list.length) {
            el.innerHTML = '<li>No information yet.</li>';
            return;
        }

        el.innerHTML = list.map((line) => '<li>' + esc(line) + '</li>').join("");
    }

    function renderActionHelp(actions) {
        const el = document.getElementById("az48-action-help");
        if (!el) return;

        actions = actions || {};

        const rows = [
            ["Strike", actions.Strike || "+2 attack this round."],
            ["Guard", actions.Guard || "+4 shield this round."],
            ["Focus", actions.Focus || "+3 Ambition. Charges Unleash."],
            ["Ready", actions.Ready || "Resolves combat."]
        ];

        el.innerHTML = rows.map((row) => {
            return '<div class="az48-action-help-row"><strong>' + esc(row[0]) + '</strong><span>' + esc(row[1]) + '</span></div>';
        }).join("");
    }

    function eventLine(event) {
        if (!event) return "";
        const label = event.actor_label ? event.actor_label + ": " : "";
        return label + str(event.text || event.type || "");
    }

    function renderEvents(payload) {
        const el = document.getElementById("az48-event-lines");
        if (!el) return;

        const summaryEvents = arr(payload.round_summary && payload.round_summary.events);
        const events = summaryEvents.length ? summaryEvents : (arr(payload.round_events).length ? arr(payload.round_events) : arr(payload.events));
        const lines = events.map(eventLine).filter(Boolean).slice(-4);

        if (!lines.length) {
            el.innerHTML = '<li>Choose a tactic to start the timeline.</li>';
            return;
        }

        el.innerHTML = lines.map((line) => '<li>' + esc(line) + '</li>').join("");
    }

    function cardStateMap(payload) {
        const legal = (payload && payload.legal_actions) || {};
        const map = new Map();
        arr(legal.card_states).forEach((state) => {
            if (state && state.id) map.set(String(state.id), state);
        });
        return map;
    }

    function findPreviewCard(payload, playable) {
        const hand = arr(payload && payload.me && payload.me.hand);
        if (!hand.length) return null;

        if (previewCardId) {
            const selected = hand.find((card, index) => normalizeCard(card, index).id === String(previewCardId));
            if (selected) return selected;
        }

        const playableSet = new Set(arr(playable).map(String));
        return hand.find((card, index) => playableSet.has(normalizeCard(card, index).id)) || hand[0];
    }

    function renderCardPreview(payload, playable) {
        const nameEl = document.getElementById("az48-card-preview-name");
        const textEl = document.getElementById("az48-card-preview-text");
        if (!nameEl || !textEl) return;

        const card = findPreviewCard(payload, playable);
        if (!card) {
            nameEl.textContent = "No cards in hand";
            textEl.textContent = emptyHandMessage(payload, payload.legal_actions || {});
            return;
        }

        const normalized = normalizeCard(card);
        const states = cardStateMap(payload);
        const cardState = states.get(String(normalized.id)) || {};
        nameEl.textContent = normalized.name;
        textEl.textContent = cardState.disabled_reason || normalized.preview || normalized.effect || "No effect preview.";
    }

    function renderClarity(payload) {
        ensureClarityPanel();

        const help = payload.help || {};
        const preview = payload.enemy_preview || {};
        const summary = payload.round_summary || {};
        const turn = payload.turn || {};
        const legal = payload.legal_actions || {};

        setList("az48-help-lines", help.turn_order || [
            "1. Choose Strike, Guard or Focus.",
            "2. Play one card if you can.",
            "3. Press Ready to resolve combat."
        ]);

        const nextAction = document.getElementById("az48-next-action");
        const turnHint = document.getElementById("az48-turn-hint");

        if (nextAction) {
            nextAction.textContent = str(legal.primary_action || turn.primary_action || "choose").replaceAll("_", " ");
        }

        if (turnHint) {
            const enemyText = preview.message ? " Enemy: " + preview.message : "";
            turnHint.textContent = str(turn.prompt || legal.prompt || payload.message || "Choose your next action.") + enemyText;
        }

        const result = document.getElementById("az48-round-result");
        if (result) result.textContent = summary.short_result || "Current Round";

        renderEvents(payload);
        renderCardPreview(payload, legal.playable_card_ids || []);
    }


    function render(payload) {
        if (!isCanonical(payload)) {
            console.warn("[Ambitionz V51] ignored non-canonical state", payload);
            return;
        }

        const previousState = latestState;

        hasCanonicalState = true;
        latestState = payload;
        window.__ambitionzArena48State = payload;
        window.__ambitionzArenaNormalizedState = adapter()
            ? adapter().normalizeArenaState(payload)
            : payload;

        window.dispatchEvent(new CustomEvent("ambitionz:arena_state_rendered", {
            detail: {
                payload,
                state: window.__ambitionzArenaNormalizedState,
            },
        }));

        const state = payload;
        const me = state.me || {};
        const enemy = state.enemy || {};
        const legal = state.legal_actions || {};
        const isFinished = String(state.phase || "").toLowerCase() === "finished" || Boolean(state.winner);
        const playable = isFinished ? [] : arr(legal.playable_card_ids).map(String);
        const hand = arr(me.hand);
        const statesByCard = cardStateMap(state);

        const phase = str(state.phase || "start");

        if (previousState && isCanonical(previousState)) {
            const previousMe = previousState.me || {};
            const previousEnemy = previousState.enemy || {};
            const meLostHp = num(previousMe.hp || 0) > num(me.hp || 0);
            const enemyLostHp = num(previousEnemy.hp || 0) > num(enemy.hp || 0);

            if (meLostHp || enemyLostHp) {
                playSound("damage");
            }
        }

        renderClarity(state);

        const showStart = !isFinished && PAGE_KIND === "training" && Boolean(legal.show_start || legal.can_start || isStartPhase(phase));
        const showIntents = !isFinished && Boolean(legal.show_intents || legal.can_choose_intent);
        const showReady = !isFinished && Boolean(legal.show_ready || legal.can_ready);
        const handIsEmpty = hand.length === 0;

        setVisible("az48-start", showStart);
        setVisible("az48-strike", showIntents);
        setVisible("az48-guard", showIntents);
        setVisible("az48-focus", showIntents);
        setVisible("az48-ready", showReady);
        document.body.classList.toggle("az48-has-actions", showStart || showIntents || showReady);
        document.body.classList.toggle("az48-has-hand", hand.length > 0);
        document.body.classList.toggle("az48-hand-empty", handIsEmpty);
        document.body.classList.toggle("az48-can-ready", showReady);
        document.body.classList.toggle("az48-can-start", showStart);
        document.body.classList.toggle("az48-match-started", hand.length > 0 || !isStartPhase(phase));
        document.body.dataset.az48Step = str((state.turn && state.turn.step) || phase);
        document.body.dataset.az48PrimaryAction = str(legal.primary_action || "");

        text("az48-mode", str(state.mode || "training"));
        text("az48-round", num(state.round || 1, 1));
        text("az48-phase", phase);
        text("az48-message", str(state.message || "Choose your action."));

        text("az48-me-name", str(me.name || "You"));
        text("az48-me-hp", me.hp === 0 ? 0 : num(me.hp || 28, 28));
        text("az48-me-energy", num(me.energy || 0));
        text("az48-me-max-energy", num(me.max_energy || me.energy || 0));
        text("az48-me-ambition", num(me.ambition || 0));
        text("my-deck", num(me.deck_count || 0));
        text("my-ready", me.ready ? "Ready" : "Not ready");

        text("az48-enemy-name", str(enemy.name || "Opponent"));
        text("az48-enemy-hp", enemy.hp === 0 ? 0 : num(enemy.hp || 28, 28));
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
                fieldCard(enemyField.lanes.left, "Enemy Left"),
                fieldCard(enemyField.lanes.center, "Enemy Center"),
                fieldCard(enemyField.lanes.right, "Enemy Right"),
            ].join("");
        }

        const meFieldEl = $("az48-me-field");
        if (meFieldEl) {
            meFieldEl.innerHTML = [
                fieldCard(meField.lanes.left, "Left Lane"),
                fieldCard(meField.lanes.center, "Center Lane"),
                fieldCard(meField.lanes.right, "Right Lane"),
            ].join("");
        }

        text("az48-hand-count", hand.length + " cards");

        const handEl = $("az48-hand");

        if (handEl) {
            if (!hand.length) {
                handEl.innerHTML = '<div class="az48-empty">' + esc(emptyHandMessage(state, legal)) + '</div>';
            } else {
                handEl.innerHTML = hand.map((card, index) => {
                    const c = normalizeCard(card, index);
                    const cardState = statesByCard.get(String(c.id)) || {};
                    return renderCard(c, {
                        playable: playable.includes(String(c.id)) || Boolean(cardState.playable),
                        disabledReason: str(cardState.disabled_reason || c.disabledReason || ""),
                    });
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

    function matchIsFinished() {
        const phase = String((latestState && latestState.phase) || "").toLowerCase();
        return phase === "finished" || Boolean(latestState && latestState.winner);
    }

    function setIntent(intent) {
        if (matchIsFinished()) {
            setMessage("Match finished. Start a new training match or go back to Arena.");
            return;
        }

        setMessage(intent + " selected.");
        if (emit("az48_set_intent", { intent })) {
            playSound("intent", { element: intent });
        }
    }

    function ready() {
        if (matchIsFinished()) {
            setMessage("Match finished. Start a new training match or go back to Arena.");
            return;
        }

        setMessage("Ready sent.");
        if (emit("az48_declare_ready", {})) {
            playSound("ready");
        }
    }

    function playCard(id) {
        if (matchIsFinished()) {
            setMessage("Match finished. Start a new training match or go back to Arena.");
            return;
        }

        const hand = arr((latestState && latestState.me && latestState.me.hand) || []);
        const index = hand.findIndex((card, cardIndex) => normalizeCard(card, cardIndex).id === String(id));

        if (index < 0) {
            setMessage("Card is no longer in hand.");
            return;
        }

        const card = normalizeCard(hand[index], index);
        const legal = (latestState && latestState.legal_actions) || {};
        const playable = arr(legal.playable_card_ids).map(String);

        if (!playable.includes(String(card.id))) {
            const states = cardStateMap(latestState);
            const cardState = states.get(String(card.id)) || {};
            setMessage(cardState.disabled_reason || "This card cannot be played now.");
            return;
        }

        const payload = { card_id: id, card_index: index };
        if (card.isMonster) {
            const legalLanes = arr(legal.legal_lanes);
            if (!legalLanes.length) {
                setMessage("No empty lane available.");
                return;
            }
            payload.lane = legalLanes[0];
        }

        setMessage("Playing card...");
        if (emit("az48_play_card", payload)) {
            playSound("cardFly", { element: card.element });
            window.setTimeout(() => playSound("cardImpact", { element: card.element }), 180);
        }
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
            const startBtn = event.target.closest("#az48-floating-start, #az48-start, #join-queue-btn, [data-az48-action='start-training']");
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

            const card = event.target.closest("#az48-hand .az48-card[data-card-id], #hand .az48-card[data-card-id]");
            if (card) {
                event.preventDefault();
                previewCardId = card.dataset.cardId;
                if (latestState) renderClarity(latestState);

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

        document.addEventListener("mouseover", (event) => {
            const card = event.target.closest("#az48-hand .az48-card[data-card-id], #hand .az48-card[data-card-id]");
            if (!card) return;
            previewCardId = card.dataset.cardId;
            if (latestState) renderClarity(latestState);
        });

        document.addEventListener("focusin", (event) => {
            const card = event.target.closest("#az48-hand .az48-card[data-card-id], #hand .az48-card[data-card-id]");
            if (!card) return;
            previewCardId = card.dataset.cardId;
            if (latestState) renderClarity(latestState);
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
            transports: ["polling"],
            upgrade: false,
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
