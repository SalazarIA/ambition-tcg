(function () {
    "use strict";

    const SCHEMA = "ambitionz_arena_clean_v50";

    const ELEMENT_ART = {
        Fire: "/static/img/cards/elemental/fire.svg",
        Water: "/static/img/cards/elemental/water.svg",
        Earth: "/static/img/cards/elemental/earth.svg",
        Plant: "/static/img/cards/elemental/plant.svg",
        Global: "/static/img/cards/elemental/global.svg",
        Neutral: "/static/img/cards/elemental/neutral.svg",
    };

    const ELEMENT_COLORS = {
        Fire: { primary: "#ff5948", secondary: "#ffc76f", accent: "#fff1bb" },
        Water: { primary: "#42bfff", secondary: "#72fff0", accent: "#d6fbff" },
        Earth: { primary: "#a77a4c", secondary: "#f2c17a", accent: "#ffe6b0" },
        Plant: { primary: "#53df76", secondary: "#b9ff7b", accent: "#e7ffd4" },
        Global: { primary: "#d9b66d", secondary: "#9aa7ff", accent: "#fff5ce" },
        Neutral: { primary: "#9ea7b7", secondary: "#d9deea", accent: "#f4f7ff" },
    };

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

    function slug(value, fallback = "neutral") {
        const text = str(value, fallback).toLowerCase();
        return text.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || fallback;
    }

    function normalizeElement(value) {
        const element = str(value, "Neutral");
        return ELEMENT_COLORS[element] ? element : "Neutral";
    }

    function normalizeCard(card, index = 0) {
        card = card || {};

        const type = str(card.type || "Monster");
        const kind = str(card.kind || "").toLowerCase();
        const isMonster = type.toLowerCase() === "monster" || kind === "creature";
        const element = normalizeElement(card.element || (type === "Trap" ? "Global" : "Neutral"));
        const power = num(card.power || card.attack || card.display_stat || card.value || card.atk || 0);
        const value = num(card.value || card.display_stat || card.power || card.attack || card.shield || 0);
        const currentHp = num(card.current_hp || card.hp || card.max_hp || 0);
        const maxHp = num(card.max_hp || card.hp || currentHp || 0);
        const stat = num(card.display_stat || (isMonster ? power : value) || card.cost || 1, 1);
        const rawImage = str(card.image || "");
        const hasSpecificArt = rawImage && !rawImage.includes("placeholder");
        const artUrl = hasSpecificArt
            ? (rawImage.startsWith("/") ? rawImage : "/static/img/" + rawImage.replace(/^\/+/, ""))
            : ELEMENT_ART[element];

        return {
            raw: card,
            id: str(card.id || card.card_id || card.runtime_id || card.name || ("card-" + index)),
            cardId: str(card.card_id || card.id || ""),
            instanceId: str(card.instance_id || ""),
            name: str(card.name || card.id || ("Card " + (index + 1))),
            type,
            kind: str(card.kind || type),
            element,
            rarity: str(card.rarity || "Common"),
            sigil: str(card.sigil || "None"),
            role: str(card.role || card.kind || "Card"),
            cost: num(card.cost || card.energy_cost || 1, 1),
            stat,
            statLabel: str(card.combat_label || (isMonster ? "PWR" : "VAL")),
            attack: num(card.attack || card.atk || power || 0),
            currentHp,
            maxHp,
            effect: str(card.effect || card.description || card.text || ""),
            effectSummary: str(card.effect_summary || card.effect || card.description || card.text || ""),
            preview: str(card.preview || card.effect_summary || card.effect || card.description || ""),
            disabledReason: str(card.disabled_reason || ""),
            playable: Boolean(card.playable),
            artUrl,
            hasSpecificArt: Boolean(hasSpecificArt),
            elementCss: "element-" + slug(element),
            typeCss: "type-" + slug(type),
            rarityCss: "rarity-" + slug(card.rarity || "common"),
            colors: ELEMENT_COLORS[element] || ELEMENT_COLORS.Neutral,
            isMonster,
            lane: str(card.lane || ""),
        };
    }

    function normalizeField(field) {
        field = field || {};
        const lanes = field.lanes || field.board || {};

        return {
            trap: field.trap ? normalizeCard(field.trap, 0) : null,
            monster: field.monster ? normalizeCard(field.monster, 1) : null,
            spell: field.spell ? normalizeCard(field.spell, 2) : null,
            lanes: {
                left: lanes.left ? normalizeCard(lanes.left, 3) : null,
                center: lanes.center ? normalizeCard(lanes.center, 4) : null,
                right: lanes.right ? normalizeCard(lanes.right, 5) : null,
            },
        };
    }

    function normalizePlayer(player, viewer) {
        player = player || {};

        return {
            sid: player.sid,
            userId: player.user_id,
            name: str(player.name || (viewer ? "You" : "Opponent")),
            hp: num(player.hp, 0),
            energy: num(player.energy, 0),
            maxEnergy: num(player.max_energy || player.energy, 0),
            ambition: num(player.ambition, 0),
            shield: num(player.shield, 0),
            intent: str(player.intent || ""),
            ready: Boolean(player.ready),
            hand: viewer ? arr(player.hand).map(normalizeCard) : [],
            handCount: num(player.hand_count || arr(player.hand).length, 0),
            deckCount: num(player.deck_count, 0),
            graveyardCount: num(player.graveyard_count, 0),
            canUnleash: Boolean(player.can_unleash),
            field: normalizeField(player.field),
            board: normalizeField({ lanes: player.board || (player.field && player.field.lanes) }).lanes,
        };
    }

    function normalizeArenaState(payload) {
        payload = payload || {};

        const legal = payload.legal_actions || {};
        const me = normalizePlayer(payload.me, true);
        const enemy = normalizePlayer(payload.enemy, false);
        const playable = arr(legal.playable_card_ids).map(String);

        me.hand = me.hand.map((card) => ({
            ...card,
            playable: playable.includes(String(card.id)),
        }));

        return {
            raw: payload,
            schema: str(payload.schema),
            isCanonical: payload.schema === SCHEMA,
            engine: str(payload.engine || ""),
            mode: str(payload.mode || "training"),
            phase: str(payload.phase || "start"),
            round: num(payload.round || 1, 1),
            message: str(payload.message || "Choose your action."),
            winner: payload.winner || null,
            reason: payload.reason || null,
            enemyPreview: payload.enemy_preview || {},
            roundSummary: payload.round_summary || {},
            events: arr(payload.events),
            roundEvents: arr(payload.round_events),
            turn: payload.turn || {},
            help: payload.help || {},
            legalActions: {
                showStart: Boolean(legal.show_start || legal.can_start),
                canStart: Boolean(legal.can_start),
                showIntents: Boolean(legal.show_intents || legal.can_choose_intent),
                canChooseIntent: Boolean(legal.can_choose_intent),
                showReady: Boolean(legal.show_ready || legal.can_ready),
                canReady: Boolean(legal.can_ready),
                canUnleash: Boolean(legal.can_unleash),
                legalLanes: arr(legal.legal_lanes).map(String),
                legalTargets: arr(legal.legal_targets).map(String),
                playableCardIds: playable,
                primaryAction: str(legal.primary_action || ""),
                prompt: str(legal.prompt || ""),
                cardStates: arr(legal.card_states),
                disabledReasonsByCard: legal.disabled_reasons_by_card || {},
            },
            me,
            enemy,
            log: arr(payload.log),
        };
    }

    function boardSlots(state) {
        state = normalizeArenaState(state && state.raw ? state.raw : state);

        return [
            { owner: "enemy", lane: "left", slot: "creature", card: state.enemy.board.left },
            { owner: "enemy", lane: "center", slot: "creature", card: state.enemy.board.center },
            { owner: "enemy", lane: "right", slot: "creature", card: state.enemy.board.right },
            { owner: "me", lane: "left", slot: "creature", card: state.me.board.left },
            { owner: "me", lane: "center", slot: "creature", card: state.me.board.center },
            { owner: "me", lane: "right", slot: "creature", card: state.me.board.right },
        ];
    }

    window.AmbitionzArenaRendererAdapter = {
        SCHEMA,
        ELEMENT_ART,
        ELEMENT_COLORS,
        normalizeCard,
        normalizeField,
        normalizePlayer,
        normalizeArenaState,
        boardSlots,
    };
})();
