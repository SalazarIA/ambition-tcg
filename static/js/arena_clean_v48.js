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
    let pendingCommand = null;
    let pendingCommandTimer = null;
    let latestStateOrderKey = -1;
    let latestPostMatchSummary = null;
    let latestGameOverResult = "";
    let lastCombatAudioSignature = "";
    let lastGameOverAudioResult = "";
    let reportedTrainingResult = false;
    const pulseTimers = {};

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
    const COMMAND_TIMEOUT_MS = 2600;
    const FIRST_PLAYER_STORAGE_KEY = "ambitionz_first_battle_flow_seen_v1";
    const TRAINING_DIFFICULTY_COPY = {
        easy: "Easy: learning bot with a more tolerant practice rhythm.",
        normal: "Normal: standard competitive beta training.",
        hard: "Hard: aggressive tactical pressure for sharper testing.",
    };

    const PAGE_KIND = document.body ? document.body.getAttribute("data-page-kind") : "arena";
    const CAMPAIGN_CONTEXT = window.AMBITIONZ_CAMPAIGN_CONTEXT || {};
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

    function trackRetentionEvent(eventKey, metadata) {
        try {
            if (window.AmbitionzRetention && typeof window.AmbitionzRetention.track === "function") {
                window.AmbitionzRetention.track(eventKey, metadata || {});
                return;
            }

            if (!window.fetch) return;

            fetch("/api/retention/event", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    event_key: eventKey,
                    page: window.location.pathname,
                    metadata: metadata || {},
                }),
            }).catch(function () {});
        } catch (err) {}
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

    function restartBodyPulse(className, duration) {
        if (!document.body || !className) return;
        const timeout = duration || 760;
        document.body.classList.remove(className);
        void document.body.offsetWidth;
        document.body.classList.add(className);
        window.clearTimeout(pulseTimers[className]);
        pulseTimers[className] = window.setTimeout(() => {
            if (document.body) document.body.classList.remove(className);
        }, timeout);
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

    function isTrainingLikePage() {
        return PAGE_KIND === "training" || PAGE_KIND === "campaign";
    }

    function selectedTrainingDifficulty() {
        if (CAMPAIGN_CONTEXT && CAMPAIGN_CONTEXT.difficulty) {
            return str(CAMPAIGN_CONTEXT.difficulty, "normal").toLowerCase();
        }

        const checked = document.querySelector('input[name="training_difficulty"]:checked');
        const value = str(checked && checked.value, "normal").toLowerCase();
        return TRAINING_DIFFICULTY_COPY[value] ? value : "normal";
    }

    function updateTrainingDifficultyUi() {
        const difficulty = selectedTrainingDifficulty();
        const label = document.getElementById("az48-training-difficulty-label");
        if (label) label.textContent = (difficulty.slice(0, 1).toUpperCase() + difficulty.slice(1)) + (PAGE_KIND === "campaign" ? " Campaign" : " Training");

        document.querySelectorAll("[data-training-difficulty]").forEach((item) => {
            item.classList.toggle("is-active", item.getAttribute("data-training-difficulty") === difficulty);
        });

        if (document.body) document.body.dataset.trainingDifficulty = difficulty;
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

    function phaseRank(payload) {
        const phase = str(payload && (payload.phase || payload.raw_phase), "").toLowerCase();
        const primary = str(payload && payload.legal_actions && payload.legal_actions.primary_action, "").toLowerCase();
        const rankByPhase = {
            start: 0,
            created: 0,
            intent: 1,
            choose_action: 1,
            card: 2,
            ready: 3,
            waiting: 4,
            finished: 6,
        };
        if (payload && payload.winner) return 6;
        if (primary === "choose_intent") return 1;
        if (primary === "play_card") return 2;
        if (primary === "ready") return 3;
        if (primary === "wait") return 4;
        return rankByPhase[phase] === undefined ? 0 : rankByPhase[phase];
    }

    function stateOrderKey(payload) {
        return (num(payload && payload.round, 0) * 10) + phaseRank(payload);
    }

    function isStalePayload(payload) {
        if (!latestState || !isCanonical(payload)) return false;
        if (payload.winner) return false;
        const nextKey = stateOrderKey(payload);
        return nextKey < latestStateOrderKey;
    }

    function actionIsCommand(action) {
        return ["start_training", "set_intent", "play_card", "ready", "unleash"].includes(String(action || ""));
    }

    function setCommandPending(command) {
        if (!command || !actionIsCommand(command.action)) return;
        pendingCommand = command;
        if (document.body) document.body.classList.add("az48-command-pending");
        window.clearTimeout(pendingCommandTimer);
        pendingCommandTimer = window.setTimeout(() => {
            pendingCommand = null;
            if (document.body) document.body.classList.remove("az48-command-pending");
            setServerError("Still syncing. Requesting the latest battle state.");
            requestState();
        }, COMMAND_TIMEOUT_MS);
    }

    function clearCommandPending() {
        pendingCommand = null;
        window.clearTimeout(pendingCommandTimer);
        pendingCommandTimer = null;
        if (document.body) document.body.classList.remove("az48-command-pending");
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
            faction: str(card.faction || factionForElement(card.element || "Neutral")),
            rarity: str(card.rarity || "Common"),
            sigil: str(card.sigil || "None"),
            role: str(card.role || card.kind || type),
            cost: num(firstValue(card.cost, card.energy_cost, card.energyCost), 1),
            stat,
            statLabel: str(card.combat_label || (isMonster ? "PWR" : "VAL")),
            attack,
            damage: num(firstValue(card.damage, card.dmg, !isMonster ? card.power : 0), 0),
            shield: num(firstValue(card.shield, card.shd), 0),
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
            effectSummary: str(card.effect_summary || card.effect || card.description || ""),
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
            ? '<div class="az48-card-stats"><span class="az48-card-stat-pair az48-stat-attack"><b>ATK</b>' + esc(c.attack || c.stat || 0) + '</span><span class="az48-card-stat-pair az48-stat-health"><b>HP</b>' + esc(c.currentHp || 0) + '/' + esc(c.maxHp || 0) + '</span></div>'
            : '<div class="az48-card-stats"><span class="az48-card-stat-pair"><b>' + esc(c.statLabel || "VAL") + '</b>' + esc(c.stat || 0) + '</span><span class="az48-card-stat-pair"><b>ELM</b>' + esc(c.element || "Neutral") + '</span></div>';
        const laneData = options.lane ? ' data-az48-lane="' + esc(options.lane) + '"' : "";
        const style = [
            "--az-card-primary:" + esc(colors.primary || "#9ea7b7"),
            "--az-card-secondary:" + esc(colors.secondary || "#d9deea"),
            "--az-card-accent:" + esc(colors.accent || "#f4f7ff"),
            "--az-card-art-image:url('" + esc(c.artUrl || "/static/img/cards/elemental/neutral.svg") + "')",
        ].join(";");

        const disabledReason = friendlyDisabledReason(options.disabledReason || c.disabledReason || "");
        const title = disabledReason || c.preview || c.effect || c.name;

        return [
            '<button type="button" class="az48-card az48-card-v2 az48-card-frame-premium-v1 ' + typeClass + ' ' + elementClass + ' ' + rarityClass + playable + (options.playable ? " is-playable az48-playable" : "") + locked + field + selected + laneSlot + legalLane + feedbackClass + '" data-card-id="' + esc(c.id) + '"' + laneData + ' data-card-type="' + esc(c.type) + '" data-element="' + esc(c.element || "Neutral") + '" data-rarity="' + esc(c.rarity || "Common") + '" data-card-preview="' + esc(c.preview || c.effect || "") + '" data-disabled-reason="' + esc(disabledReason) + '" aria-pressed="' + (options.selected ? "true" : "false") + '" title="' + esc(title) + '" style="' + style + '">',
            '<span class="az48-card-sheen" aria-hidden="true"></span>',
            '<span class="az48-cost">E ' + esc(c.cost) + '</span>',
            '<span class="az48-rarity">' + esc(c.rarity) + '</span>',
            '<span class="az48-card-element-mark">' + esc((c.element || "N").slice(0, 1).toUpperCase()) + '</span>',
            '<div class="az48-art"><span class="az48-art-image" aria-hidden="true"></span><span class="az48-art-glow" aria-hidden="true"></span></div>',
            '<strong class="az48-name">' + esc(c.name) + '</strong>',
            stats,
            '<p class="az48-effect">' + esc(c.effect || c.role || c.kind || "") + '</p>',
            '<p class="az48-card-preview-line">' + esc(c.preview || "") + '</p>',
            '<div class="az48-tags"><span>' + esc(c.element || "Neutral") + '</span><span>' + esc(c.type) + '</span>' + keywordTags.map((keyword) => '<span class="az48-keyword-chip">' + esc(keyword) + '</span>').join("") + '</div>',
            '<span class="az48-power">' + esc(c.statLabel) + ' ' + esc(c.stat) + '</span>',
            '</button>'
        ].join("");
    }

    function fieldCard(card, label, owner, lane, legalLane, feedbackClass = "") {
        const feedback = feedbackClass ? " " + feedbackClass : "";

        if (!card) {
            const hint = legalLane ? "Playable lane" : "Empty lane";
            return '<button type="button" class="az48-slot az48-lane-slot' + (legalLane ? " is-legal-lane" : "") + feedback + '" data-az48-owner="' + esc(owner || "") + '" data-az48-lane="' + esc(lane || "") + '"><span class="az48-slot-label">' + esc(label) + '</span><small>' + esc(hint) + '</small></button>';
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
        if (enemy && enemy.ready) return isTrainingLikePage() ? "Bot ready" : "Ready";
        if (enemy && enemy.intent) return isTrainingLikePage() ? "Bot chose " + intentLabel(enemy.intent, "Intent") : intentLabel(enemy.intent, "Intent set");
        if (preview && preview.ready) return isTrainingLikePage() ? "Bot ready" : "Ready";
        if (preview && preview.intent) return isTrainingLikePage() ? "Bot chose " + intentLabel(preview.intent, "Intent") : intentLabel(preview.intent, "Intent set");
        if (preview && preview.message) return str(preview.message);

        return isTrainingLikePage() ? "Bot thinking" : "Choosing";
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
            '<div class="az48-clarity-card az48-highlight-card">',
            '<span>Battle Highlights</span>',
            '<strong id="az48-highlight-headline">No clash yet</strong>',
            '<dl class="az48-highlight-grid" id="az48-highlight-grid"></dl>',
            '<p id="az48-highlight-next">Choose your next line.</p>',
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
                title: PAGE_KIND === "campaign" ? "1. Start Chapter" : "1. Start Training",
                hint: PAGE_KIND === "campaign" ? "Press Start to enter this campaign-marked duel." : "Press Start to draw your opening hand.",
                button: PAGE_KIND === "campaign" ? "Start Chapter" : "Start Training",
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
        setButtonContent("az48-start", PAGE_KIND === "campaign" ? "Start Chapter" : "Start Training", "Draw Hand");
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

    function syncActionControls(step, legal) {
        legal = legal || {};
        const hasPendingCommand = Boolean(pendingCommand);

        const available = {
            "az48-start": !hasPendingCommand && step === "start" && Boolean(legal.can_start || legal.show_start),
            "az48-floating-start": !hasPendingCommand && step === "start" && isTrainingLikePage(),
            "az48-strike": !hasPendingCommand && step === "choose_intent",
            "az48-guard": !hasPendingCommand && step === "choose_intent",
            "az48-focus": !hasPendingCommand && step === "choose_intent",
            "az48-ready": !hasPendingCommand && ["choose_card", "ready"].includes(step) && Boolean(legal.can_ready || legal.show_ready),
        };

        Object.entries(available).forEach(([id, isAvailable]) => {
            const button = document.getElementById(id);
            if (!button) return;

            button.disabled = !isAvailable;
            button.classList.toggle("is-primary-action", isAvailable);
            button.setAttribute("aria-disabled", isAvailable ? "false" : "true");
            button.dataset.az48ActionState = isAvailable ? "available" : "unavailable";
        });
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
            ["Guard", actions.Guard || "+5 shield this round."],
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

    function localBattleHighlights(payload) {
        payload = payload || {};
        const summary = payload.round_summary || {};
        const dealt = Math.max(0, num(summary.enemy_hp_before) - num(summary.enemy_hp_after));
        const taken = Math.max(0, num(summary.player_hp_before) - num(summary.player_hp_after));
        return {
            headline: dealt || taken ? ("You dealt " + dealt + " and took " + taken + ".") : "No clash resolved yet.",
            next_step: uiCopyForStep(getArenaUiStep(payload), payload).hint || "Follow the highlighted action.",
            items: [
                { key: "damage_dealt", label: "Damage dealt", value: dealt },
                { key: "damage_taken", label: "Damage taken", value: taken },
                { key: "shield_gained", label: "Shield gained", value: 0 },
                { key: "ambition_gained", label: "Ambition gained", value: 0 },
            ],
        };
    }

    function renderBattleHighlights(payload) {
        const headline = document.getElementById("az48-highlight-headline");
        const grid = document.getElementById("az48-highlight-grid");
        const next = document.getElementById("az48-highlight-next");
        if (!headline || !grid || !next) return;

        const highlights = (payload && payload.battle_highlights) || localBattleHighlights(payload);
        const items = arr(highlights.items).filter((item) => item && item.key).slice(0, 6);

        headline.textContent = str(highlights.headline || "No clash resolved yet.");
        next.textContent = str(highlights.next_step || "Follow the highlighted action.");
        grid.innerHTML = items.map((item) => {
            return '<div class="az48-highlight-item az48-highlight-' + esc(slug(item.key)) + '"><dt>' + esc(item.label || item.key) + '</dt><dd>' + esc(item.value) + '</dd></div>';
        }).join("");
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

    function renderSummaryItem(kind, text, index = 0) {
        const safeKind = slug(kind || "event", "event");
        return '<li class="az48-summary-item az48-summary-item-' + safeKind + '" style="--az48-event-index:' + esc(index) + '">' + esc(text) + '</li>';
    }

    function renderCombatEvent(event, index = 0) {
        event = event || {};
        const type = str(event.type || event.kind || "").toLowerCase();
        const amount = eventAmount(event);
        const attackerName = eventName(event.attacker_name || event.attacker, "Carta");
        const defenderName = eventName(event.defender_name || event.defender, "Carta");
        const cardName = eventName(event.card_name || event.card || event.name, "Carta");
        const targetName = eventName(event.target_name || event.target || event.defender_name || event.defender || event.name, "alvo");
        const heroTarget = eventName(event.target_name || event.target || "", event.target_side ? "herói" : "alvo");

        if (type === "round_start") return renderSummaryItem("event", "Rodada iniciada.", index);
        if (type === "round_resolve") return renderSummaryItem("event", "Resolução da rodada.", index);
        if (type === "intent_selected") return renderSummaryItem("event", str(event.message || event.text, "Intenção escolhida."), index);
        if (type === "card_played") return renderSummaryItem("played", cardName + " entrou na rodada.", index);
        if (type === "shield_gain") return renderSummaryItem("shield", "Escudo +" + amount + ".", index);
        if (type === "ambition_gain") return renderSummaryItem("ambition", "Ambition +" + amount + ".", index);
        if (type === "lane_attack") return renderSummaryItem("attack", attackerName + " atacou " + defenderName + ".", index);
        if (type === "direct_attack") return renderSummaryItem("attack", attackerName + " atacou diretamente o herói.", index);
        if (type === "creature_damage") return renderSummaryItem("damage", targetName + " recebeu " + amount + " de dano.", index);
        if (type === "hero_damage") return renderSummaryItem("damage", heroTarget + " recebeu " + amount + " de dano.", index);
        if (type === "creature_death") return renderSummaryItem("death", cardName + " foi derrotado.", index);
        if (type === "keyword_guarded") return renderSummaryItem("keyword", "Guarded reduziu " + amount + " de dano.", index);
        if (type === "keyword_focused") return renderSummaryItem("keyword", "Focused gerou " + amount + " de Ambition.", index);
        if (type === "round_end") return renderSummaryItem("end", "Rodada encerrada.", index);
        if (type === "match_finished") return renderSummaryItem("end", "Partida encerrada.", index);

        return renderSummaryItem("event", str(event.message, "Evento da rodada."), index);
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
            events.map((event, index) => renderCombatEvent(event, index)).join(""),
            '</ol>',
        ].join("");

        const list = panel.querySelector(".az48-summary-list");
        if (list) list.scrollTop = list.scrollHeight;
    }

    function resultKey(value) {
        const key = str(value || "").toLowerCase();
        if (["win", "winner", "victory", "player", "you"].includes(key)) return "win";
        if (["lose", "loss", "defeat", "opponent", "enemy", "bot"].includes(key)) return "lose";
        if (["draw", "tie"].includes(key)) return "draw";
        return "";
    }

    function trainingResultCopy(summary, state) {
        summary = summary || {};
        state = state || {};
        const summaryText = summary.summary || {};
        const key = resultKey(summary.result || latestGameOverResult || state.result || state.winner);
        const rounds = num(summary.rounds || state.round || 0);
        const mode = str(summary.mode || state.mode || "training");

        const titleByKey = {
            win: mode === "campaign" ? "Chapter Cleared" : "Victory",
            lose: mode === "campaign" ? "Chapter Attempted" : "Defeat",
            draw: mode === "campaign" ? "Chapter Draw" : "Draw",
        };
        const messageByKey = {
            win: mode === "campaign" ? "Campaign progress recorded." : "You won the training duel.",
            lose: mode === "campaign" ? "Campaign attempt recorded. Tune and return." : "You were defeated in training.",
            draw: mode === "campaign" ? "Campaign chapter ended in a draw and was recorded." : "The training duel ended in a draw.",
        };

        return {
            title: str(summaryText.title || titleByKey[key] || "Training Complete"),
            message: str(summaryText.message || state.message || messageByKey[key] || "Training match finished."),
            rounds,
            mode,
            key,
        };
    }

    function estimatedTrainingXp(key) {
        if (key === "win") return 70;
        if (key === "lose") return 35;
        if (key === "draw") return 45;
        return 35;
    }

    function resultReason(summary, state, copy) {
        const highlights = (state && state.battle_highlights) || {};
        const items = arr(highlights.items);
        const valueFor = (key) => {
            const found = items.find((item) => item && item.key === key);
            return num(found && found.value, 0);
        };
        const dealt = valueFor("damage_dealt");
        const taken = valueFor("damage_taken");
        const shield = valueFor("shield_gained");

        if (summary && summary.campaign_result) {
            return "Campaign chapter result recorded.";
        }
        if (copy.key === "win" && dealt >= taken + 4) {
            return "You won by keeping pressure ahead of incoming damage.";
        }
        if (copy.key === "win" && shield > 0) {
            return "Your defense bought enough time to close the match.";
        }
        if (copy.key === "lose" && taken > dealt) {
            return "You suffered more direct pressure than you returned.";
        }
        if (copy.key === "lose") {
            return "The enemy survived the final exchange. Tune your intent timing and deck line.";
        }
        if (copy.key === "draw") {
            return "Both sides ended close. One cleaner lane or Ready timing can swing it.";
        }
        return "Review the reward summary and choose the next battle step.";
    }

    function updateResultActionLinks(summary) {
        const actions = (summary && summary.next_actions) || {};
        const mapping = {
            primary: actions.primary,
            campaign: actions.campaign,
            collection: actions.collection,
            deck: actions.deck,
            history: actions.history,
            missions: actions.missions || "/missions",
            shop: actions.shop || "/shop",
            progression: actions.progression || "/progression",
            menu: actions.menu || "/",
        };

        Object.entries(mapping).forEach(([key, href]) => {
            const link = document.querySelector('[data-result-action="' + key + '"]');
            if (link && href) link.setAttribute("href", href);
        });
    }

    function renderResultNextBestAction(summary) {
        const panel = document.getElementById("az48-result-next-best");
        if (!panel) return;

        const action = (summary && summary.next_best_action) || {};
        const href = str(action.url || "");
        const title = str(action.title || "");
        const description = str(action.description || "");
        const label = str(action.label || "");

        if (!href && !title && !description && !label) {
            panel.hidden = true;
            panel.dataset.reason = "";
            return;
        }

        const titleEl = document.getElementById("az48-result-next-title");
        const copyEl = document.getElementById("az48-result-next-copy");
        const linkEl = document.getElementById("az48-result-next-link");

        if (titleEl) titleEl.textContent = title || "Choose your next step.";
        if (copyEl) copyEl.textContent = description || "Review rewards, tune your deck or play another Training match.";
        if (linkEl) {
            linkEl.textContent = label || "Continue";
            linkEl.setAttribute("href", href || "/training");
        }

        panel.dataset.reason = str(action.reason || action.kind || "next_step");
        panel.hidden = false;
    }

    function renderResultMissions(summary) {
        const el = document.getElementById("az48-result-missions");
        if (!el) return;

        const missions = arr(summary && summary.mission_progress).filter(Boolean);
        if (!missions.length) {
            el.hidden = true;
            el.innerHTML = "";
            return;
        }

        el.innerHTML = missions.slice(0, 3).map((mission) => {
            const name = str(mission.name || mission.title || mission.mission_name || mission.mission_key || mission.mission_id || mission.id || "Mission progress");
            const target = firstValue(mission.target_count, mission.target);
            const progress = mission.progress !== undefined && target !== undefined
                ? " " + num(mission.progress) + "/" + num(target)
                : "";
            const status = mission.is_complete || mission.complete || mission.completed ? " complete" : " progressed";
            return '<li><b>' + esc(name) + '</b><span>' + esc(progress + status) + '</span></li>';
        }).join("");
        el.hidden = false;
    }

    function renderResultProgress(copy, rewards, summary) {
        const panel = document.getElementById("az48-result-progress");
        const label = document.getElementById("az48-result-progress-label");
        const value = document.getElementById("az48-result-progress-value");
        const fill = document.getElementById("az48-result-progress-fill");

        if (!panel || !label || !value || !fill) return;

        summary = summary || {};
        const xpValue = firstValue(summary.xp_gained, rewards && rewards.xp);
        const hasServerXp = xpValue !== undefined && xpValue !== null && xpValue !== "";
        const xp = hasServerXp ? num(xpValue) : estimatedTrainingXp(copy.key);
        const serverPercent = summary.level_progress_percent !== undefined ? num(summary.level_progress_percent) : null;
        const percent = serverPercent !== null
            ? Math.max(0, Math.min(100, Math.round(serverPercent)))
            : Math.max(10, Math.min(100, Math.round((xp / 120) * 100)));
        const level = summary.level ? "Level " + num(summary.level, 1) + " progress" : (copy.mode === "campaign" ? "Campaign reward" : "Training reward");

        label.textContent = hasServerXp ? level : "Progress preview";
        value.textContent = hasServerXp ? ("XP +" + xp + " · " + percent + "%") : ("Estimated XP +" + xp);
        fill.style.width = percent + "%";
        panel.hidden = false;
    }

    function renderTrainingResult(state) {
        const panel = document.getElementById("az48-training-result");
        if (!panel) return;

        const phase = str((state && state.phase) || "").toLowerCase();
        const finished = phase === "finished" || Boolean(state && state.winner) || Boolean(latestGameOverResult);

        if (!isTrainingLikePage() || !finished) {
            panel.hidden = true;
            panel.classList.remove("is-visible");
            document.body.classList.remove("az48-training-finished");
            return;
        }

        const summary = latestPostMatchSummary || {};
        const copy = trainingResultCopy(summary, state);
        const titleEl = document.getElementById("az48-result-title");
        const textEl = document.getElementById("az48-result-text");
        const metaEl = document.getElementById("az48-result-meta");
        const rewardsEl = document.getElementById("az48-result-rewards");
        const rewards = summary.rewards || {};
        const rewardLines = [];

        if (titleEl) titleEl.textContent = copy.title;
        if (textEl) {
            const detail = [
                copy.message,
                copy.rounds ? ("Rounds: " + copy.rounds + ".") : "",
                copy.mode ? ("Mode: " + copy.mode + ".") : "",
            ].filter(Boolean).join(" ");
            textEl.textContent = detail;
        }

        if (metaEl) {
            const reason = resultReason(summary, state, copy);
            const meta = [
                copy.rounds ? ("Rounds " + copy.rounds) : "",
                copy.mode ? ("Mode " + copy.mode) : "",
                summary.history_id ? ("History #" + summary.history_id) : "",
                reason,
            ].filter(Boolean);
            metaEl.innerHTML = meta.map((line) => '<span>' + esc(line) + '</span>').join("");
            metaEl.hidden = meta.length === 0;
        }

        if (rewardsEl) {
            if (rewards.xp !== undefined && rewards.xp !== null) rewardLines.push("XP +" + num(rewards.xp));
            if (rewards.campaign_bonus_xp) rewardLines.push("Campaign +" + num(rewards.campaign_bonus_xp) + " XP");
            if (rewards.coins !== undefined && rewards.coins !== null) rewardLines.push("Gold +" + num(rewards.coins));
            if (summary.campaign_chapter_id) rewardLines.push("Chapter " + str(summary.campaign_chapter_id));
            if (summary.history_id) rewardLines.push("History #" + str(summary.history_id));
            if (arr(summary.mission_progress).length) rewardLines.push("Mission progress");
            rewardsEl.textContent = rewardLines.length
                ? "Reward Preview · " + rewardLines.join(" · ")
                : "";
            rewardsEl.hidden = rewardLines.length === 0;
        }

        renderResultProgress(copy, rewards, summary);
        renderResultMissions(summary);
        renderResultNextBestAction(summary);
        updateResultActionLinks(summary);

        panel.hidden = false;
        panel.classList.add("is-visible");
        panel.dataset.result = copy.key || "finished";
        document.body.classList.add("az48-training-finished");

        if (!reportedTrainingResult) {
            reportedTrainingResult = true;
            trackRetentionEvent("training_result_view", {
                result: copy.key || "finished",
                rounds: copy.rounds || 0,
                has_server_reward: Boolean(rewards && (rewards.xp !== undefined || rewards.coins !== undefined)),
            });
            trackRetentionEvent("post_match_summary_view", {
                result: copy.key || "finished",
                mode: copy.mode || PAGE_KIND,
                history_id: summary.history_id || null,
                campaign_chapter_id: summary.campaign_chapter_id || null,
            });
            if (window.AmbitionzBetaTelemetry && typeof window.AmbitionzBetaTelemetry.track === "function") {
                window.AmbitionzBetaTelemetry.track("finish_match", {
                    result: copy.key || "finished",
                    mode: copy.mode || PAGE_KIND,
                    rounds: copy.rounds || 0,
                    xp: firstValue(summary.xp_gained, rewards && rewards.xp) || 0,
                    gold: firstValue(summary.gold_gained, rewards && rewards.coins) || 0,
                }, "finish_match_result");
            }
        }
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
            cardPlayed: new Set(),
            lanes: new Set(),
            heroDamage: new Set(),
            shield: new Set(),
            ambition: new Set(),
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

            if (type === "card_played") {
                const side = eventSide(event.side || event.actor);
                if (side) feedback.cardPlayed.add(side);
            }

            if (type === "shield_gain") {
                const side = eventSide(event.side || event.actor);
                if (side) feedback.shield.add(side);
            }

            if (type === "ambition_gain") {
                const side = eventSide(event.side || event.actor);
                if (side) feedback.ambition.add(side);
            }
        });

        return feedback;
    }

    function playCombatLogFeedback(state) {
        const events = getRoundCombatLog(state);
        if (!events.length) return;

        const signature = [
            num((state && state.round) || 0),
            events.map((event) => {
                return [
                    str(event && (event.type || event.kind), ""),
                    eventLane(event),
                    eventAmount(event),
                    str(event && (event.card_name || event.attacker_name || event.defender_name || event.target_side), ""),
                ].join(":");
            }).join("|"),
        ].join("::");

        if (signature === lastCombatAudioSignature) return;
        lastCombatAudioSignature = signature;

        const hasResolve = events.some((event) => ["round_resolve", "round_end"].includes(str(event && (event.type || event.kind), "").toLowerCase()));
        const hasDamage = events.some((event) => ["creature_damage", "hero_damage", "direct_attack"].includes(str(event && (event.type || event.kind), "").toLowerCase()));
        const hasDeath = events.some((event) => str(event && (event.type || event.kind), "").toLowerCase() === "creature_death");

        if (hasResolve) playSound("roundResolve");
        if (hasDamage) window.setTimeout(() => playSound("damage"), 90);
        if (hasDeath) window.setTimeout(() => playSound("death"), 180);
    }

    function feedbackClassesForLane(feedback, side, lane) {
        const classes = [];
        const key = feedbackKey(side, lane);

        if (feedback && feedback.lanes && feedback.lanes.has(lane)) classes.push("az48-lane-resolved");
        if (feedback && feedback.cardDamage && feedback.cardDamage.has(key)) classes.push("az48-card-damaged");
        if (feedback && feedback.cardDeath && feedback.cardDeath.has(key)) classes.push("az48-card-defeated");
        if (feedback && feedback.cardPlayed && feedback.cardPlayed.has(side)) classes.push("az48-card-recently-played");

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

    function factionForElement(element) {
        const key = str(element || "").toLowerCase();
        if (key === "fire") return "Ember Court";
        if (key === "water") return "Tideborn Order";
        if (key === "earth") return "Stonebound Clan";
        if (key === "plant") return "Verdant Pact";
        if (key === "global") return "Arcane Neutral";
        return "Arcane Neutral";
    }

    function identityForElement(element) {
        const key = str(element || "").toLowerCase();
        if (key === "fire") return "Fire: pressure and damage.";
        if (key === "water") return "Water: focus, resources and light sustain.";
        if (key === "earth") return "Earth: defense and durable bodies.";
        if (key === "plant") return "Plant: control and steady growth.";
        return "Neutral: flexible arcane utility.";
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
        if (key === "shield") return "Shield: absorbs hero damage before HP is lost.";
        if (key === "ambition") return "Ambition: charges Unleash and late-round power.";
        if (key === "strike") return "Strike: offensive intent. Creatures hit harder this round.";
        if (key === "guard") return "Guard: defensive intent. Gain shield and blunt attacks.";
        if (key === "focus") return "Focus: scaling intent. Gain more Ambition.";
        if (key === "monster") return "Monster: enters a lane and fights through combat.";
        if (key === "spell") return "Spell: resolves an immediate effect.";
        if (key === "trap") return "Trap: defensive card that can add shield or counter damage.";
        if (["fire", "water", "earth", "plant", "neutral", "global"].includes(key)) return identityForElement(key);
        return str(keyword || "Keyword") + ": keyword effect resolved by the server.";
    }

    function educationTermsForCard(card, cardState) {
        const c = normalizeCard(card);
        const terms = [];
        arr(c.keywords).forEach((keyword) => terms.push(keyword));
        arr(c.keywordText).forEach((keyword) => terms.push(keyword));
        terms.push(c.type);
        if (c.element) terms.push(c.element);
        if (/shield/i.test(c.preview + " " + c.effectSummary + " " + c.effect)) terms.push("Shield");
        if (/ambition/i.test(c.preview + " " + c.effectSummary + " " + c.effect)) terms.push("Ambition");
        if (/strike/i.test(c.preview + " " + (cardState && cardState.preview || ""))) terms.push("Strike");
        if (/guard/i.test(c.preview + " " + (cardState && cardState.preview || ""))) terms.push("Guard");
        if (/focus/i.test(c.preview + " " + (cardState && cardState.preview || ""))) terms.push("Focus");

        const seen = new Set();
        return terms.filter((term) => {
            const key = str(term).toLowerCase();
            if (!key || seen.has(key)) return false;
            seen.add(key);
            return true;
        }).slice(0, 5);
    }

    function friendlyDisabledReason(reason) {
        const text = str(reason || "");
        const key = text.toLowerCase();
        if (!text) return "";
        if (key.includes("needs") && key.includes("energy")) return text.replace("Needs", "Energy required:");
        if (key.includes("choose strike")) return "Choose Strike, Guard or Focus before playing this card.";
        if (key.includes("only one card")) return "You already played one card this round.";
        if (key.includes("no empty lane")) return "All lanes are full. Use a spell or press Ready.";
        if (key.includes("ready")) return "You are already Ready. Wait for combat to resolve.";
        if (key.includes("not the card step")) return "This card can be played during the Card step.";
        if (key.includes("match finished")) return "The match is finished. Review the result panel.";
        return text;
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
            ["Faction", c.faction || factionForElement(c.element)],
            ["Role", c.role || c.sigil || "Card"],
        ];

        if (c.isMonster) {
            rows.push(["ATK", c.attack || c.stat || 0]);
            rows.push(["HP", (c.currentHp || 0) + "/" + (c.maxHp || 0)]);
        } else {
            if (c.damage) rows.push(["DMG", c.damage]);
            if (c.shield) rows.push(["SHD", c.shield]);
            if (!c.damage && !c.shield) rows.push([c.statLabel || "Value", c.stat || 0]);
        }

        el.innerHTML = rows.map((row) => {
            return '<span><b>' + esc(row[0]) + '</b>' + esc(row[1]) + '</span>';
        }).join("");
    }

    function renderCardKeywords(card, cardState) {
        const el = document.getElementById("az48-card-keyword-lines");
        if (!el) return;

        if (!card) {
            el.innerHTML = "";
            return;
        }

        const keywords = educationTermsForCard(card, cardState || {});

        if (!keywords.length) {
            el.innerHTML = '<li>No extra terms.</li>';
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
        textEl.textContent = friendlyDisabledReason(cardState.disabled_reason) || normalized.preview || normalized.effectSummary || normalized.effect || "No effect preview.";
        renderCardDetailStats(card);
        renderCardKeywords(card, cardState);
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

        renderBattleHighlights(payload);
        renderEvents(payload);
        renderCardPreview(payload, legal.playable_card_ids || []);
        renderStepList(uiStep);
        updateActionButtons(uiStep);
        syncActionControls(uiStep, legal);
    }


    function render(payload) {
        if (!isCanonical(payload)) {
            console.warn("[Ambitionz V51] ignored non-canonical state", payload);
            return;
        }

        if (isStalePayload(payload)) {
            console.warn("[Ambitionz V51] ignored stale state", payload);
            return;
        }

        const previousState = latestState;
        latestStateOrderKey = Math.max(latestStateOrderKey, stateOrderKey(payload));
        clearCommandPending();

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
        const uiStep = getArenaUiStep(state);
        const primaryAction = str(legal.primary_action || (uiStep === "choose_card" ? "play_card" : uiStep));

        if (selectedCardId && !hand.some((card, index) => normalizeCard(card, index).id === String(selectedCardId))) {
            clearSelection();
        }

        if (previousState && isCanonical(previousState)) {
            const previousMe = previousState.me || {};
            const previousEnemy = previousState.enemy || {};
            const meLostHp = num(previousMe.hp || 0) > num(me.hp || 0);
            const enemyLostHp = num(previousEnemy.hp || 0) > num(enemy.hp || 0);
            const meGainedAmbition = num(me.ambition || 0) > num(previousMe.ambition || 0);
            const handSpentCard = arr(previousMe.hand).length > hand.length;

            if ((meLostHp || enemyLostHp) && !getRoundCombatLog(state).length) {
                playSound("damage");
            }

            if (meGainedAmbition) restartBodyPulse("az48-ambition-gained", 860);
            if (handSpentCard) restartBodyPulse("az48-card-played-feedback", 720);
        }

        playCombatLogFeedback(state);

        renderClarity(state);
        renderRoundSummary(state);
        renderTrainingResult(state);

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
        document.body.dataset.az48PrimaryAction = primaryAction;
        document.body.dataset.az48ServerPrimaryAction = str(legal.primary_action || "");
        document.body.dataset.az48UiStep = uiStep;
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
        document.body.classList.toggle("az48-me-shield-gained", combatFeedback.shield.has("me"));
        document.body.classList.toggle("az48-enemy-shield-gained", combatFeedback.shield.has("enemy"));
        document.body.classList.toggle("az48-me-ambition-gained", combatFeedback.ambition.has("me"));

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
        if (pendingCommand && actionIsCommand(action)) {
            setMessage("Syncing previous action. One moment.");
            return false;
        }

        commandSeq += 1;
        const legacyEvent = LEGACY_EVENT_BY_ACTION[action] || "";
        const command = {
            schema: ARENA_COMMAND_SCHEMA,
            action,
            client_command_id: "az48-" + commandSeq,
            legacy_event: legacyEvent,
            ...(payload || {}),
        };

        if ((action === "start_training" || action === "request_state") && isTrainingLikePage() && !command.difficulty) {
            command.difficulty = selectedTrainingDifficulty();
        }

        if ((action === "start_training" || action === "request_state") && CAMPAIGN_CONTEXT && CAMPAIGN_CONTEXT.chapter_id) {
            command.campaign_chapter_id = CAMPAIGN_CONTEXT.chapter_id;
            command.campaign_title = CAMPAIGN_CONTEXT.title || "Campaign Chapter";
            command.campaign_difficulty = CAMPAIGN_CONTEXT.difficulty || "normal";
            command.campaign_reward = CAMPAIGN_CONTEXT.reward || "";
        }

        const sent = emit("arena_command_v1", command);
        if (sent) setCommandPending(command);
        return sent;
    }

    function startTraining() {
        clearCommandPending();
        latestStateOrderKey = -1;
        reportedTrainingResult = false;
        latestPostMatchSummary = null;
        latestGameOverResult = "";
        renderTrainingResult(null);
        trackRetentionEvent(PAGE_KIND === "campaign" ? "campaign_start" : "training_start_click", {
            mode: PAGE_KIND,
            source: "arena_clean_v48",
            difficulty: selectedTrainingDifficulty(),
            campaign_chapter_id: CAMPAIGN_CONTEXT && CAMPAIGN_CONTEXT.chapter_id ? CAMPAIGN_CONTEXT.chapter_id : null,
        });
        setMessage(PAGE_KIND === "campaign"
            ? "Starting campaign chapter. Draw your hand, then play through the Training flow."
            : "Starting " + selectedTrainingDifficulty() + " Training. Draw your hand, then practice intent, card, lane and Ready.");
        setServerError("");
        if (emitCommand("start_training", { difficulty: selectedTrainingDifficulty() })) {
            playSound("uiTap");
        }
    }

    function requestState() {
        emitCommand("request_state", {});
    }

    function matchIsFinished() {
        const phase = String((latestState && latestState.phase) || "").toLowerCase();
        return phase === "finished" || Boolean(latestState && latestState.winner);
    }

    function finishedActionMessage() {
        return PAGE_KIND === "training"
            ? "Training finished. Review the result, play again, or return to the menu."
            : "Match finished. Start a new match or go back to Arena.";
    }

    function setIntent(intent) {
        if (matchIsFinished()) {
            setMessage(finishedActionMessage());
            return;
        }

        setMessage("Intent set: " + intent + ". Play a highlighted card or press Ready.");
        setServerError("");
        clearSelection();
        if (emitCommand("set_intent", { intent })) {
            playSound("intent", { element: intent });
        }
    }

    function ready() {
        if (matchIsFinished()) {
            setMessage(finishedActionMessage());
            return;
        }

        setMessage("Ready sent. Resolving the round when the opponent is ready.");
        setServerError("");
        clearSelection();
        if (emitCommand("ready", {})) {
            playSound("ready");
        }
    }

    function playCard(id, choice = {}) {
        if (matchIsFinished()) {
            setMessage(finishedActionMessage());
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

        if (!choice.lane && !choice.target) {
            playSound("cardSelect", { element: card.element });
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

        latestStateOrderKey = -1;
        clearCommandPending();
        setMessage("Searching for opponent...");
        emit("join_queue", {});
    }

    function joinBotMatch() {
        latestStateOrderKey = -1;
        clearCommandPending();
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

        latestStateOrderKey = -1;
        clearCommandPending();
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
            if (hasCanonicalState) window.setTimeout(requestState, 80);
        });

        socket.on("connect_error", (error) => {
            setMessage("Socket connection error.");
            setServerError("Socket connection error. Check your connection and try again.");
            console.error("[Ambitionz V51] connect_error", error);
        });

        socket.on("disconnect", () => {
            clearCommandPending();
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
            clearCommandPending();
            const message = payload && payload.message ? payload.message : "Action failed.";
            setMessage(message);
            setServerError(message);
            appendLog(message);
        });

        socket.on("game_over", (payload) => {
            latestGameOverResult = str(payload && payload.result, "");
            const message = "Game Over: " + str(payload && payload.result, "Unknown");
            const key = resultKey(latestGameOverResult);
            if (key && key !== lastGameOverAudioResult) {
                lastGameOverAudioResult = key;
                playSound(key === "win" ? "victory" : (key === "lose" ? "defeat" : "roundResolve"));
            }
            setMessage(message);
            appendLog(message);
            renderTrainingResult(latestState || { phase: "finished", result: latestGameOverResult });
        });

        socket.on("post_match_summary", (payload) => {
            latestPostMatchSummary = payload || {};
            renderTrainingResult(latestState || { phase: "finished", result: latestGameOverResult || latestPostMatchSummary.result });
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

            const restartBtn = event.target.closest("#az48-training-restart");
            if (restartBtn) {
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

    function shouldShowFirstPlayerCoach() {
        if (!isTrainingLikePage()) return false;
        try {
            return window.localStorage.getItem(FIRST_PLAYER_STORAGE_KEY) !== "1";
        } catch (error) {
            return true;
        }
    }

    function setFirstPlayerCoachSeen() {
        try {
            window.localStorage.setItem(FIRST_PLAYER_STORAGE_KEY, "1");
        } catch (error) {}
    }

    function closeFirstPlayerCoach(permanent) {
        const coach = document.getElementById("az48-first-player-flow");
        if (coach) coach.remove();
        if (permanent) setFirstPlayerCoachSeen();
    }

    function ensureFirstPlayerCoach() {
        if (!shouldShowFirstPlayerCoach()) return;
        if (document.getElementById("az48-first-player-flow")) return;

        const coach = document.createElement("aside");
        coach.id = "az48-first-player-flow";
        coach.className = "az48-first-player-flow";
        coach.setAttribute("aria-label", "First-time player flow");
        coach.innerHTML = [
            '<span>First Duel Guide</span>',
            '<strong>Reduce enemy HP, one clear round at a time.</strong>',
            '<ol>',
            '<li>Choose Strike, Guard or Focus.</li>',
            '<li>Play one card if the server highlights it.</li>',
            '<li>Click Ready to resolve combat.</li>',
            '<li>Read Battle Highlights and Round Summary.</li>',
            '<li>Use Collection and Deck after the match.</li>',
            '</ol>',
            '<div>',
            '<button type="button" data-first-flow-close>Entendi</button>',
            '<button type="button" data-first-flow-never>Não mostrar novamente</button>',
            '</div>'
        ].join("");

        document.body.appendChild(coach);
    }

    function bindFirstPlayerCoach() {
        document.addEventListener("click", (event) => {
            const close = event.target.closest("[data-first-flow-close]");
            if (close) {
                event.preventDefault();
                closeFirstPlayerCoach(false);
                return;
            }

            const never = event.target.closest("[data-first-flow-never]");
            if (never) {
                event.preventDefault();
                closeFirstPlayerCoach(true);
            }
        });
    }

    function bindTrainingDifficulty() {
        updateTrainingDifficultyUi();
        document.querySelectorAll('input[name="training_difficulty"]').forEach((input) => {
            input.addEventListener("change", updateTrainingDifficultyUi);
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
            renderTrainingResult,
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
        bindTrainingDifficulty();
        bindFirstPlayerCoach();
        ensureFirstPlayerCoach();

        setMessage("Connecting...");
    }

    document.addEventListener("DOMContentLoaded", boot);
})();


// ARENA_PLAY_CARD_AZ48_FIX_V56


// ARENA_PLAY_CARD_AZ48_FIX_V57


// ARENA_PLAY_CARD_ID_FIX_V58
