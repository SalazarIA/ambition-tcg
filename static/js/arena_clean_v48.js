(function () {
    const socket = io();

    let latestState = null;

    function $(id) {
        return document.getElementById(id);
    }

    function text(id, value) {
        const el = $(id);
        if (el) el.textContent = value;
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

    function cardId(card, index = 0) {
        return str(card.id || card.card_id || card.runtime_id || card.name || ("card-" + index));
    }

    function normalizeCard(card, index = 0) {
        card = card || {};
        const type = str(card.type || "Monster");
        const isMonster = type.toLowerCase() === "monster";
        const power = num(card.power || card.attack || card.value || 0);
        const value = num(card.value || card.power || card.attack || 0);

        return {
            id: cardId(card, index),
            name: str(card.name || cardId(card, index)),
            type,
            element: str(card.element || "Neutral"),
            rarity: str(card.rarity || "Common"),
            sigil: str(card.sigil || "None"),
            cost: num(card.cost || card.energy_cost || 1, 1),
            stat: isMonster ? power : value,
            statLabel: isMonster ? "PWR" : "VAL",
            effect: str(card.effect || card.description || ""),
        };
    }

    function normalizePayload(payload) {
        payload = payload || {};

        if (payload.me && payload.enemy) {
            return payload;
        }

        return {
            mode: payload.mode || window.AMBITIONZ_ARENA_MODE || "training",
            phase: payload.phase || "start",
            round: payload.round || 1,
            message: payload.message || payload.status_message || "Choose your action.",
            me: payload.me || {
                name: payload.player_name || "You",
                hp: payload.hp || 3600,
                energy: payload.energy || 0,
                max_energy: payload.max_energy || payload.energy || 0,
                ambition: payload.ambition || 0,
                hand: payload.my_hand || payload.hand || [],
                field: payload.my_field || payload.field || {},
            },
            enemy: payload.enemy || {
                name: payload.enemy_name || "Opponent",
                hp: payload.enemy_hp || 3600,
                energy: payload.enemy_energy || 0,
                max_energy: payload.enemy_max_energy || payload.enemy_energy || 0,
                hand_count: payload.enemy_hand_count || 0,
                field: payload.enemy_field || {},
            },
            legal_actions: payload.legal_actions || {
                playable_card_ids: payload.playable_card_ids || [],
                can_ready: true,
                can_play_cards: true,
            },
        };
    }

    function fieldCard(card, label) {
        if (!card) {
            return '<article class="az48-slot">' + esc(label) + '</article>';
        }

        return renderCard(card, { field: true });
    }

    function normalizeField(field) {
        field = field || {};

        return {
            trap: field.trap || field.field_t || null,
            monster: field.monster || field.field_m || field.active_monster || null,
            spell: field.spell || field.field_st || field.support || null,
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

    function render(payload) {
        const state = normalizePayload(payload);
        latestState = state;
        window.__ambitionzArena48State = state;

        const me = state.me || {};
        const enemy = state.enemy || {};
        const legal = state.legal_actions || {};
        const playable = arr(legal.playable_card_ids).map(String);

        text("az48-mode", str(state.mode || "training"));
        text("az48-round", num(state.round || 1, 1));
        text("az48-phase", str(state.phase || "start"));
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
        text("az48-enemy-hand", num(enemy.hand_count || arr(enemy.hand).length || 0));

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

        const hand = arr(me.hand || state.my_hand || state.hand);
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

    function emitMany(names, payload) {
        names.forEach((name) => {
            try {
                socket.emit(name, payload || {});
                console.debug("[Ambitionz V48 emit]", name, payload || {});
            } catch (error) {
                console.warn("[Ambitionz V48 emit failed]", name, error);
            }
        });
    }

    function startTraining() {
        emitMany(["start_training_v1", "start_training", "request_match_state"], {});
    }

    function setIntent(intent) {
        emitMany(["set_intent_v1", "set_intent"], { intent });
    }

    function ready() {
        emitMany(["declare_ready_v1", "declare_ready"], {});
    }

    function playCard(cardId) {
        emitMany(["play_card_v1", "play_card"], { card_id: cardId });
    }

    socket.on("connect", () => {
        text("az48-message", "Connected. Press Start.");
        if (window.AMBITIONZ_ARENA_MODE === "training") {
            emitMany(["request_match_state"], {});
        }
    });

    [
        "game_state_update",
        "match_state",
        "match_state_v1",
        "arena_state",
        "battle_state",
        "training_started",
        "start_training_result"
    ].forEach((eventName) => {
        socket.on(eventName, (payload) => {
            console.debug("[Ambitionz V48 state]", eventName, payload);
            render(payload || {});
        });
    });

    socket.on("battle_log", (payload) => {
        if (typeof payload === "string") {
            text("az48-message", payload);
        } else if (payload && payload.message) {
            text("az48-message", payload.message);
        }
    });

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

    window.AmbitionzArena48 = {
        render,
        startTraining,
        setIntent,
        ready,
        playCard,
        socket,
    };
})();
