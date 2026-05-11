(function () {
    "use strict";

    let socket = null;
    let latestState = null;
    let hasCanonicalState = false;
    let bootTries = 0;
    let previewCardId = null;
    let detailCardSnapshot = null;
    let selectedCardId = null;
    let selectionMode = "";
    let commandSeq = 0;

    const CANONICAL_SCHEMA = "ambitionz_arena_clean_v50";
    const ARENA_COMMAND_SCHEMA = "arena_command_v1";
    const LEGACY_EVENT_BY_ACTION = {
        start_training: "az48_start_training",
        request_state: "az48_request_state",
        set_intent: "az48_set_intent",
        play_card: "az48_play_card",
        ready: "az48_declare_ready",
        unleash: "az48_unleash",
    };

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

    function setServerError(message) {
        const panel = document.getElementById("az48-server-error");
        const textEl = document.getElementById("az48-server-error-text");
        const value = str(message || "");

        if (!panel || !textEl) return;

        panel.hidden = !value;
        panel.classList.toggle("is-visible", Boolean(value));
        textEl.textContent = value;
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

    function firstValue(...values) {
        return values.find((value) => value !== undefined && value !== null && value !== "");
    }

    function slug(value, fallback = "event") {
        const text = str(value, fallback).toLowerCase();
        return text.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || fallback;
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

        const power = num(firstValue(card.power, card.attack, card.display_stat, card.value), 0);
        const value = num(firstValue(card.value, card.display_stat, card.power, card.attack), 0);
        const attack = num(firstValue(card.attack, card.atk, power), 0);
        const currentHp = num(firstValue(card.current_hp, card.currentHp, card.hp, card.max_hp, card.maxHp), 0);
        const maxHp = num(firstValue(card.max_hp, card.maxHp, card.hp, currentHp), 0);
        const stat = num(firstValue(card.display_stat, card.stat, isMonster ? power : value, card.cost), 1);

        return {
            id: str(card.id || card.card_id || card.runtime_id || card.name || ("card-" + index)),
            cardId: str(card.card_id || card.id || ""),
            instanceId: str(card.instance_id || ""),
            name: str(card.name || card.id || ("Card " + (index + 1))),
            type,
            kind: str(card.kind || type),
            element: str(card.element || "Neutral"),
            rarity: str(card.rarity || "Common"),
            sigil: str(card.sigil || "None"),
            cost: num(firstValue(card.cost, card.energy_cost, card.energyCost), 1),
            stat,
            statLabel: str(card.combat_label || (isMonster ? "PWR" : "VAL")),
            attack,
            currentHp,
            maxHp,
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
            keywords: arr(card.keywords).map(String),
            keywordText: arr(card.keyword_text).map(String),
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
        const selected = options.selected ? " is-selected selected" : "";
        const laneSlot = options.lane ? " az48-lane-slot" : "";
        const legalLane = options.legalLane ? " is-legal-lane" : "";
        const feedbackClass = options.feedbackClass ? " " + options.feedbackClass : "";
        const colors = c.colors || {};
        const keywordTags = arr(c.keywordText && c.keywordText.length ? c.keywordText : c.keywords).slice(0, 2);
        const stats = c.isMonster
            ? '<div class="az48-card-stats"><span>ATK ' + esc(c.attack || c.stat || 0) + '</span><span>HP ' + esc(c.currentHp || 0) + '/' + esc(c.maxHp || 0) + '</span></div>'
            : '<div class="az48-card-stats"><span>' + esc(c.statLabel || "VAL") + ' ' + esc(c.stat || 0) + '</span><span>' + esc(c.element || "Neutral") + '</span></div>';
        const laneData = options.lane ? ' data-az48-lane="' + esc(options.lane) + '"' : "";
        const style = [
            "--az-card-primary:" + esc(colors.primary || "#9ea7b7"),
            "--az-card-secondary:" + esc(colors.secondary || "#d9deea"),
            "--az-card-accent:" + esc(colors.accent || "#f4f7ff"),
            "--az-card-art-image:url('" + esc(c.artUrl || "/static/img/cards/elemental/neutral.svg") + "')",
        ].join(";");

        const title = options.disabledReason || c.preview || c.effect || c.name;

        return [
            '<button type="button" class="az48-card az48-card-v2 ' + typeClass + ' ' + elementClass + ' ' + rarityClass + playable + (options.playable ? " is-playable az48-playable" : "") + locked + field + selected + laneSlot + legalLane + feedbackClass + '" data-card-id="' + esc(c.id) + '"' + laneData + ' data-card-preview="' + esc(c.preview || c.effect || "") + '" data-disabled-reason="' + esc(options.disabledReason || "") + '" aria-pressed="' + (options.selected ? "true" : "false") + '" title="' + esc(title) + '" style="' + style + '">',
            '<span class="az48-card-sheen" aria-hidden="true"></span>',
            '<span class="az48-cost">E ' + esc(c.cost) + '</span>',
            '<span class="az48-rarity">' + esc(c.rarity) + '</span>',
            '<div class="az48-art"><span class="az48-art-image" aria-hidden="true"></span><span class="az48-art-glow" aria-hidden="true"></span></div>',
            '<strong class="az48-name">' + esc(c.name) + '</strong>',
            stats,
            '<p class="az48-effect">' + esc(c.effect || c.role || c.kind || "") + '</p>',
            '<p class="az48-card-preview-line">' + esc(c.preview || "") + '</p>',
            '<div class="az48-tags"><span>' + esc(c.element || "Neutral") + '</span><span>' + esc(c.type) + '</span>' + keywordTags.map((keyword) => '<span>' + esc(keyword) + '</span>').join("") + '</div>',
            '<span class="az48-power">' + esc(c.statLabel) + ' ' + esc(c.stat) + '</span>',
            '</button>'
        ].join("");
    }

    function fieldCard(card, label, owner, lane, legalLane, feedbackClass = "") {
        const feedback = feedbackClass ? " " + feedbackClass : "";

        if (!card) {
            return '<button type="button" class="az48-slot az48-lane-slot' + (legalLane ? " is-legal-lane" : "") + feedback + '" data-az48-owner="' + esc(owner || "") + '" data-az48-lane="' + esc(lane || "") + '">' + esc(label) + '</button>';
        }
        return renderCard(card, { field: true, lane, legalLane, feedbackClass });
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

    function intentLabel(value, fallback = "Choose") {
        const key = str(value || "").toLowerCase();
        const labels = {
            strike: "Strike",
            attack: "Strike",
            guard: "Guard",
            defend: "Guard",
            focus: "Focus",
            build: "Focus",
        };

        return labels[key] || fallback;
    }

    function opponentStatusLabel(state, enemy, preview) {
        const phase = str((state && state.phase) || "").toLowerCase();

        if (phase === "finished" || (state && state.winner)) return "Finished";
        if (enemy && enemy.ready) return "Ready";
        if (enemy && enemy.intent) return intentLabel(enemy.intent, "Intent set");
        if (preview && preview.ready) return "Ready";
        if (preview && preview.intent) return intentLabel(preview.intent, "Intent set");
        if (preview && preview.message) return str(preview.message);

        return "Choosing";
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
            '<ol class="az48-step-list" id="az48-step-list" aria-label="Round steps"></ol>',
            '<div class="az48-server-error" id="az48-server-error" hidden>',
            '<strong>Server message</strong>',
            '<p id="az48-server-error-text"></p>',
            '</div>',
            '</div>',
            '<div class="az48-clarity-card az48-preview-card">',
            '<span>Card Detail</span>',
            '<strong id="az48-card-preview-name">No card selected</strong>',
            '<div class="az48-card-detail-stats" id="az48-card-detail-stats"></div>',
            '<p id="az48-card-preview-text">Hover a card to preview its effect.</p>',
            '<ul class="az48-card-keyword-lines" id="az48-card-keyword-lines"></ul>',
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

    function setButtonContent(id, label, detail) {
        const el = $(id);
        if (!el) return;

        el.innerHTML = esc(label) + (detail ? " <small>" + esc(detail) + "</small>" : "");
    }

    function getArenaUiStep(state) {
        state = state || {};

        const legal = state.legal_actions || {};
        const phase = str(state.phase || "").toLowerCase();

        if (phase === "finished" || state.winner) return "finished";
        if (selectionMode === "lane") return "choose_lane";
        if (selectionMode === "target") return "choose_target";
        if (isStartPhase(phase) || legal.can_start || legal.show_start) return "start";
        if (legal.show_intents || legal.can_choose_intent) return "choose_intent";
        if (legal.can_play_cards && arr(legal.playable_card_ids).length) return "choose_card";
        if (legal.can_ready || legal.show_ready) return "ready";
        if (phase === "waiting" || ((state.me || {}).ready && !(state.enemy || {}).ready)) return "waiting";
        return "waiting";
    }

    function selectedCardName() {
        const entry = selectedHandCard();
        return entry ? entry.card.name : "the selected card";
    }

    function uiCopyForStep(step, state) {
        const legal = (state && state.legal_actions) || {};
        const message = str((state && state.message) || "");

        if (step === "start") {
            return {
                title: "1. Start Training",
                hint: "Press Start to draw your opening hand.",
                button: "Start Training",
                detail: "Draw Hand",
            };
        }

        if (step === "choose_intent") {
            return {
                title: "1. Choose Intent",
                hint: "Pick Strike, Guard or Focus for this round.",
                button: "Choose Intent",
                detail: "Strike / Guard / Focus",
            };
        }

        if (step === "choose_card") {
            return {
                title: "2. Choose Card",
                hint: "Play one highlighted card, or skip the card and press Ready.",
                button: "Play Card",
                detail: "Optional",
            };
        }

        if (step === "choose_lane") {
            return {
                title: "3. Choose Lane",
                hint: "Select an empty lane for " + selectedCardName() + ".",
                button: "Choose Lane",
                detail: "Left / Center / Right",
            };
        }

        if (step === "choose_target") {
            return {
                title: "3. Choose Target",
                hint: "Select a highlighted target for " + selectedCardName() + ".",
                button: "Choose Target",
                detail: "Required",
            };
        }

        if (step === "ready") {
            return {
                title: "4. Ready",
                hint: legal.can_play_cards ? "You may still play one card, or press Ready to resolve." : "Press Ready to resolve the round.",
                button: "Ready",
                detail: "Resolve Round",
            };
        }

        if (step === "finished") {
            return {
                title: "Match Finished",
                hint: message || "The duel has ended.",
                button: "Finished",
                detail: "",
            };
        }

        return {
            title: "5. Wait",
            hint: message || "Waiting for the opponent or server update.",
            button: "Waiting",
            detail: "Resolve",
        };
    }

    function renderStepList(activeStep) {
        const el = document.getElementById("az48-step-list");
        if (!el) return;

        const order = [
            ["choose_intent", "Intent"],
            ["choose_card", "Card"],
            ["choose_lane", "Lane/Target"],
            ["ready", "Ready"],
            ["waiting", "Resolve"],
        ];
        const aliases = {
            start: "choose_intent",
            choose_target: "choose_lane",
            finished: "waiting",
        };
        const current = aliases[activeStep] || activeStep;
        const activeIndex = Math.max(0, order.findIndex((step) => step[0] === current));

        el.innerHTML = order.map((step, index) => {
            const status = index < activeIndex ? "done" : (index === activeIndex ? "active" : "todo");
            return '<li class="az48-step-item az48-step-' + status + '">' + esc(step[1]) + '</li>';
        }).join("");
    }

    function updateActionButtons(step) {
        setButtonContent("az48-start", "Start Training", "Draw Hand");
        setButtonContent("az48-strike", "Strike", "Attack");
        setButtonContent("az48-guard", "Guard", "Defend");
        setButtonContent("az48-focus", "Focus", "Build");

        if (step === "choose_card") {
            setButtonContent("az48-ready", "Skip Card", "Ready");
        } else if (step === "ready") {
            setButtonContent("az48-ready", "Ready", "Resolve Round");
        } else {
            setButtonContent("az48-ready", "Ready", "Resolve Round");
        }
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

    function summaryEventsFrom(value) {
        if (Array.isArray(value)) return value;
        if (!value || typeof value !== "object") return [];
        if (Array.isArray(value.combat_log)) return value.combat_log;
        if (Array.isArray(value.combatLog)) return value.combatLog;
        if (Array.isArray(value.combat_events)) return value.combat_events;
        if (Array.isArray(value.events)) return value.events;
        return [];
    }

    function getRoundCombatLog(state) {
        state = state || {};

        const sources = [
            state.combat_log,
            state.round_summary,
            state.last_round_summary,
            state.match && state.match.combat_log,
        ];

        for (const source of sources) {
            const events = summaryEventsFrom(source);
            if (events.length) return events.filter((event) => event && typeof event === "object");
        }

        return [];
    }

    function eventAmount(event) {
        event = event || {};
        if (event.amount !== undefined && event.amount !== null && event.amount !== "") return num(event.amount, 0);
        if (event.damage !== undefined && event.damage !== null && event.damage !== "") return num(event.damage, 0);
        if (event.value !== undefined && event.value !== null && event.value !== "") return num(event.value, 0);
        return 0;
    }

    function eventName(value, fallback) {
        if (value && typeof value === "object") {
            return str(value.name || value.card_name || value.label, fallback);
        }
        return str(value, fallback);
    }

    function renderSummaryItem(kind, text) {
        const safeKind = slug(kind || "event", "event");
        return '<li class="az48-summary-item az48-summary-item-' + safeKind + '">' + esc(text) + '</li>';
    }

    function renderCombatEvent(event) {
        event = event || {};
        const type = str(event.type || event.kind || "").toLowerCase();
        const amount = eventAmount(event);
        const attackerName = eventName(event.attacker_name || event.attacker, "Carta");
        const defenderName = eventName(event.defender_name || event.defender, "Carta");
        const cardName = eventName(event.card_name || event.card || event.name, "Carta");
        const targetName = eventName(event.target_name || event.target || event.defender_name || event.defender || event.name, "alvo");
        const heroTarget = eventName(event.target_name || event.target || "", event.target_side ? "herói" : "alvo");

        if (type === "round_start") return renderSummaryItem("event", "Rodada iniciada.");
        if (type === "round_resolve") return renderSummaryItem("event", "Resolução da rodada.");
        if (type === "lane_attack") return renderSummaryItem("attack", attackerName + " atacou " + defenderName + ".");
        if (type === "direct_attack") return renderSummaryItem("attack", attackerName + " atacou diretamente o herói.");
        if (type === "creature_damage") return renderSummaryItem("damage", targetName + " recebeu " + amount + " de dano.");
        if (type === "hero_damage") return renderSummaryItem("damage", heroTarget + " recebeu " + amount + " de dano.");
        if (type === "creature_death") return renderSummaryItem("death", cardName + " foi derrotado.");
        if (type === "keyword_guarded") return renderSummaryItem("keyword", "Guarded reduziu " + amount + " de dano.");
        if (type === "keyword_focused") return renderSummaryItem("keyword", "Focused gerou " + amount + " de Ambition.");
        if (type === "round_end") return renderSummaryItem("end", "Rodada encerrada.");

        return renderSummaryItem("event", str(event.message, "Evento da rodada."));
    }

    function renderRoundSummary(state) {
        const panel = document.getElementById("az48-round-summary");
        if (!panel) return;

        const events = getRoundCombatLog(state);
        const title = '<strong class="az48-summary-title">Round Summary</strong>';

        if (!events.length) {
            panel.innerHTML = [
                '<div class="az48-summary-header">',
                title,
                '<p class="az48-summary-empty">A resolução da rodada aparecerá aqui.</p>',
                '</div>',
                '<ol class="az48-summary-list" aria-label="Round Summary events"></ol>',
            ].join("");
            return;
        }

        panel.innerHTML = [
            '<div class="az48-summary-header">',
            title,
            '</div>',
            '<ol class="az48-summary-list" aria-label="Round Summary events">',
            events.map(renderCombatEvent).join(""),
            '</ol>',
        ].join("");

        const list = panel.querySelector(".az48-summary-list");
        if (list) list.scrollTop = list.scrollHeight;
    }

    function eventSide(value) {
        const side = str(value || "").toLowerCase();
        if (["player", "me", "self", "you"].includes(side)) return "me";
        if (["opponent", "enemy", "bot"].includes(side)) return "enemy";
        return "";
    }

    function eventRefSide(ref, fallback = "") {
        if (ref && typeof ref === "object") return eventSide(ref.side || fallback);
        return eventSide(fallback);
    }

    function eventLane(event) {
        const lane = str((event && event.lane) || "").toLowerCase();
        return ["left", "center", "right"].includes(lane) ? lane : "";
    }

    function feedbackKey(side, lane) {
        return side && lane ? side + ":" + lane : "";
    }

    function combatFeedbackFromState(state) {
        const feedback = {
            cardDamage: new Set(),
            cardDeath: new Set(),
            lanes: new Set(),
            heroDamage: new Set(),
        };

        getRoundCombatLog(state).forEach((event) => {
            const type = str(event && (event.type || event.kind) || "").toLowerCase();
            const lane = eventLane(event);

            if (lane && ["lane_attack", "direct_attack", "creature_damage", "hero_damage", "creature_death"].includes(type)) {
                feedback.lanes.add(lane);
            }

            if (type === "creature_damage") {
                const side = eventRefSide(event.defender, event.target_side || event.side);
                const key = feedbackKey(side, lane);
                if (key) feedback.cardDamage.add(key);
            }

            if (type === "creature_death") {
                const side = eventSide(event.side || event.target_side);
                const key = feedbackKey(side, lane);
                if (key) feedback.cardDeath.add(key);
            }

            if (type === "hero_damage") {
                const side = eventSide(event.target_side || event.target || event.side);
                if (side) feedback.heroDamage.add(side);
            }
        });

        return feedback;
    }

    function feedbackClassesForLane(feedback, side, lane) {
        const classes = [];
        const key = feedbackKey(side, lane);

        if (feedback && feedback.lanes && feedback.lanes.has(lane)) classes.push("az48-lane-resolved");
        if (feedback && feedback.cardDamage && feedback.cardDamage.has(key)) classes.push("az48-card-damaged");
        if (feedback && feedback.cardDeath && feedback.cardDeath.has(key)) classes.push("az48-card-defeated");

        return classes.join(" ");
    }

    function cardStateMap(payload) {
        const legal = (payload && payload.legal_actions) || {};
        const map = new Map();
        arr(legal.card_states).forEach((state) => {
            if (state && state.id) map.set(String(state.id), state);
        });
        return map;
    }

    function selectedHandEntry(id) {
        const hand = arr((latestState && latestState.me && latestState.me.hand) || []);
        const index = hand.findIndex((card, cardIndex) => normalizeCard(card, cardIndex).id === String(id));
        if (index < 0) return null;
        return { raw: hand[index], card: normalizeCard(hand[index], index), index };
    }

    function selectedHandCard() {
        if (!selectedCardId) return null;
        return selectedHandEntry(selectedCardId);
    }

    function allKnownCards(payload) {
        payload = payload || latestState || {};
        const me = payload.me || {};
        const enemy = payload.enemy || {};
        const meField = normalizeField(me.field);
        const enemyField = normalizeField(enemy.field);

        return arr(me.hand)
            .concat(arr(enemy.hand))
            .concat([meField.lanes.left, meField.lanes.center, meField.lanes.right])
            .concat([enemyField.lanes.left, enemyField.lanes.center, enemyField.lanes.right])
            .filter(Boolean);
    }

    function findKnownCardById(id, payload) {
        const cardId = str(id || "");
        if (!cardId) return null;

        return allKnownCards(payload).find((card, index) => normalizeCard(card, index).id === cardId) || null;
    }

    function setCardDetailFromElement(cardEl) {
        if (!cardEl) return;
        previewCardId = cardEl.dataset.cardId || "";
        detailCardSnapshot = findKnownCardById(previewCardId) || detailCardSnapshot;
        if (latestState) renderClarity(latestState);
    }

    function clearSelection() {
        selectedCardId = null;
        selectionMode = "";
        document.body.classList.remove("az48-selecting-lane", "az48-selecting-target");
    }

    function setSelection(entry, mode) {
        selectedCardId = entry.card.id;
        selectionMode = mode;
        previewCardId = entry.card.id;
        detailCardSnapshot = entry.raw;
        document.body.classList.toggle("az48-selecting-lane", mode === "lane");
        document.body.classList.toggle("az48-selecting-target", mode === "target");
    }

    function legalLanes() {
        return arr(latestState && latestState.legal_actions && latestState.legal_actions.legal_lanes).map(String);
    }

    function legalTargets() {
        return arr(latestState && latestState.legal_actions && latestState.legal_actions.legal_targets).map(String);
    }

    function defaultTargetFor(card) {
        if (!card || card.isMonster) return "";
        if (String(card.kind || "").toLowerCase() === "support") return "";
        const targets = legalTargets();
        if (num(card.attack || card.stat || 0) > 0 && targets.includes("enemy_hero")) return "enemy_hero";
        if (targets.includes("self")) return "self";
        return targets[0] || "";
    }

    function needsTargetSelection(card) {
        if (!card || card.isMonster) return false;
        if (String(card.kind || "").toLowerCase() === "support") return false;
        return legalTargets().length > 1;
    }

    function findPreviewCard(payload, playable) {
        const hand = arr(payload && payload.me && payload.me.hand);

        if (detailCardSnapshot) {
            const normalized = normalizeCard(detailCardSnapshot);
            if (!previewCardId || normalized.id === String(previewCardId)) return detailCardSnapshot;
        }

        if (previewCardId) {
            const selected = findKnownCardById(previewCardId, payload);
            if (selected) return selected;
        }

        if (!hand.length) return null;

        const playableSet = new Set(arr(playable).map(String));
        return hand.find((card, index) => playableSet.has(normalizeCard(card, index).id)) || hand[0];
    }

    function keywordDescription(keyword) {
        const key = str(keyword || "").toLowerCase();
        if (key === "guarded") return "Guarded: reduces incoming damage when the server resolves it.";
        if (key === "focused") return "Focused: generates Ambition when the server resolves it.";
        return str(keyword || "Keyword") + ": keyword effect resolved by the server.";
    }

    function renderCardDetailStats(card) {
        const el = document.getElementById("az48-card-detail-stats");
        if (!el) return;

        if (!card) {
            el.innerHTML = "";
            return;
        }

        const c = normalizeCard(card);
        const rows = [
            ["Cost", c.cost],
            ["Type", c.type],
            ["Element", c.element || "Neutral"],
        ];

        if (c.isMonster) {
            rows.push(["ATK", c.attack || c.stat || 0]);
            rows.push(["HP", (c.currentHp || 0) + "/" + (c.maxHp || 0)]);
        } else {
            rows.push([c.statLabel || "Value", c.stat || 0]);
        }

        el.innerHTML = rows.map((row) => {
            return '<span><b>' + esc(row[0]) + '</b>' + esc(row[1]) + '</span>';
        }).join("");
    }

    function renderCardKeywords(card) {
        const el = document.getElementById("az48-card-keyword-lines");
        if (!el) return;

        if (!card) {
            el.innerHTML = "";
            return;
        }

        const c = normalizeCard(card);
        const keywords = arr(c.keywords).length ? arr(c.keywords) : arr(c.keywordText);

        if (!keywords.length) {
            el.innerHTML = '<li>No keywords.</li>';
            return;
        }

        el.innerHTML = keywords.map((keyword) => '<li>' + esc(keywordDescription(keyword)) + '</li>').join("");
    }

    function renderCardPreview(payload, playable) {
        const nameEl = document.getElementById("az48-card-preview-name");
        const textEl = document.getElementById("az48-card-preview-text");
        if (!nameEl || !textEl) return;

        const card = findPreviewCard(payload, playable);
        if (!card) {
            nameEl.textContent = "No cards in hand";
            textEl.textContent = emptyHandMessage(payload, payload.legal_actions || {});
            renderCardDetailStats(null);
            renderCardKeywords(null);
            return;
        }

        const normalized = normalizeCard(card);
        const states = cardStateMap(payload);
        const cardState = states.get(String(normalized.id)) || {};
        nameEl.textContent = normalized.name;
        textEl.textContent = cardState.disabled_reason || normalized.preview || normalized.effect || "No effect preview.";
        renderCardDetailStats(card);
        renderCardKeywords(card);
    }

    function renderClarity(payload) {
        ensureClarityPanel();

        const help = payload.help || {};
        const preview = payload.enemy_preview || {};
        const summary = payload.round_summary || {};
        const turn = payload.turn || {};
        const legal = payload.legal_actions || {};
        const uiStep = getArenaUiStep(payload);
        const copy = uiCopyForStep(uiStep, payload);

        setList("az48-help-lines", help.turn_order || [
            "1. Choose Strike, Guard or Focus.",
            "2. Play one card if you can.",
            "3. Press Ready to resolve combat."
        ]);

        const nextAction = document.getElementById("az48-next-action");
        const turnHint = document.getElementById("az48-turn-hint");

        if (nextAction) {
            nextAction.textContent = copy.title || str(legal.primary_action || turn.primary_action || "choose").replaceAll("_", " ");
        }

        if (turnHint) {
            const enemyText = preview.message ? " Enemy: " + preview.message : "";
            turnHint.textContent = str(copy.hint || turn.prompt || legal.prompt || payload.message || "Choose your next action.") + enemyText;
        }

        const result = document.getElementById("az48-round-result");
        if (result) result.textContent = summary.short_result || "Current Round";

        renderEvents(payload);
        renderCardPreview(payload, legal.playable_card_ids || []);
        renderStepList(uiStep);
        updateActionButtons(uiStep);
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

        if (selectedCardId && !hand.some((card, index) => normalizeCard(card, index).id === String(selectedCardId))) {
            clearSelection();
        }

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
        renderRoundSummary(state);

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
        document.body.classList.toggle("az48-me-ready", Boolean(me.ready));
        document.body.classList.toggle("az48-enemy-ready", Boolean(enemy.ready));
        document.body.dataset.az48Step = str((state.turn && state.turn.step) || phase);
        document.body.dataset.az48PrimaryAction = str(legal.primary_action || "");
        document.body.dataset.az48UiStep = getArenaUiStep(state);
        document.body.dataset.az48PlayerIntent = slug(me.intent || "none", "none");

        text("az48-mode", str(state.mode || "training"));
        text("az48-round", num(state.round || 1, 1));
        text("az48-phase", phase);
        text("az48-message", str(state.message || "Choose your action."));

        text("az48-me-name", str(me.name || "You"));
        text("az48-me-hp", me.hp === 0 ? 0 : num(me.hp || 28, 28));
        text("az48-me-energy", num(me.energy || 0));
        text("az48-me-max-energy", num(me.max_energy || me.energy || 0));
        text("az48-me-ambition", num(me.ambition || 0));
        text("az48-me-intent", intentLabel(me.intent, "Choose"));
        text("my-deck", num(me.deck_count || 0));
        text("my-ready", me.ready ? "Ready" : "Not ready");

        text("az48-enemy-name", str(enemy.name || "Opponent"));
        text("az48-enemy-hp", enemy.hp === 0 ? 0 : num(enemy.hp || 28, 28));
        text("az48-enemy-energy", num(enemy.energy || 0));
        text("az48-enemy-max-energy", num(enemy.max_energy || enemy.energy || 0));
        text("az48-enemy-hand", num(enemy.hand_count || 0));
        text("az48-enemy-status", opponentStatusLabel(state, enemy, state.enemy_preview || {}));
        text("enemy-deck", num(enemy.deck_count || 0));
        text("enemy-ready", enemy.ready ? "Ready" : "Not ready");

        const meField = normalizeField(me.field);
        const enemyField = normalizeField(enemy.field);
        const legalLaneSet = new Set(selectionMode === "lane" ? legalLanes() : []);
        const combatFeedback = combatFeedbackFromState(state);
        document.body.classList.toggle("az48-me-hero-hit", combatFeedback.heroDamage.has("me"));
        document.body.classList.toggle("az48-enemy-hero-hit", combatFeedback.heroDamage.has("enemy"));

        const enemyFieldEl = $("az48-enemy-field");
        if (enemyFieldEl) {
            enemyFieldEl.innerHTML = [
                fieldCard(enemyField.lanes.left, "Enemy Left", "enemy", "left", false, feedbackClassesForLane(combatFeedback, "enemy", "left")),
                fieldCard(enemyField.lanes.center, "Enemy Center", "enemy", "center", false, feedbackClassesForLane(combatFeedback, "enemy", "center")),
                fieldCard(enemyField.lanes.right, "Enemy Right", "enemy", "right", false, feedbackClassesForLane(combatFeedback, "enemy", "right")),
            ].join("");
        }

        const meFieldEl = $("az48-me-field");
        if (meFieldEl) {
            meFieldEl.innerHTML = [
                fieldCard(meField.lanes.left, "Left Lane", "me", "left", legalLaneSet.has("left"), feedbackClassesForLane(combatFeedback, "me", "left")),
                fieldCard(meField.lanes.center, "Center Lane", "me", "center", legalLaneSet.has("center"), feedbackClassesForLane(combatFeedback, "me", "center")),
                fieldCard(meField.lanes.right, "Right Lane", "me", "right", legalLaneSet.has("right"), feedbackClassesForLane(combatFeedback, "me", "right")),
            ].join("");
        }

        const targetSet = new Set(selectionMode === "target" ? legalTargets() : []);
        document.querySelectorAll("[data-az48-target]").forEach((el) => {
            const target = el.getAttribute("data-az48-target") || "";
            el.classList.toggle("is-legal-target", targetSet.has(target));
        });

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
                        selected: selectedCardId === String(c.id),
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

    function emitCommand(action, payload) {
        commandSeq += 1;
        const legacyEvent = LEGACY_EVENT_BY_ACTION[action] || "";
        const command = {
            schema: ARENA_COMMAND_SCHEMA,
            action,
            client_command_id: "az48-" + commandSeq,
            legacy_event: legacyEvent,
            ...(payload || {}),
        };
        return emit("arena_command_v1", command);
    }

    function startTraining() {
        setMessage("Starting training...");
        setServerError("");
        emitCommand("start_training", {});
    }

    function requestState() {
        emitCommand("request_state", {});
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
        setServerError("");
        clearSelection();
        if (emitCommand("set_intent", { intent })) {
            playSound("intent", { element: intent });
        }
    }

    function ready() {
        if (matchIsFinished()) {
            setMessage("Match finished. Start a new training match or go back to Arena.");
            return;
        }

        setMessage("Ready sent.");
        setServerError("");
        clearSelection();
        if (emitCommand("ready", {})) {
            playSound("ready");
        }
    }

    function playCard(id, choice = {}) {
        if (matchIsFinished()) {
            setMessage("Match finished. Start a new training match or go back to Arena.");
            return;
        }

        const entry = selectedHandEntry(id);

        if (!entry) {
            setMessage("Card is no longer in hand.");
            clearSelection();
            return;
        }

        const card = entry.card;
        const legal = (latestState && latestState.legal_actions) || {};
        const playable = arr(legal.playable_card_ids).map(String);

        if (!playable.includes(String(card.id))) {
            const states = cardStateMap(latestState);
            const cardState = states.get(String(card.id)) || {};
            setMessage(cardState.disabled_reason || "This card cannot be played now.");
            clearSelection();
            return;
        }

        const payload = { card_id: id, card_index: entry.index };
        if (card.isMonster) {
            const legalLaneList = legalLanes();
            if (!legalLaneList.length) {
                setMessage("No empty lane available.");
                clearSelection();
                return;
            }

            if (!choice.lane) {
                setSelection(entry, "lane");
                setMessage("Choose an empty lane for " + card.name + ".");
                if (latestState) render(latestState);
                return;
            }

            if (!legalLaneList.includes(String(choice.lane))) {
                setMessage("That lane is not available.");
                return;
            }

            payload.lane = String(choice.lane);
        } else if (needsTargetSelection(card) && !choice.target) {
            setSelection(entry, "target");
            setMessage("Choose a target for " + card.name + ".");
            if (latestState) render(latestState);
            return;
        } else {
            payload.target = choice.target || defaultTargetFor(card);
        }

        setMessage("Playing card...");
        setServerError("");
        if (emitCommand("play_card", payload)) {
            clearSelection();
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
            setServerError("Socket connection error. Check your connection and try again.");
            console.error("[Ambitionz V51] connect_error", error);
        });

        socket.on("disconnect", () => {
            setMessage("Disconnected. Reconnecting...");
            setServerError("Disconnected. Reconnecting...");
        });

        socket.on("az48_state", (payload) => {
            console.debug("[Ambitionz V51 canonical]", payload);
            setServerError("");
            render(payload);
        });

        socket.on("arena_state_update", (payload) => {
            if (isCanonical(payload)) {
                setServerError("");
                render(payload);
            }
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
            setServerError(message);
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

            const laneSlot = event.target.closest("[data-az48-lane]");
            if (laneSlot && selectionMode === "lane" && laneSlot.classList.contains("is-legal-lane")) {
                event.preventDefault();
                const entry = selectedHandCard();
                if (!entry) {
                    clearSelection();
                    setMessage("Select a card first.");
                    return;
                }
                playCard(entry.card.id, { lane: laneSlot.getAttribute("data-az48-lane") });
                return;
            }

            const targetSlot = event.target.closest("[data-az48-target]");
            if (targetSlot && selectionMode === "target") {
                event.preventDefault();
                const entry = selectedHandCard();
                if (!entry) {
                    clearSelection();
                    setMessage("Select a card first.");
                    return;
                }
                playCard(entry.card.id, { target: targetSlot.getAttribute("data-az48-target") });
                return;
            }

            const fieldDetailCard = event.target.closest("#az48-me-field .az48-card[data-card-id], #az48-enemy-field .az48-card[data-card-id]");
            if (fieldDetailCard) {
                event.preventDefault();
                setCardDetailFromElement(fieldDetailCard);
                setMessage("Inspecting " + str(fieldDetailCard.querySelector(".az48-name") && fieldDetailCard.querySelector(".az48-name").textContent, "card") + ".");
                return;
            }

            const card = event.target.closest("#az48-hand .az48-card[data-card-id], #hand .az48-card[data-card-id]");
            if (card) {
                event.preventDefault();
                setCardDetailFromElement(card);

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
            const card = event.target.closest("#az48-hand .az48-card[data-card-id], #hand .az48-card[data-card-id], #az48-me-field .az48-card[data-card-id], #az48-enemy-field .az48-card[data-card-id]");
            if (!card) return;
            setCardDetailFromElement(card);
        });

        document.addEventListener("focusin", (event) => {
            const card = event.target.closest("#az48-hand .az48-card[data-card-id], #hand .az48-card[data-card-id], #az48-me-field .az48-card[data-card-id], #az48-enemy-field .az48-card[data-card-id]");
            if (!card) return;
            setCardDetailFromElement(card);
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
            getRoundCombatLog,
            renderRoundSummary,
            renderCombatEvent,
            renderSummaryItem,
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
