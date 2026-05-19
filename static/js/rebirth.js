(function () {
    "use strict";

    const endpoints = window.REBIRTH_ENDPOINTS || {};
    const app = {
        state: null,
        selectedInstanceId: null,
        pending: false
    };

    const elements = {};

    function byId(id) {
        return document.getElementById(id);
    }

    function cacheElements() {
        [
            "player-hp",
            "bot-hp",
            "turn-number",
            "bot-card",
            "focus-card",
            "evolution-panel",
            "evolution-name",
            "evolve-button",
            "player-hand",
            "hand-count",
            "play-button",
            "next-turn-button",
            "result-label",
            "result-title",
            "result-copy",
            "turn-log",
            "phase-label"
        ].forEach((id) => {
            elements[id] = byId(id);
        });
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function setText(id, value) {
        if (elements[id]) {
            elements[id].textContent = value == null ? "" : String(value);
        }
    }

    async function api(url, body) {
        const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify(body || {})
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
            const message = payload && payload.error ? payload.error.message : "Rebirth request failed.";
            throw new Error(message);
        }
        return payload;
    }

    async function request(action) {
        if (app.pending) return;
        app.pending = true;
        renderButtons();
        try {
            await action();
        } catch (error) {
            showError(error.message || "Action failed.");
        } finally {
            app.pending = false;
            renderButtons();
        }
    }

    function applyState(state) {
        app.state = state;
        if (!handContains(app.selectedInstanceId)) {
            app.selectedInstanceId = null;
        }
        render();
    }

    function handContains(instanceId) {
        if (!instanceId || !app.state || !app.state.player) return false;
        return app.state.player.hand.some((card) => card.instance_id === instanceId);
    }

    function selectedCard() {
        if (!app.state || !app.state.player) return null;
        if (app.selectedInstanceId) {
            return app.state.player.hand.find((card) => card.instance_id === app.selectedInstanceId) || null;
        }
        return app.state.player.played_card || null;
    }

    function cardInnerMarkup(card) {
        return `
            <div class="rb-card-art">
                <span>${escapeHtml(card.family)}</span>
            </div>
            <div class="rb-card-body">
                <span>${escapeHtml(card.element)} - Tier ${escapeHtml(card.tier)}</span>
                <strong>${escapeHtml(card.name)}</strong>
                <p>${escapeHtml(card.flavor)}</p>
            </div>
            <b class="rb-power">${escapeHtml(card.power)}</b>
        `;
    }

    function cardMarkup(card, options) {
        const opts = options || {};
        const selected = opts.selected ? " is-selected" : "";
        const tag = opts.button ? "button" : "article";
        const attrs = opts.button
            ? `type="button" data-card-instance="${escapeHtml(card.instance_id)}"`
            : "";
        return `
            <${tag} class="rb-card${selected}" data-element="${escapeHtml(card.element)}" ${attrs}>
                ${cardInnerMarkup(card)}
            </${tag}>
        `;
    }

    function emptyFocusMarkup() {
        return `
            <div class="rb-card-art">
                <span>Choose</span>
            </div>
            <div class="rb-card-body">
                <span>Ready</span>
                <strong>Select a monster</strong>
                <p>Your card becomes the center of the clash.</p>
            </div>
            <b class="rb-power">?</b>
        `;
    }

    function render() {
        if (!app.state) return;
        const state = app.state;
        setText("player-hp", state.player.hp);
        setText("bot-hp", state.bot.hp);
        setText("turn-number", String(state.turn).padStart(2, "0"));
        setText("phase-label", state.phase);
        renderFocusCard();
        renderBotCard();
        renderEvolution();
        renderHand();
        renderResult();
        renderLog();
        renderButtons();
    }

    function renderFocusCard() {
        const host = elements["focus-card"];
        if (!host) return;
        const card = selectedCard();
        if (!card) {
            host.className = "rb-card rb-card-large rb-empty-card";
            host.removeAttribute("data-element");
            host.innerHTML = emptyFocusMarkup();
            return;
        }
        host.className = "rb-card rb-card-large";
        host.setAttribute("data-element", card.element);
        host.innerHTML = cardInnerMarkup(card);
    }

    function renderBotCard() {
        const host = elements["bot-card"];
        if (!host || !app.state) return;
        const card = app.state.bot.played_card;
        if (!card) {
            host.className = "rb-card-back";
            host.removeAttribute("data-element");
            host.innerHTML = "<span>Bot's Card</span>";
            return;
        }
        host.className = "rb-card rb-card-large";
        host.setAttribute("data-element", card.element);
        host.innerHTML = cardInnerMarkup(card);
    }

    function renderEvolution() {
        const panel = elements["evolution-panel"];
        const button = elements["evolve-button"];
        if (!panel || !button || !app.state) return;
        const evolution = (app.state.available_evolutions || [])[0];
        if (!evolution || app.state.phase !== "choose") {
            panel.hidden = true;
            button.dataset.cardId = "";
            return;
        }
        panel.hidden = false;
        button.dataset.cardId = evolution.card_id;
        setText("evolution-name", `${evolution.name} x${evolution.count}`);
    }

    function renderHand() {
        const host = elements["player-hand"];
        if (!host || !app.state) return;
        const hand = app.state.player.hand || [];
        setText("hand-count", `${hand.length} cards`);
        host.innerHTML = hand.map((card) => cardMarkup(card, {
            button: true,
            selected: card.instance_id === app.selectedInstanceId
        })).join("");
        host.querySelectorAll("[data-card-instance]").forEach((button) => {
            button.addEventListener("click", () => {
                if (app.state.phase !== "choose") return;
                app.selectedInstanceId = button.getAttribute("data-card-instance");
                render();
            });
        });
    }

    function renderResult() {
        if (!app.state) return;
        const result = app.state.result;
        if (app.state.is_finished) {
            const won = app.state.winner === "player";
            const tied = app.state.winner === "clash";
            setText("result-label", tied ? "Clash" : won ? "Victory" : "Defeat");
            setText("result-title", tied ? "Both sides fell." : won ? "You won the duel." : "Bot won the duel.");
            setText("result-copy", tied ? "The match ended in a final clash." : "Start a new match when ready.");
            return;
        }
        if (result) {
            setText("result-label", result.outcome);
            setText("result-title", result.outcome === "Clash" ? "No damage." : result.outcome);
            setText("result-copy", result.message);
            return;
        }
        setText("result-label", "Waiting");
        setText("result-title", "Pick one monster.");
        setText("result-copy", "The bot will answer with one monster. Higher power wins the turn.");
    }

    function renderLog() {
        const host = elements["turn-log"];
        if (!host || !app.state) return;
        host.innerHTML = (app.state.log || [])
            .slice()
            .reverse()
            .map((line) => `<li>${escapeHtml(line)}</li>`)
            .join("");
    }

    function renderButtons() {
        if (!app.state) return;
        const canChoose = app.state.phase === "choose" && !app.state.is_finished && !app.pending;
        if (elements["play-button"]) {
            elements["play-button"].disabled = !canChoose || !app.selectedInstanceId;
        }
        if (elements["next-turn-button"]) {
            elements["next-turn-button"].disabled = app.pending || app.state.phase !== "result";
        }
        if (elements["evolve-button"]) {
            elements["evolve-button"].disabled = !canChoose || !elements["evolve-button"].dataset.cardId;
        }
    }

    function showError(message) {
        setText("result-label", "Error");
        setText("result-title", "Action refused.");
        setText("result-copy", message);
    }

    function bindEvents() {
        document.querySelectorAll("[data-new-match]").forEach((button) => {
            button.addEventListener("click", startMatch);
        });

        if (elements["play-button"]) {
            elements["play-button"].addEventListener("click", () => {
                if (!app.selectedInstanceId || !app.state) return;
                request(async () => {
                    const payload = await api(endpoints.playCard, {
                        match_id: app.state.match_id,
                        card_instance_id: app.selectedInstanceId
                    });
                    applyState(payload.state);
                });
            });
        }

        if (elements["next-turn-button"]) {
            elements["next-turn-button"].addEventListener("click", () => {
                if (!app.state) return;
                request(async () => {
                    const payload = await api(endpoints.nextTurn, { match_id: app.state.match_id });
                    applyState(payload.state);
                });
            });
        }

        if (elements["evolve-button"]) {
            elements["evolve-button"].addEventListener("click", () => {
                if (!app.state) return;
                const cardId = elements["evolve-button"].dataset.cardId;
                if (!cardId) return;
                request(async () => {
                    const payload = await api(endpoints.evolve, {
                        match_id: app.state.match_id,
                        card_id: cardId
                    });
                    app.selectedInstanceId = payload.evolved.instance_id;
                    applyState(payload.state);
                });
            });
        }
    }

    function startMatch() {
        request(async () => {
            const payload = await api(endpoints.start, {});
            applyState(payload.state);
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        cacheElements();
        bindEvents();
        startMatch();
    });
})();
