(function () {
    "use strict";

    const config = window.AMBITIONZ_ASCENSION_CONFIG || {};
    const state = {
        match: null,
        actions: null,
        reward: null,
        selectedCardId: null,
        tutorialStep: 0,
    };

    const TUTORIAL_KEY = "ambitionz_ascension_tutorial_seen_v1";
    const tutorialSteps = [
        ["Champion", "One active Champion anchors your side of the Duel Altar. Summon one early."],
        ["Intent", "Strike, Guard, Focus and Scheme are psychological commitments before the clash."],
        ["One-card Play", "Each card has a purpose: summon, bind, burn, equip, set, cast or ascend."],
        ["Commit", "Commit resolves the Round once your Intent is chosen."],
        ["Dominate", "A full Ambition Core can attempt Domination, but failure leaves vulnerability."],
        ["Reward", "Finished duels reveal XP, Gold, Champion progress and unlock progress."]
    ];

    const $ = (selector) => document.querySelector(selector);

    function api(url, body) {
        const options = {
            method: body ? "POST" : "GET",
            headers: { "Content-Type": "application/json" },
        };
        if (body) {
            options.body = JSON.stringify(body);
        }
        return fetch(url, options).then((response) => response.json());
    }

    function setError(message) {
        const node = $("#ax-error");
        if (node) {
            node.textContent = message || "";
        }
    }

    function applyPayload(payload) {
        if (!payload || !payload.match) {
            setError("The Duel Altar did not answer. Try a new duel.");
            return;
        }
        state.match = payload.match;
        state.actions = payload.actions || state.actions;
        state.reward = payload.reward || state.reward;
        if (!payload.ok && payload.error) {
            setError(payload.error.message || payload.error.code || "Action refused.");
        } else {
            setError("");
        }
        render();
    }

    function startMatch() {
        state.reward = null;
        api(config.startUrl, { bot_profile: selectedBotProfile() }).then(applyPayload).catch(() => setError("Could not start Ascension Duel."));
    }

    function selectedBotProfile() {
        return "Controller";
    }

    function loadState() {
        api(config.stateUrl).then(applyPayload).catch(startMatch);
    }

    function selectIntent(intent) {
        api(config.intentUrl, { intent }).then(applyPayload).catch(() => setError("Intent could not be committed."));
    }

    function selectCard(cardId) {
        state.selectedCardId = cardId;
        renderHand();
        renderModePicker();
    }

    function playSelected(mode) {
        if (!state.selectedCardId) {
            setError("Select a card first.");
            return;
        }
        api(config.playUrl, { card_id: state.selectedCardId, mode }).then((payload) => {
            if (payload.ok) {
                state.selectedCardId = null;
            }
            applyPayload(payload);
        }).catch(() => setError("The card could not be played."));
    }

    function commitRound() {
        api(config.commitUrl, {}).then(applyPayload).catch(() => setError("Commit failed."));
    }

    function dominate() {
        api(config.dominateUrl, {}).then(applyPayload).catch(() => setError("Domination failed."));
    }

    function initials(name) {
        return String(name || "?")
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map((part) => part.charAt(0).toUpperCase())
            .join("");
    }

    function cardResolveLine(card) {
        const resolve = card && card.resolve ? card.resolve : {};
        const bits = [];
        if (resolve.pressure) bits.push(`Pressure ${resolve.pressure}`);
        if (resolve.guard) bits.push(`Guard ${resolve.guard}`);
        if (resolve.damage) bits.push(`Burn ${resolve.damage}`);
        if (resolve.heal) bits.push(`Recover ${resolve.heal}`);
        if (card && card.ambition_cost) bits.push(`Cost ${card.ambition_cost}`);
        return bits.join(" · ");
    }

    function renderChampion(selector, card, emptyText) {
        const host = $(selector);
        if (!host) return;
        if (!card) {
            host.innerHTML = `<div class="ax-champion-empty">${emptyText}</div>`;
            return;
        }
        host.innerHTML = `
            <article class="ax-champion ${card.ascended ? "is-ascended" : ""}">
                <small>${card.faction || "Unbound"}</small>
                <b>${initials(card.name)}</b>
                <strong>${card.name}</strong>
            </article>
        `;
    }

    function renderSouls(selector, souls) {
        const host = $(selector);
        if (!host) return;
        const items = souls || [];
        if (!items.length) {
            host.innerHTML = `<span class="ax-empty">No Bound Souls</span>`;
            return;
        }
        host.innerHTML = items.map((card) => `<span class="ax-soul" title="${card.name}">${initials(card.name)}</span>`).join("");
    }

    function renderRelic(selector, relic) {
        const host = $(selector);
        if (!host) return;
        host.textContent = relic ? `Relic: ${relic.name}` : "No Relic";
    }

    function renderSchemes(selector, side) {
        const host = $(selector);
        if (!host) return;
        const schemes = side.schemes || [];
        if (!schemes.length) {
            host.innerHTML = `<span>No Schemes</span>`;
            return;
        }
        host.innerHTML = schemes.map((scheme) => `<span>${scheme.revealed ? scheme.name : "Prepared Scheme"}</span>`).join("");
    }

    function renderAmbitionCore(player) {
        const value = Math.max(0, Number(player.ambition || 0));
        const fill = $("#ax-ambition-fill");
        const label = $("#ax-ambition-value");
        if (fill) {
            fill.style.height = `${Math.min(100, (value / 12) * 100)}%`;
        }
        if (label) {
            label.textContent = value;
        }
    }

    function renderIntentRing(player) {
        document.querySelectorAll("[data-ax-intent]").forEach((button) => {
            const intent = button.getAttribute("data-ax-intent");
            button.classList.toggle("is-selected", player.intent === intent);
            button.disabled = Boolean(state.match && state.match.winner);
        });
    }

    function legalModes(cardId) {
        const actionCard = (state.actions && state.actions.cards || []).find((item) => item.id === cardId);
        return actionCard ? actionCard.modes || [] : [];
    }

    function renderModePicker() {
        const host = $("#ax-mode-picker");
        if (!host) return;
        if (!state.selectedCardId) {
            host.innerHTML = "<span>Select a card</span>";
            return;
        }
        const modes = legalModes(state.selectedCardId);
        if (!modes.length) {
            host.innerHTML = "<span>No legal purpose</span>";
            return;
        }
        host.innerHTML = modes.map((mode) => `<button type="button" data-ax-mode="${mode}">${mode}</button>`).join("");
        host.querySelectorAll("[data-ax-mode]").forEach((button) => {
            button.addEventListener("click", () => playSelected(button.getAttribute("data-ax-mode")));
        });
    }

    function renderHand() {
        const hand = state.match && state.match.player ? state.match.player.hand || [] : [];
        const host = $("#ax-hand");
        const count = $("#ax-hand-count");
        if (count) {
            count.textContent = `${hand.length} card${hand.length === 1 ? "" : "s"}`;
        }
        if (!host) return;
        if (!hand.length) {
            host.innerHTML = `<div class="ax-empty">Your hand is empty. Commit to draw into the next round.</div>`;
            return;
        }
        host.innerHTML = hand.map((card) => {
            const modes = legalModes(card.id);
            const selected = state.selectedCardId === card.id ? " is-selected" : "";
            const disabled = modes.length ? "" : " disabled";
            return `
                <button type="button" class="ax-card${selected}" data-ax-card-id="${card.id}"${disabled}>
                    <span>${card.type}</span>
                    <strong>${card.name}</strong>
                    <p>${card.text || ""}</p>
                    <small>${cardResolveLine(card) || card.faction || "Ascension Duel"}</small>
                </button>
            `;
        }).join("");
        host.querySelectorAll("[data-ax-card-id]").forEach((button) => {
            button.addEventListener("click", () => selectCard(button.getAttribute("data-ax-card-id")));
        });
    }

    function renderChronicle() {
        const list = $("#ax-chronicle-list");
        if (!list || !state.match) return;
        const events = state.match.chronicle || [];
        list.innerHTML = events.slice(-8).reverse().map((event) => `<li>${event.message}</li>`).join("");
    }

    function renderWinner() {
        const winner = state.match && state.match.winner;
        const label = $("#ax-winner-label");
        if (!label) return;
        if (!winner) {
            label.textContent = "";
        } else if (winner === "player") {
            label.textContent = "Victory";
        } else if (winner === "opponent") {
            label.textContent = "Broken";
        } else {
            label.textContent = "Draw";
        }
    }

    function renderBotStyle() {
        const node = $("#ax-bot-style");
        if (!node || !state.match) return;
        const profile = state.match.bot_profile || {};
        node.textContent = `Rival Style: ${profile.label || profile.key || "Controller"}`;
        node.title = profile.description || "";
    }

    function renderReward() {
        const panel = $("#ax-reward-panel");
        if (!panel) return;
        const reward = state.reward;
        panel.hidden = !reward;
        if (!reward) return;
        $("#ax-reward-summary").textContent = reward.summary || "Reward recorded.";
        $("#ax-reward-xp").textContent = reward.xp || 0;
        $("#ax-reward-gold").textContent = reward.gold || 0;
        $("#ax-reward-champion").textContent = reward.champion_progress ? reward.champion_progress.amount || 0 : 0;
    }

    function renderTutorial() {
        const overlay = $("#ax-onboarding");
        if (!overlay || overlay.hidden) return;
        const step = tutorialSteps[state.tutorialStep] || tutorialSteps[0];
        $("#ax-onboarding-title").textContent = step[0];
        $("#ax-onboarding-text").textContent = step[1];
        document.querySelectorAll("[data-ax-tutorial-dot]").forEach((dot) => {
            dot.classList.toggle("is-selected", Number(dot.getAttribute("data-ax-tutorial-dot")) === state.tutorialStep);
        });
    }

    function openTutorial(force) {
        const overlay = $("#ax-onboarding");
        if (!overlay) return;
        if (!force && window.localStorage && window.localStorage.getItem(TUTORIAL_KEY)) return;
        state.tutorialStep = 0;
        overlay.hidden = false;
        renderTutorial();
    }

    function closeTutorial() {
        const overlay = $("#ax-onboarding");
        if (overlay) overlay.hidden = true;
        if (window.localStorage) {
            window.localStorage.setItem(TUTORIAL_KEY, "1");
        }
    }

    function advanceTutorial() {
        if (state.tutorialStep >= tutorialSteps.length - 1) {
            closeTutorial();
            return;
        }
        state.tutorialStep += 1;
        renderTutorial();
    }

    function render() {
        if (!state.match) return;
        const player = state.match.player;
        const opponent = state.match.opponent;

        $("#ax-round-label").textContent = `Round ${state.match.round}`;
        $("#ax-phase-label").textContent = state.match.phase === "finished" ? "Duel complete" : "Awaiting Commit";
        $("#ax-player-hp").textContent = player.hp;
        $("#ax-enemy-hp").textContent = opponent.hp;
        $("#ax-player-echo").textContent = player.echo_count;
        $("#ax-enemy-echo").textContent = opponent.echo_count;
        $("#ax-player-intent").textContent = player.intent || "Choose";
        $("#ax-enemy-intent").textContent = opponent.intent ? "Committed" : "Veiled";

        renderChampion("#ax-player-champion", player.active_champion, "Summon a Champion to claim the altar.");
        renderChampion("#ax-enemy-champion", opponent.active_champion, "The rival has not revealed a Champion.");
        renderSouls("#ax-player-bound-souls", player.bound_souls);
        renderSouls("#ax-enemy-bound-souls", opponent.bound_souls);
        renderRelic("#ax-player-relic", player.relic);
        renderRelic("#ax-enemy-relic", opponent.relic);
        renderSchemes("#ax-player-schemes", player);
        renderSchemes("#ax-enemy-schemes", opponent);
        renderAmbitionCore(player);
        renderIntentRing(player);
        renderHand();
        renderModePicker();
        renderChronicle();
        renderWinner();
        renderBotStyle();
        renderReward();

        const commitButton = $("#ax-commit-button");
        const dominateButton = $("#ax-dominate-button");
        if (commitButton) {
            commitButton.disabled = Boolean(state.match.winner || !player.intent);
        }
        if (dominateButton) {
            dominateButton.disabled = Boolean(state.match.winner || !(state.actions && state.actions.can_dominate));
        }
    }

    function bind() {
        document.querySelectorAll("[data-ax-intent]").forEach((button) => {
            button.addEventListener("click", () => selectIntent(button.getAttribute("data-ax-intent")));
        });
        $("#ax-commit-button").addEventListener("click", commitRound);
        $("#ax-dominate-button").addEventListener("click", dominate);
        $("#ax-new-duel-button").addEventListener("click", startMatch);
        $("#ax-tutorial-button").addEventListener("click", () => openTutorial(true));
        $("#ax-onboarding-next").addEventListener("click", advanceTutorial);
        $("#ax-onboarding-close").addEventListener("click", closeTutorial);
    }

    document.addEventListener("DOMContentLoaded", () => {
        bind();
        loadState();
        openTutorial(false);
    });
}());
