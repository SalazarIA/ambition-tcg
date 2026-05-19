(function () {
    "use strict";

    const RebirthConfig = {
        endpoints: window.REBIRTH_ENDPOINTS || {},
        assets: window.REBIRTH_ASSETS || {},
        boardWidth: 852,
        boardHeight: 1846
    };

    const RebirthStore = {
        state: null,
        selectedInstanceId: null,
        pending: false,
        elements: {},

        setPending(value) {
            this.pending = Boolean(value);
            const board = this.elements["rebirth-board"];
            if (board) {
                board.classList.toggle("is-pending", this.pending);
            }
        },

        setState(state) {
            this.state = state;
            if (!this.handContains(this.selectedInstanceId)) {
                this.selectedInstanceId = null;
            }
            if (!this.selectedInstanceId && state && state.phase === "choose" && state.player && state.player.hand.length) {
                this.selectedInstanceId = state.player.hand[0].instance_id;
            }
        },

        handContains(instanceId) {
            if (!instanceId || !this.state || !this.state.player) return false;
            return this.state.player.hand.some((card) => card.instance_id === instanceId);
        },

        selectedCard() {
            if (!this.state || !this.state.player) return null;
            if (this.selectedInstanceId) {
                return this.state.player.hand.find((card) => card.instance_id === this.selectedInstanceId) || null;
            }
            return this.state.player.played_card || null;
        },

        firstEvolution() {
            return ((this.state && this.state.available_evolutions) || [])[0] || null;
        }
    };

    const RebirthDom = {
        byId(id) {
            return document.getElementById(id);
        },

        cache() {
            [
                "rebirth-board",
                "rebirth-error",
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
                RebirthStore.elements[id] = this.byId(id);
            });
        },

        setText(id, value) {
            const element = RebirthStore.elements[id];
            if (element) {
                element.textContent = value == null ? "" : String(value);
            }
        }
    };

    const RebirthText = {
        escape(value) {
            return String(value == null ? "" : value)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }
    };

    const RebirthApi = {
        async post(url, body) {
            if (!url) {
                throw this.error("missing_endpoint", "Rebirth endpoint is not configured.");
            }
            let response;
            try {
                response = await fetch(url, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    credentials: "same-origin",
                    body: JSON.stringify(body || {})
                });
            } catch (error) {
                throw this.error("network_error", error.message || "Network request failed.");
            }

            let payload = null;
            try {
                payload = await response.json();
            } catch (_error) {
                throw this.error("malformed_response", "The server returned an unreadable response.");
            }

            if (!response.ok || !payload || payload.ok !== true) {
                const serverError = payload && payload.error ? payload.error : {};
                throw this.error(serverError.code || "rebirth_error", serverError.message || "Rebirth request failed.");
            }

            return payload;
        },

        error(code, message) {
            const error = new Error(message);
            error.code = code;
            return error;
        }
    };

    const RebirthBoardScaler = {
        init() {
            this.scale();
            window.addEventListener("resize", () => this.scale(), { passive: true });
            if (window.visualViewport) {
                window.visualViewport.addEventListener("resize", () => this.scale(), { passive: true });
                window.visualViewport.addEventListener("scroll", () => this.scale(), { passive: true });
            }
            window.addEventListener("wheel", (event) => event.preventDefault(), { passive: false });
            window.addEventListener("touchmove", (event) => {
                const target = event.target;
                if (target && target.closest && target.closest(".rb-hand, .rb-log ol")) {
                    return;
                }
                event.preventDefault();
            }, { passive: false });
        },

        scale() {
            const viewport = window.visualViewport || window;
            const width = Math.max(1, viewport.width || window.innerWidth || RebirthConfig.boardWidth);
            const height = Math.max(1, viewport.height || window.innerHeight || RebirthConfig.boardHeight);
            const scale = Math.min(width / RebirthConfig.boardWidth, height / RebirthConfig.boardHeight);
            document.documentElement.style.setProperty("--rb-scale", String(scale));
            window.scrollTo(0, 0);
        }
    };

    const RebirthAssets = {
        manifest: null,
        seen: new Set(),

        preload() {
            [
                RebirthConfig.assets.fallbackCardArt,
                RebirthConfig.assets.botCardBack,
                RebirthConfig.assets.botEmblem
            ].filter(Boolean).forEach((src) => {
                this.preloadUrl(src);
            });
            if (RebirthConfig.assets.manifest) {
                fetch(RebirthConfig.assets.manifest, { credentials: "same-origin" })
                    .then((response) => response.ok ? response.json() : null)
                    .then((manifest) => {
                        this.manifest = manifest || null;
                        Object.values((manifest && manifest.cards) || {}).forEach((src) => this.preloadUrl(src));
                    })
                    .catch(() => {});
            }
        },

        preloadUrl(src) {
            if (!src || this.seen.has(src)) return;
            this.seen.add(src);
            const image = new Image();
            image.src = src;
        },

        preloadCard(card) {
            if (card && card.art) {
                this.preloadUrl(card.art);
            }
        },

        preloadState(state) {
            if (!state) return;
            ((state.player && state.player.hand) || []).forEach((card) => this.preloadCard(card));
            this.preloadCard(state.player && state.player.played_card);
            this.preloadCard(state.bot && state.bot.played_card);
        },

        artStyle(card) {
            const source = card && card.art ? card.art : RebirthConfig.assets.fallbackCardArt;
            return source ? `style="background-image: url('${RebirthText.escape(source)}')"` : "";
        },

        cssVars(card) {
            const palette = card && card.palette ? card.palette : {};
            const safe = (value, fallback) => /^#[0-9a-f]{6}$/i.test(String(value || "")) ? value : fallback;
            return [
                `--card-accent:${safe(palette.accent, "#f4ad26")}`,
                `--card-secondary:${safe(palette.secondary, "#58d6ff")}`,
                `--card-shadow:${safe(palette.shadow, "#08090b")}`
            ].join(";");
        },

        imageMarkup(card) {
            const source = card && card.art ? card.art : RebirthConfig.assets.fallbackCardArt;
            if (!source) return "";
            return `<img data-rebirth-art data-art-key="${RebirthText.escape(card && card.art_key ? card.art_key : "fallback")}" src="${RebirthText.escape(source)}" alt="" loading="eager">`;
        },

        bindFallbacks(root) {
            const host = root || document;
            host.querySelectorAll("img[data-rebirth-art]").forEach((image) => {
                image.addEventListener("error", () => {
                    const frame = image.closest(".rb-card-art, .rb-mini-art, .rb-evolution-thumb");
                    image.hidden = true;
                    if (frame) {
                        frame.classList.add("rb-asset-fallback");
                        if (RebirthConfig.assets.fallbackCardArt) {
                            frame.style.backgroundImage = `url('${RebirthConfig.assets.fallbackCardArt}')`;
                        }
                    }
                }, { once: true });
            });
        }
    };

    const RebirthMarkup = {
        card(card) {
            return `
                <div class="rb-card-topline">
                    <div>
                        <strong>${RebirthText.escape(card.name)}</strong>
                        <span>${RebirthText.escape(card.role || card.family)}</span>
                    </div>
                    <b class="rb-card-rank">${RebirthText.escape(card.attack || card.power)}</b>
                </div>
                <div class="rb-card-art" ${RebirthAssets.artStyle(card)}>
                    ${RebirthAssets.imageMarkup(card)}
                </div>
                <div class="rb-card-rule">
                    <strong>${RebirthText.escape(card.ability_name || "Clash")}</strong>
                    <p>${RebirthText.escape(card.ability_text || card.flavor)}</p>
                </div>
                <div class="rb-card-stats">
                    <span><i class="rb-stat-sword"></i><b>${RebirthText.escape(card.attack || card.power)}</b></span>
                    <span><i class="rb-stat-crest"></i></span>
                    <span><i class="rb-stat-shield"></i><b>${RebirthText.escape(card.guard || 0)}</b></span>
                </div>
            `;
        },

        miniCard(card, options) {
            const selected = options && options.selected ? " is-selected" : "";
            return `
                <button class="rb-mini-card${selected}" type="button" data-card-instance="${RebirthText.escape(card.instance_id)}" data-art-key="${RebirthText.escape(card.art_key || card.id)}" style="${RebirthAssets.cssVars(card)}" aria-pressed="${selected ? "true" : "false"}" aria-label="Select ${RebirthText.escape(card.name)}, attack ${RebirthText.escape(card.attack)}, guard ${RebirthText.escape(card.guard)}">
                    <b class="rb-power">${RebirthText.escape(card.attack || card.power)}</b>
                    <div class="rb-mini-art" ${RebirthAssets.artStyle(card)}></div>
                    <div class="rb-mini-copy">
                        <span>${RebirthText.escape(card.element)} - Tier ${RebirthText.escape(card.tier)}</span>
                        <strong>${RebirthText.escape(card.name)}</strong>
                        <div class="rb-mini-stats">
                            <b>${RebirthText.escape(card.attack || card.power)}</b>
                            <b>${RebirthText.escape(card.guard || 0)}</b>
                        </div>
                    </div>
                </button>
            `;
        },

        emptyFocus() {
            return `
                <div class="rb-card-topline">
                    <div>
                        <strong>Select a monster</strong>
                        <span>Ready</span>
                    </div>
                    <b class="rb-card-rank">?</b>
                </div>
                <div class="rb-card-art rb-asset-fallback">
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
    };

    const RebirthRenderer = {
        render() {
            if (!RebirthStore.state) return;
            const state = RebirthStore.state;
            RebirthAssets.preloadState(state);
            RebirthDom.setText("player-hp", state.player.hp);
            RebirthDom.setText("bot-hp", state.bot.hp);
            RebirthDom.setText("turn-number", String(state.turn).padStart(2, "0"));
            RebirthDom.setText("phase-label", state.phase);
            this.hpBars();
            this.focusCard();
            this.botCard();
            this.evolutionPanel();
            this.hand();
            this.result();
            this.log();
            this.buttons();
            RebirthAssets.bindFallbacks(RebirthStore.elements["rebirth-board"]);
        },

        hpBars() {
            const state = RebirthStore.state;
            const playerMax = Number(state.player.max_hp || 30);
            const botMax = Number(state.bot.max_hp || 30);
            const playerScale = Math.max(0, Math.min(1, Number(state.player.hp || 0) / playerMax));
            const botScale = Math.max(0, Math.min(1, Number(state.bot.hp || 0) / botMax));
            if (RebirthStore.elements["player-hp-fill"]) {
                RebirthStore.elements["player-hp-fill"].style.transform = `scaleX(${playerScale})`;
            }
            if (RebirthStore.elements["bot-hp-fill"]) {
                RebirthStore.elements["bot-hp-fill"].style.transform = `scaleX(${botScale})`;
            }
        },

        focusCard() {
            const host = RebirthStore.elements["focus-card"];
            if (!host) return;
            const card = RebirthStore.selectedCard();
            if (!card) {
                host.className = "rb-main-card rb-monster-card rb-monster-card-main rb-empty-card";
                host.removeAttribute("data-element");
                host.removeAttribute("data-art-key");
                host.removeAttribute("style");
                host.innerHTML = RebirthMarkup.emptyFocus();
                return;
            }
            host.className = `rb-main-card rb-monster-card rb-monster-card-main${Number(card.tier || 1) > 1 ? " is-evolved" : ""}`;
            host.setAttribute("data-element", card.element);
            host.setAttribute("data-art-key", card.art_key || card.id);
            host.setAttribute("style", RebirthAssets.cssVars(card));
            host.innerHTML = RebirthMarkup.card(card);
        },

        botCard() {
            const host = RebirthStore.elements["bot-card"];
            if (!host) return;
            const card = RebirthStore.state.bot.played_card;
            if (!card) {
                host.className = "rb-bot-card rb-card-back";
                host.removeAttribute("data-element");
                host.removeAttribute("data-art-key");
                host.removeAttribute("style");
                host.innerHTML = "<span>Bot's Card</span>";
                return;
            }
            host.className = "rb-bot-card rb-monster-card rb-bot-revealed";
            host.setAttribute("data-element", card.element);
            host.setAttribute("data-art-key", card.art_key || card.id);
            host.setAttribute("style", RebirthAssets.cssVars(card));
            host.innerHTML = RebirthMarkup.card(card);
        },

        evolutionPanel() {
            const panel = RebirthStore.elements["evolution-panel"];
            const button = RebirthStore.elements["evolve-button"];
            const thumb = RebirthStore.elements["evolution-card-thumbnail"];
            if (!panel || !button) return;
            const evolution = RebirthStore.firstEvolution();
            const canUse = Boolean(evolution && RebirthStore.state.phase === "choose" && !RebirthStore.state.is_finished);
            panel.classList.toggle("is-empty", !canUse);
            button.disabled = !canUse || RebirthStore.pending;
            button.dataset.cardId = canUse ? evolution.card_id : "";

            if (!canUse) {
                RebirthDom.setText("evolution-name", "No duplicate");
                if (thumb) {
                    thumb.style.backgroundImage = "";
                    thumb.classList.add("rb-asset-fallback");
                }
                return;
            }

            RebirthDom.setText("evolution-name", `${evolution.name} x${evolution.count}`);
            const sourceCard = (RebirthStore.state.player.hand || []).find((card) => card.id === evolution.card_id);
            if (thumb && sourceCard) {
                thumb.classList.remove("rb-asset-fallback");
                thumb.style.backgroundImage = `url('${sourceCard.art}')`;
                thumb.style.setProperty("--card-accent", (sourceCard.palette && sourceCard.palette.accent) || "#f4ad26");
            }
        },

        hand() {
            const host = RebirthStore.elements["player-hand"];
            if (!host) return;
            const hand = RebirthStore.state.player.hand || [];
            RebirthDom.setText("hand-count", `${hand.length} cards`);
            host.innerHTML = hand.map((card) => RebirthMarkup.miniCard(card, {
                selected: card.instance_id === RebirthStore.selectedInstanceId
            })).join("");
        },

        result() {
            const state = RebirthStore.state;
            const result = state.result;
            const panel = RebirthStore.elements["result-panel"];
            if (panel) {
                panel.classList.remove("is-victory", "is-defeat", "is-clash");
            }
            if (state.is_finished) {
                const won = state.winner === "player";
                const tied = state.winner === "clash";
                if (panel) {
                    panel.classList.add(tied ? "is-clash" : won ? "is-victory" : "is-defeat");
                }
                RebirthDom.setText("result-label", tied ? "Clash" : won ? "Victory" : "Defeat");
                RebirthDom.setText("result-title", tied ? "Both sides fell." : won ? "You won the duel." : "Bot won the duel.");
                RebirthDom.setText("result-copy", "Start a new match when ready.");
                return;
            }
            if (result) {
                if (panel) {
                    panel.classList.add(`is-${String(result.outcome || "clash").toLowerCase()}`);
                }
                RebirthDom.setText("result-label", result.outcome);
                RebirthDom.setText("result-title", result.outcome === "Clash" ? "No damage." : result.outcome);
                RebirthDom.setText("result-copy", result.message);
                return;
            }
            RebirthDom.setText("result-label", "Waiting");
            RebirthDom.setText("result-title", "Pick one monster.");
            RebirthDom.setText("result-copy", "The bot will answer with one monster. Higher attack wins the clash.");
        },

        log() {
            const host = RebirthStore.elements["turn-log"];
            if (!host) return;
            host.innerHTML = (RebirthStore.state.log || [])
                .slice()
                .reverse()
                .map((line) => `<li>${RebirthText.escape(line)}</li>`)
                .join("");
        },

        buttons() {
            const state = RebirthStore.state;
            if (!state) return;
            const canChoose = state.phase === "choose" && !state.is_finished && !RebirthStore.pending;
            const canNext = state.phase === "result" && !state.is_finished && !RebirthStore.pending;
            const evolution = RebirthStore.firstEvolution();
            if (RebirthStore.elements["play-button"]) {
                RebirthStore.elements["play-button"].disabled = !canChoose || !RebirthStore.selectedInstanceId;
            }
            if (RebirthStore.elements["next-turn-button"]) {
                if (state.phase === "result") {
                    RebirthStore.elements["next-turn-button"].innerHTML = '<i class="rb-action-loop"></i>Next Turn';
                    RebirthStore.elements["next-turn-button"].disabled = !canNext;
                    RebirthDom.setText("secondary-action-copy", "Advance to the next clash");
                } else if (state.is_finished) {
                    RebirthStore.elements["next-turn-button"].innerHTML = '<i class="rb-action-loop"></i>Finished';
                    RebirthStore.elements["next-turn-button"].disabled = true;
                    RebirthDom.setText("secondary-action-copy", "Start a new match");
                } else {
                    RebirthStore.elements["next-turn-button"].innerHTML = '<i class="rb-action-loop"></i>Combine';
                    RebirthStore.elements["next-turn-button"].disabled = !canChoose || !evolution;
                    RebirthDom.setText("secondary-action-copy", "Merge duplicates to evolve");
                }
            }
            if (RebirthStore.elements["evolve-button"]) {
                RebirthStore.elements["evolve-button"].disabled = !canChoose || !evolution;
            }
        }
    };

    const RebirthErrors = {
        show(message) {
            const error = RebirthStore.elements["rebirth-error"];
            if (!error) return;
            error.textContent = message || "Action refused.";
            error.classList.add("is-visible");
        },

        clear() {
            const error = RebirthStore.elements["rebirth-error"];
            if (!error) return;
            error.textContent = "";
            error.classList.remove("is-visible");
        }
    };

    const RebirthFlow = {
        async request(action) {
            if (RebirthStore.pending) return;
            RebirthErrors.clear();
            RebirthStore.setPending(true);
            RebirthRenderer.buttons();
            try {
                await action();
            } catch (error) {
                RebirthErrors.show(error.message || "Action failed.");
                RebirthDom.setText("result-label", "Error");
                RebirthDom.setText("result-title", "Action refused.");
                RebirthDom.setText("result-copy", error.message || "Action failed.");
            } finally {
                RebirthStore.setPending(false);
                RebirthRenderer.buttons();
            }
        },

        applyState(state) {
            RebirthStore.setState(state);
            RebirthRenderer.render();
        },

        async startMatch() {
            await this.request(async () => {
                const payload = await RebirthApi.post(RebirthConfig.endpoints.start, {});
                RebirthStore.selectedInstanceId = null;
                this.applyState(payload.state);
            });
        },

        async evolveFirstDuplicate() {
            const evolution = RebirthStore.firstEvolution();
            if (!evolution || !RebirthStore.state) return;
            await this.request(async () => {
                const payload = await RebirthApi.post(RebirthConfig.endpoints.evolve, {
                    match_id: RebirthStore.state.match_id,
                    card_id: evolution.card_id
                });
                RebirthStore.selectedInstanceId = payload.evolved ? payload.evolved.instance_id : null;
                this.applyState(payload.state);
            });
        },

        async playSelectedCard() {
            if (!RebirthStore.selectedInstanceId || !RebirthStore.state) return;
            await this.request(async () => {
                const payload = await RebirthApi.post(RebirthConfig.endpoints.playCard, {
                    match_id: RebirthStore.state.match_id,
                    card_instance_id: RebirthStore.selectedInstanceId
                });
                RebirthStore.selectedInstanceId = null;
                this.applyState(payload.state);
            });
        },

        async nextTurn() {
            if (!RebirthStore.state) return;
            await this.request(async () => {
                const payload = await RebirthApi.post(RebirthConfig.endpoints.nextTurn, {
                    match_id: RebirthStore.state.match_id
                });
                this.applyState(payload.state);
            });
        }
    };

    const RebirthInput = {
        bind() {
            document.querySelectorAll("[data-new-match]").forEach((button) => {
                button.addEventListener("click", () => RebirthFlow.startMatch());
            });

            const playButton = RebirthStore.elements["play-button"];
            if (playButton) {
                playButton.addEventListener("click", () => RebirthFlow.playSelectedCard());
            }

            const nextButton = RebirthStore.elements["next-turn-button"];
            if (nextButton) {
                nextButton.addEventListener("click", () => {
                    if (!RebirthStore.state) return;
                    if (RebirthStore.state.phase === "choose") {
                        RebirthFlow.evolveFirstDuplicate();
                    } else if (RebirthStore.state.phase === "result") {
                        RebirthFlow.nextTurn();
                    }
                });
            }

            const evolveButton = RebirthStore.elements["evolve-button"];
            if (evolveButton) {
                evolveButton.addEventListener("click", () => RebirthFlow.evolveFirstDuplicate());
            }

            const hand = RebirthStore.elements["player-hand"];
            if (hand) {
                hand.addEventListener("click", (event) => {
                    const button = event.target.closest("[data-card-instance]");
                    if (!button || !RebirthStore.state || RebirthStore.state.phase !== "choose") return;
                    RebirthStore.selectedInstanceId = button.getAttribute("data-card-instance");
                    RebirthRenderer.render();
                });
            }
        }
    };

    function init() {
        if ("scrollRestoration" in window.history) {
            window.history.scrollRestoration = "manual";
        }
        window.scrollTo(0, 0);
        RebirthDom.cache();
        RebirthBoardScaler.init();
        RebirthAssets.preload();
        RebirthInput.bind();
        RebirthFlow.startMatch();
    }

    document.addEventListener("DOMContentLoaded", init);
})();
