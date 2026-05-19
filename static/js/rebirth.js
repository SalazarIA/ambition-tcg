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
            "player-hp-fill",
            "bot-hp",
            "bot-hp-fill",
            "turn-number",
            "bot-card",
            "focus-card",
            "evolution-panel",
            "evolution-name",
            "evolution-card-thumbnail",
            "evolve-button",
            "player-hand",
            "hand-count",
            "play-button",
            "next-turn-button",
            "secondary-action-copy",
            "result-label",
            "result-title",
            "result-copy",
            "result-panel",
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
        if (!app.selectedInstanceId && state && state.phase === "choose" && state.player && state.player.hand.length) {
            app.selectedInstanceId = state.player.hand[0].instance_id;
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

    function artStyle(card) {
        return card && card.art ? `style="background-image: url('${escapeHtml(card.art)}')"` : "";
    }

    function cardInnerMarkup(card) {
        return `
            <div class="rb-card-topline">
                <div>
                    <strong>${escapeHtml(card.name)}</strong>
                    <span>${escapeHtml(card.role || card.family)}</span>
                </div>
                <b class="rb-card-rank">${escapeHtml(card.attack || card.power)}</b>
            </div>
            <div class="rb-card-art" ${artStyle(card)}>
                <img src="${escapeHtml(card.art)}" alt="" loading="lazy">
            </div>
            <div class="rb-card-rule">
                <strong>${escapeHtml(card.ability_name || "Clash")}</strong>
                <p>${escapeHtml(card.ability_text || card.flavor)}</p>
            </div>
            <div class="rb-card-stats">
                <span><i class="rb-stat-sword"></i><b>${escapeHtml(card.attack || card.power)}</b></span>
                <span><i class="rb-stat-crest"></i></span>
                <span><i class="rb-stat-shield"></i><b>${escapeHtml(card.guard || 0)}</b></span>
            </div>
        `;
    }

    function miniCardMarkup(card, options) {
        const opts = options || {};
        const selected = opts.selected ? " is-selected" : "";
        return `
            <button class="rb-mini-card${selected}" type="button" data-card-instance="${escapeHtml(card.instance_id)}" aria-pressed="${opts.selected ? "true" : "false"}" aria-label="Select ${escapeHtml(card.name)}, attack ${escapeHtml(card.attack)}, guard ${escapeHtml(card.guard)}">
                <b class="rb-power">${escapeHtml(card.attack || card.power)}</b>
                <div class="rb-mini-art" ${artStyle(card)}></div>
                <div class="rb-mini-copy">
                    <span>${escapeHtml(card.element)} - Tier ${escapeHtml(card.tier)}</span>
                    <strong>${escapeHtml(card.name)}</strong>
                    <div class="rb-mini-stats">
                        <b>${escapeHtml(card.attack || card.power)}</b>
                        <b>${escapeHtml(card.guard || 0)}</b>
                    </div>
                </div>
            </button>
        `;
    }

    function emptyFocusMarkup() {
        return `
            <div class="rb-card-topline">
                <div>
                    <strong>Select a monster</strong>
                    <span>Ready</span>
                </div>
                <b class="rb-card-rank">?</b>
            </div>
            <div class="rb-card-art">
                <span>Choose</span>
            </div>
            <div class="rb-card-rule">
                <strong>One Card Clash</strong>
                <p>Your card becomes the center of the duel.</p>
            </div>
            <div class="rb-card-stats">
                <span><i class="rb-stat-sword"></i><b>0</b></span>
                <span><i class="rb-stat-crest"></i></span>
                <span><i class="rb-stat-shield"></i><b>0</b></span>
            </div>
        `;
    }

    function render() {
        if (!app.state) return;
        const state = app.state;
        setText("player-hp", state.player.hp);
        setText("bot-hp", state.bot.hp);
        setText("turn-number", String(state.turn).padStart(2, "0"));
        setText("phase-label", state.phase);
        renderHpBars();
        renderFocusCard();
        renderBotCard();
        renderEvolution();
        renderHand();
        renderResult();
        renderLog();
        renderButtons();
    }

    function renderHpBars() {
        if (!app.state) return;
        const playerMax = Number(app.state.player.max_hp || 30);
        const botMax = Number(app.state.bot.max_hp || 30);
        const playerScale = Math.max(0, Math.min(1, Number(app.state.player.hp || 0) / playerMax));
        const botScale = Math.max(0, Math.min(1, Number(app.state.bot.hp || 0) / botMax));
        if (elements["player-hp-fill"]) {
            elements["player-hp-fill"].style.transform = `scaleX(${playerScale})`;
        }
        if (elements["bot-hp-fill"]) {
            elements["bot-hp-fill"].style.transform = `scaleX(${botScale})`;
        }
    }

    function renderFocusCard() {
        const host = elements["focus-card"];
        if (!host) return;
        const card = selectedCard();
        if (!card) {
            host.className = "rb-monster-card rb-monster-card-main rb-empty-card";
            host.removeAttribute("data-element");
            host.innerHTML = emptyFocusMarkup();
            return;
        }
        host.className = `rb-monster-card rb-monster-card-main${Number(card.tier || 1) > 1 ? " is-evolved" : ""}`;
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
        host.className = "rb-monster-card rb-bot-revealed";
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
        const sourceCard = (app.state.player.hand || []).find((card) => card.id === evolution.card_id);
        if (elements["evolution-card-thumbnail"] && sourceCard) {
            elements["evolution-card-thumbnail"].style.backgroundImage = `url('${sourceCard.art}')`;
        }
    }

    function renderHand() {
        const host = elements["player-hand"];
        if (!host || !app.state) return;
        const hand = app.state.player.hand || [];
        setText("hand-count", `${hand.length} cards`);
        host.innerHTML = hand.map((card) => miniCardMarkup(card, {
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
        const panel = elements["result-panel"];
        if (panel) {
            panel.classList.remove("is-victory", "is-defeat", "is-clash");
        }
        if (app.state.is_finished) {
            const won = app.state.winner === "player";
            const tied = app.state.winner === "clash";
            if (panel) {
                panel.classList.add(tied ? "is-clash" : won ? "is-victory" : "is-defeat");
            }
            setText("result-label", tied ? "Clash" : won ? "Victory" : "Defeat");
            setText("result-title", tied ? "Both sides fell." : won ? "You won the duel." : "Bot won the duel.");
            setText("result-copy", tied ? "The match ended in a final clash." : "Start a new match when ready.");
            return;
        }
        if (result) {
            if (panel) {
                panel.classList.add(`is-${String(result.outcome || "clash").toLowerCase()}`);
            }
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
        const evolution = (app.state.available_evolutions || [])[0];
        if (elements["play-button"]) {
            elements["play-button"].disabled = !canChoose || !app.selectedInstanceId;
        }
        if (elements["next-turn-button"]) {
            if (app.state.phase === "result") {
                elements["next-turn-button"].innerHTML = '<i class="rb-action-loop"></i>Next Turn';
                elements["next-turn-button"].disabled = app.pending;
                setText("secondary-action-copy", "Advance to the next clash");
            } else {
                elements["next-turn-button"].innerHTML = '<i class="rb-action-loop"></i>Combine';
                elements["next-turn-button"].disabled = !canChoose || !evolution;
                setText("secondary-action-copy", "Merge duplicates to evolve");
            }
        }
        if (elements["evolve-button"]) {
            elements["evolve-button"].disabled = !canChoose || !evolution;
        }
    }

    function evolveFirstDuplicate() {
        if (!app.state) return Promise.resolve();
        const evolution = (app.state.available_evolutions || [])[0];
        if (!evolution) return Promise.resolve();
        return request(async () => {
            const payload = await api(endpoints.evolve, {
                match_id: app.state.match_id,
                card_id: evolution.card_id
            });
            app.selectedInstanceId = payload.evolved.instance_id;
            applyState(payload.state);
        });
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
                if (app.state.phase === "choose") {
                    evolveFirstDuplicate();
                    return;
                }
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
                evolveFirstDuplicate();
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
