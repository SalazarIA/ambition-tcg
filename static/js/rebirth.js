(function () {
    "use strict";

    const ONBOARDING_KEY = "ambitionz_rebirth_onboarding_seen";
    const log3DMap = {
        match_start: "rebirth:match_start",
        intent_selected: "rebirth:intent_selected",
        card_activated: "rebirth:card_activated",
        ambition_gained: "rebirth:focus",
        guard_applied: "rebirth:guard",
        damage_dealt: "rebirth:damage",
        match_finished: "rebirth:ko",
        round_resolved: "rebirth:round_resolved",
        round_end: "rebirth:round_end"
    };

    const RB = {
        state: null,
        pending: false,
        loading: false,
        lastEventId: 0,
        selectedCardId: null,
        errorTimer: null,
        config: window.REBIRTH_CONFIG || {},

        api(url, body) {
            const options = {
                method: body ? "POST" : "GET",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" }
            };
            if (body) options.body = JSON.stringify(body);
            return fetch(url, options).then((response) => response.json().catch(() => ({
                ok: false,
                error: { message: `Request failed with ${response.status}` }
            })));
        },

        request(action, label) {
            if (this.pending) return Promise.resolve();
            this.setLoading(true);
            return action()
                .catch(() => this.showError(label || "Rebirth action failed."))
                .finally(() => this.setLoading(false));
        },

        newMatch() {
            this.lastEventId = 0;
            this.selectedCardId = null;
            return this.request(
                () => this.api(this.config.newUrl).then((payload) => this.applyPayload(payload, "rebirth:match_start")),
                "Could not initialize Rebirth."
            );
        },

        restart() {
            this.lastEventId = 0;
            this.selectedCardId = null;
            return this.request(
                () => this.api(this.config.restartUrl, {}).then((payload) => this.applyPayload(payload, "rebirth:match_start")),
                "Could not restart Rebirth."
            );
        },

        selectIntent(intent) {
            if (!this.state || this.state.is_finished || this.pending) return Promise.resolve();
            return this.request(
                () => this.api(this.config.intentUrl, { match_id: this.state.match_id, intent })
                    .then((payload) => this.applyPayload(payload, "rebirth:intent_selected", { intent, side: "player" })),
                "Intent was refused."
            );
        },

        playCard(cardId) {
            if (!this.state || this.state.is_finished || this.pending || !this.canPlayCard(cardId)) return Promise.resolve();
            this.selectedCardId = cardId;
            this.renderHand();
            return this.request(
                () => this.api(this.config.playCardUrl, { match_id: this.state.match_id, card_id: cardId })
                    .then((payload) => this.applyPayload(payload, "rebirth:card_activated", { card_id: cardId, side: "player" })),
                "Card could not be activated."
            );
        },

        resolve() {
            if (!this.state || this.state.is_finished || this.pending) return Promise.resolve();
            if (!this.state.player || !this.state.player.active_card) {
                this.showError("Activate one card before resolving the round.");
                return Promise.resolve();
            }
            if (!this.state.selected_intent) {
                this.showError("Choose Strike, Guard or Focus before resolving.");
                return Promise.resolve();
            }
            if (!this.canResolve()) return Promise.resolve();
            return this.request(
                () => this.api(this.config.resolveUrl, { match_id: this.state.match_id })
                    .then((payload) => this.applyPayload(payload, "rebirth:round_resolved")),
                "Round could not resolve."
            );
        },

        applyPayload(payload, fallbackEventName, fallbackPayload) {
            if (!payload || !payload.ok || !payload.state) {
                const message = payload && payload.error && payload.error.message ? payload.error.message : "Rebirth action failed.";
                this.showError(message);
                return;
            }

            this.state = payload.state;
            if (!this.handContains(this.selectedCardId)) this.selectedCardId = null;
            this.showError("");
            this.render();
            this.emitNew3DEvents(fallbackEventName, fallbackPayload || {});

            if (window.Rebirth3D) {
                window.Rebirth3D.setState(this.state);
                if (this.state.is_finished) window.Rebirth3D.setWinner(this.state.winner);
            }
        },

        emitNew3DEvents(fallbackEventName, fallbackPayload) {
            if (fallbackEventName) this.emit3D(fallbackEventName, fallbackPayload);
            const events = (this.state && this.state.combat_log ? this.state.combat_log : [])
                .filter((entry) => Number(entry.id || 0) > this.lastEventId);
            events.forEach((entry) => this.emitLog3D(entry));
            const maxId = events.reduce((max, entry) => Math.max(max, Number(entry.id || 0)), this.lastEventId);
            this.lastEventId = maxId;
        },

        emitLog3D(entry) {
            const eventName = log3DMap[entry.type];
            if (!eventName) return;
            const payload = entry.payload || {};
            this.emit3D(eventName, payload);
            if (entry.type === "intent_selected" && payload.intent) {
                this.emit3D(`rebirth:${String(payload.intent).toLowerCase()}`, payload);
            }
        },

        handContains(cardId) {
            if (!cardId || !this.state) return false;
            return Boolean((this.state.hand || []).find((card) => card.id === cardId));
        },

        canResolve() {
            const actions = this.state && this.state.available_actions ? this.state.available_actions : [];
            return Boolean(actions.find((action) => action.type === "resolve" && action.enabled));
        },

        canPlayCard(cardId) {
            const actions = this.state && this.state.available_actions ? this.state.available_actions : [];
            return Boolean(actions.find((action) => action.type === "play_card" && action.card_id === cardId && action.enabled));
        },

        render() {
            if (!this.state) return;
            const player = this.state.player || {};
            const opponent = this.state.opponent || {};

            setText("rb-player-name", player.name || "Player");
            setText("rb-opponent-name", opponent.name || "Rival");
            setText("rb-player-hp", player.hp);
            setText("rb-opponent-hp", opponent.hp);
            setText("rb-player-ambition", player.ambition);
            setText("rb-opponent-ambition", opponent.ambition);
            setText("rb-player-intent", formatIntent(player.selected_intent || "None"));
            setText("rb-opponent-intent", opponent.selected_intent ? "Committed" : "Veiled");
            setText("rb-round", this.state.round);
            setText("rb-phase", this.state.phase || "START");
            setText("rb-selected-intent", formatIntent(this.state.selected_intent || "None"));
            setText("rb-winner-label", this.state.winner || "None");

            this.renderBanner();
            this.replaceCard("rb-player-active", player.active_card);
            this.replaceCard("rb-opponent-active", opponent.active_card);
            this.renderHand();
            this.renderLog();
            this.renderButtons();
            this.renderWinner();
        },

        renderBanner() {
            const banner = document.getElementById("rb-cinematic-banner");
            if (!banner) return;
            const event = this.state.cinematic_event;
            if (this.state.is_finished) {
                banner.innerHTML = `<strong>${escapeHtml(this.state.winner === "player" ? "ASCENSION ACHIEVED" : "WILL BROKEN")}</strong><span>${escapeHtml(this.state.winner === "player" ? "You broke the opponent's will." : "Rebuild your intent and challenge again.")}</span>`;
                return;
            }
            if (!event) {
                banner.innerHTML = "<strong>Rebirth Core Online</strong><span>Activate one card and choose your intent.</span>";
                return;
            }
            banner.innerHTML = `<strong>${escapeHtml(event.title || event.type || "Arena Shift")}</strong><span>${escapeHtml(event.message || cinematicText(event))}</span>`;
        },

        replaceCard(id, card) {
            const node = document.getElementById(id);
            if (!node) return;
            node.outerHTML = this.renderCard(card, { active: true, id });
        },

        renderCard(card, options) {
            const opts = options || {};
            const idAttr = opts.id ? ` id="${escapeHtml(opts.id)}"` : "";
            if (!card) {
                return `<div${idAttr} class="rb-active-card rb-empty-slot">No active card</div>`;
            }
            const tag = opts.button ? "button" : "article";
            const classes = [
                opts.active ? "rb-active-card" : "rb-card rb-hand-card",
                opts.button && this.selectedCardId === card.id ? "is-selected" : ""
            ].filter(Boolean).join(" ");
            const disabled = opts.button && (!this.canPlayCard(card.id) || this.pending) ? " disabled" : "";
            const data = opts.button ? ` type="button" data-rb-card-id="${escapeHtml(card.id)}"${disabled}` : "";
            return `
                <${tag}${idAttr} class="${classes}"${data}>
                    <span class="rb-card-meta">${escapeHtml(card.element || "Unknown")} / ${escapeHtml(card.role || "Duelist")} / ${escapeHtml(card.rarity || "Common")}</span>
                    <strong class="rb-card-name">${escapeHtml(card.name || "Unnamed Card")}</strong>
                    <p>${escapeHtml(card.text || "")}</p>
                    <small class="rb-card-stats">ATK ${number(card.attack)} · GRD ${number(card.guard)} · AMB ${number(card.ambition)}</small>
                </${tag}>
            `;
        },

        renderHand() {
            const hand = this.state && this.state.hand ? this.state.hand : [];
            const host = document.getElementById("rb-hand");
            setText("rb-hand-count", `${hand.length} card${hand.length === 1 ? "" : "s"}`);
            if (!host) return;
            if (!hand.length) {
                host.innerHTML = '<div class="rb-card rb-empty-slot">No cards in hand.</div>';
                return;
            }
            host.innerHTML = hand.map((card) => this.renderCard(card, { button: true })).join("");
            host.querySelectorAll("[data-rb-card-id]").forEach((button) => {
                button.addEventListener("click", () => this.playCard(button.getAttribute("data-rb-card-id")));
            });
        },

        renderLog() {
            const list = document.getElementById("rb-combat-log-list");
            if (!list) return;
            const events = this.state.combat_log || [];
            list.innerHTML = events.slice(-10).reverse().map((entry) => `<li class="rb-log-entry">${escapeHtml(humanLog(entry))}</li>`).join("");
        },

        renderButtons() {
            if (!this.state) return;
            document.querySelectorAll("[data-rb-intent]").forEach((button) => {
                const intent = button.getAttribute("data-rb-intent");
                button.classList.toggle("is-selected", this.state.selected_intent === intent);
                button.disabled = Boolean(this.state.is_finished || this.pending);
            });
            document.querySelectorAll("[data-rb-new-duel]").forEach((button) => {
                button.disabled = Boolean(this.pending);
            });
            const resolve = document.getElementById("rb-resolve-button");
            if (resolve) {
                const needsCard = !(this.state.player && this.state.player.active_card);
                const needsIntent = !this.state.selected_intent;
                resolve.textContent = needsCard ? "Activate a Card" : needsIntent ? "Choose Intent" : "Resolve Round";
                resolve.disabled = Boolean(this.state.is_finished || this.pending || needsCard || needsIntent || !this.canResolve());
            }
        },

        renderWinner() {
            const panel = document.getElementById("rb-winner-state");
            if (!panel) return;
            panel.hidden = !this.state.is_finished;
            if (!this.state.is_finished) return;
            const playerWon = this.state.winner === "player";
            setText("rb-winner-title", playerWon ? "ASCENSION ACHIEVED" : "WILL BROKEN");
            setText("rb-winner-copy", playerWon ? "You broke the opponent's will." : "Rebuild your intent and challenge again.");
        },

        emit3D(eventName, payload) {
            if (!eventName || !window.Rebirth3D) return;
            const normalized = String(eventName).startsWith("rebirth:") ? String(eventName) : `rebirth:${eventName}`;
            window.Rebirth3D.emit(normalized, payload || {});
        },

        setLoading(flag) {
            this.pending = Boolean(flag);
            this.loading = this.pending;
            const node = document.getElementById("rb-loading");
            if (node) node.hidden = !this.pending;
            this.renderButtons();
        },

        showError(message) {
            const node = document.getElementById("rb-error");
            if (!node) return;
            window.clearTimeout(this.errorTimer);
            node.textContent = message || "";
            if (message) {
                this.errorTimer = window.setTimeout(() => {
                    node.textContent = "";
                }, 3600);
            }
        },

        initOnboarding() {
            const panel = document.getElementById("rb-onboarding");
            const dismiss = document.getElementById("rb-onboarding-dismiss");
            const reset = document.getElementById("rb-reset-tips");
            const seen = window.localStorage && window.localStorage.getItem(ONBOARDING_KEY) === "true";
            if (panel) panel.hidden = seen;
            if (dismiss) {
                dismiss.addEventListener("click", () => {
                    if (window.localStorage) window.localStorage.setItem(ONBOARDING_KEY, "true");
                    if (panel) panel.hidden = true;
                });
            }
            if (reset) {
                reset.addEventListener("click", () => {
                    if (window.localStorage) window.localStorage.removeItem(ONBOARDING_KEY);
                    if (panel) panel.hidden = false;
                });
            }
        }
    };

    function setText(id, value) {
        const node = document.getElementById(id);
        if (node) node.textContent = value == null ? "" : String(value);
    }

    function number(value) {
        return Number(value || 0);
    }

    function formatIntent(value) {
        return String(value || "None").toLowerCase().replace(/^\w/, (letter) => letter.toUpperCase());
    }

    function cinematicText(event) {
        const type = String(event.type || "event").replace(/_/g, " ");
        if (event.payload && event.payload.winner) return `${type}: ${event.payload.winner}`;
        if (event.payload && event.payload.amount) return `${type}: ${event.payload.amount}`;
        return type;
    }

    function humanLog(entry) {
        const payload = entry.payload || {};
        const side = payload.side ? formatIntent(payload.side) : "";
        if (entry.type === "round_start") return `Round ${payload.round || entry.round} started.`;
        if (entry.type === "draw") return `${side || "A side"} drew ${payload.count || 1} card.`;
        if (entry.type === "intent_selected") return `${side || "A side"} chose ${formatIntent(payload.intent)}.`;
        if (entry.type === "card_activated") return `${payload.card_name || "A card"} entered the arena.`;
        if (entry.type === "active_card_replaced") return `${payload.old_card_name || "A card"} became discard; ${payload.new_card_name || "a new card"} took its place.`;
        if (entry.type === "attack_calculated") return `${side || "A side"} prepared ${payload.attack || 0} pressure.`;
        if (entry.type === "guard_applied") return `${side || "A side"} guarded ${payload.amount || 0} pressure.`;
        if (entry.type === "ambition_gained") return `${side || "A side"} gained ${payload.amount || 0} Ambition.`;
        if (entry.type === "damage_dealt") return `${formatIntent(payload.target || "Target")} took ${payload.amount || 0} damage.`;
        if (entry.type === "round_resolved") return `Round ${payload.round || entry.round} resolved.`;
        if (entry.type === "round_end") return `Round ${payload.round || entry.round} ended.`;
        if (entry.type === "match_finished") return `${formatIntent(payload.winner || "Winner")} wins.`;
        return entry.message || String(entry.type || "Event").replace(/_/g, " ");
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function bind() {
        document.querySelectorAll("[data-rb-intent]").forEach((button) => {
            button.addEventListener("click", () => RB.selectIntent(button.getAttribute("data-rb-intent")));
        });
        const resolve = document.getElementById("rb-resolve-button");
        if (resolve) resolve.addEventListener("click", () => RB.resolve());
        document.querySelectorAll("[data-rb-new-duel]").forEach((button) => {
            button.addEventListener("click", () => RB.restart());
        });
        RB.initOnboarding();
    }

    document.addEventListener("DOMContentLoaded", () => {
        if (window.Rebirth3D) {
            window.Rebirth3D.init(document.getElementById("rebirth-3d-stage"));
        }
        bind();
        RB.newMatch();
    });

    window.RB = RB;
}());
