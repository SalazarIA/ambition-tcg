(function () {
    "use strict";

    const RB = {
        state: null,
        loading: false,
        config: window.REBIRTH_CONFIG || {},

        api(url, body) {
            const options = {
                method: body ? "POST" : "GET",
                headers: { "Content-Type": "application/json" }
            };
            if (body) options.body = JSON.stringify(body);
            return fetch(url, options).then((response) => response.json());
        },

        newMatch() {
            this.setLoading(true);
            return this.api(this.config.newUrl)
                .then((payload) => this.applyPayload(payload, "match_start"))
                .catch(() => this.showError("Could not initialize Rebirth."))
                .finally(() => this.setLoading(false));
        },

        restart() {
            this.setLoading(true);
            return this.api(this.config.restartUrl, {})
                .then((payload) => this.applyPayload(payload, "match_start"))
                .catch(() => this.showError("Could not restart Rebirth."))
                .finally(() => this.setLoading(false));
        },

        selectIntent(intent) {
            if (!this.state || this.state.is_finished) return;
            this.setLoading(true);
            return this.api(this.config.intentUrl, { match_id: this.state.match_id, intent })
                .then((payload) => this.applyPayload(payload, "intent_selected", { intent, side: "player" }))
                .catch(() => this.showError("Intent was refused."))
                .finally(() => this.setLoading(false));
        },

        playCard(cardId) {
            if (!this.state || this.state.is_finished) return;
            this.setLoading(true);
            return this.api(this.config.playCardUrl, { match_id: this.state.match_id, card_id: cardId })
                .then((payload) => this.applyPayload(payload, "card_activated", { card_id: cardId, side: "player" }))
                .catch(() => this.showError("Card could not be activated."))
                .finally(() => this.setLoading(false));
        },

        resolve() {
            if (!this.state || this.state.is_finished || !this.canResolve()) return;
            this.setLoading(true);
            return this.api(this.config.resolveUrl, { match_id: this.state.match_id })
                .then((payload) => this.applyPayload(payload, "round_resolved"))
                .catch(() => this.showError("Round could not resolve."))
                .finally(() => this.setLoading(false));
        },

        applyPayload(payload, eventName, eventPayload) {
            if (!payload || !payload.ok || !payload.state) {
                const message = payload && payload.error && payload.error.message ? payload.error.message : "Rebirth action failed.";
                this.showError(message);
                return;
            }
            this.state = payload.state;
            this.showError("");
            this.render();
            this.emit3D(eventName, eventPayload || payload.state.cinematic_event || {});
            if (payload.state.cinematic_event) {
                this.emit3D(payload.state.cinematic_event.type, payload.state.cinematic_event.payload || {});
            }
            if (payload.state.is_finished) {
                this.emit3D("ko", { winner: payload.state.winner });
            }
        },

        canResolve() {
            return Boolean((this.state.available_actions || []).find((action) => action.type === "resolve" && action.enabled));
        },

        canPlayCard(cardId) {
            return Boolean((this.state.available_actions || []).find((action) => action.type === "play_card" && action.card_id === cardId && action.enabled));
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
            setText("rb-player-intent", player.selected_intent || "None");
            setText("rb-opponent-intent", opponent.selected_intent ? "Committed" : "Veiled");

            const banner = document.getElementById("rb-cinematic-banner");
            if (banner) {
                const event = this.state.cinematic_event;
                banner.innerHTML = `<span>${this.state.is_finished ? `Winner: ${this.state.winner}` : event ? cinematicText(event) : "Rebirth core online."}</span>`;
            }

            const playerActive = document.getElementById("rb-player-active");
            const opponentActive = document.getElementById("rb-opponent-active");
            if (playerActive) playerActive.outerHTML = this.renderCard(player.active_card, { active: true, id: "rb-player-active" });
            if (opponentActive) opponentActive.outerHTML = this.renderCard(opponent.active_card, { active: true, id: "rb-opponent-active" });

            this.renderHand();
            this.renderLog();
            this.renderButtons();

            if (window.Rebirth3D) {
                window.Rebirth3D.setState(this.state);
            }
        },

        renderCard(card, options) {
            const opts = options || {};
            const idAttr = opts.id ? ` id="${opts.id}"` : "";
            if (!card) {
                return `<div${idAttr} class="rb-active-card rb-empty-slot">No active card</div>`;
            }
            const classes = opts.active ? "rb-active-card" : "rb-card";
            const disabled = opts.button && !this.canPlayCard(card.id) ? " disabled" : "";
            const tag = opts.button ? "button" : "article";
            const data = opts.button ? ` type="button" data-rb-card-id="${card.id}"${disabled}` : "";
            return `
                <${tag}${idAttr} class="${classes}"${data}>
                    <span>${card.element} · ${card.role}</span>
                    <strong>${card.name}</strong>
                    <p>${card.text || ""}</p>
                    <small>ATK ${card.attack} · GRD ${card.guard} · AMB ${card.ambition}</small>
                </${tag}>
            `;
        },

        renderHand() {
            const hand = this.state.hand || [];
            const host = document.getElementById("rb-hand");
            setText("rb-hand-count", `${hand.length} card${hand.length === 1 ? "" : "s"}`);
            if (!host) return;
            if (!hand.length) {
                host.innerHTML = `<div class="rb-card rb-empty-slot">No cards in hand.</div>`;
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
            list.innerHTML = events.slice(-8).reverse().map((entry) => `<li>${entry.message || entry.type}</li>`).join("");
        },

        renderButtons() {
            if (!this.state) return;
            document.querySelectorAll("[data-rb-intent]").forEach((button) => {
                const intent = button.getAttribute("data-rb-intent");
                button.classList.toggle("is-selected", this.state.selected_intent === intent);
                button.disabled = Boolean(this.state.is_finished || this.loading);
            });
            const resolve = document.getElementById("rb-resolve-button");
            if (resolve) resolve.disabled = Boolean(this.state.is_finished || this.loading || !this.canResolve());
        },

        emit3D(eventName, payload) {
            if (!eventName || !window.Rebirth3D) return;
            const normalized = String(eventName).replace("round_resolved", "round_end");
            window.Rebirth3D.emit(normalized, payload || {});
        },

        setLoading(flag) {
            this.loading = Boolean(flag);
            const node = document.getElementById("rb-loading");
            if (node) node.hidden = !this.loading;
            this.renderButtons();
        },

        showError(message) {
            const node = document.getElementById("rb-error");
            if (node) node.textContent = message || "";
        }
    };

    function setText(id, value) {
        const node = document.getElementById(id);
        if (node) node.textContent = value == null ? "" : String(value);
    }

    function cinematicText(event) {
        const type = String(event.type || "event").replace(/_/g, " ");
        if (event.payload && event.payload.winner) return `${type}: ${event.payload.winner}`;
        if (event.payload && event.payload.amount) return `${type}: ${event.payload.amount}`;
        return type;
    }

    function bind() {
        document.querySelectorAll("[data-rb-intent]").forEach((button) => {
            button.addEventListener("click", () => RB.selectIntent(button.getAttribute("data-rb-intent")));
        });
        const resolve = document.getElementById("rb-resolve-button");
        const restart = document.getElementById("rb-new-match-button");
        if (resolve) resolve.addEventListener("click", () => RB.resolve());
        if (restart) restart.addEventListener("click", () => RB.restart());
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
