(function () {
    "use strict";

    const RebirthConfig = {
        endpoints: window.REBIRTH_ENDPOINTS || {},
        assets: window.REBIRTH_ASSETS || {},
        player: window.REBIRTH_PLAYER_CONTEXT || {},
        boardWidth: 852,
        boardHeight: 1846
    };

    const RebirthStore = {
        state: null,
        selectedInstanceId: null,
        selectedAttackerId: null,
        selectedSummonSlot: null,
        reward: null,
        lastResultSignature: null,
        guidedFirstMatch: false,
        tutorialCompletionSent: false,
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
            if (!this.fieldContains(this.selectedAttackerId)) {
                this.selectedAttackerId = null;
            }
            if (this.selectedSummonSlot !== null && !this.fieldSlotOpen("player", this.selectedSummonSlot)) {
                this.selectedSummonSlot = null;
            }
            if (!this.selectedInstanceId && !this.selectedAttackerId && state && state.phase === "choose" && state.player && state.player.hand.length) {
                this.selectedInstanceId = state.player.hand[0].instance_id;
            }
        },

        handContains(instanceId) {
            if (!instanceId || !this.state || !this.state.player) return false;
            return this.state.player.hand.some((card) => card.instance_id === instanceId);
        },

        handCard(instanceId) {
            if (!instanceId || !this.state || !this.state.player) return null;
            return this.state.player.hand.find((card) => card.instance_id === instanceId) || null;
        },

        fieldContains(instanceId) {
            if (!instanceId || !this.state || !this.state.player) return false;
            return this.fieldCards("player").some((card) => card.instance_id === instanceId);
        },

        fieldCard(instanceId) {
            if (!instanceId || !this.state || !this.state.player) return null;
            return this.fieldCards("player").find((card) => card.instance_id === instanceId) || null;
        },

        selectedCard() {
            if (!this.state || !this.state.player) return null;
            if (this.selectedInstanceId) {
                return this.state.player.hand.find((card) => card.instance_id === this.selectedInstanceId) || null;
            }
            if (this.selectedAttackerId) {
                return this.fieldCards("player").find((card) => card.instance_id === this.selectedAttackerId) || null;
            }
            return this.state.player.played_card || null;
        },

        fieldSlots(sideName) {
            if (!this.state) return [null, null, null];
            const side = this.state[sideName] || {};
            const rootField = sideName === "player" ? this.state.player_field : this.state.bot_field;
            const source = Array.isArray(rootField)
                ? rootField
                : Array.isArray(side.field)
                    ? side.field
                    : null;
            const slots = [null, null, null];
            if (source) {
                source.slice(0, 3).forEach((card, index) => {
                    slots[index] = card || null;
                });
                return slots;
            }
            (side.battlefield || []).forEach((card, index) => {
                const slot = Number.isInteger(Number(card && card.field_slot)) ? Number(card.field_slot) : index;
                if (slot >= 0 && slot < 3 && !slots[slot]) {
                    slots[slot] = card;
                }
            });
            return slots;
        },

        fieldCards(sideName) {
            return this.fieldSlots(sideName).filter(Boolean);
        },

        fieldSlotIndex(slot) {
            if (slot === null || slot === undefined || slot === "") return null;
            const index = Number(slot);
            return Number.isInteger(index) ? index : null;
        },

        fieldSlotOpen(sideName, slot) {
            const index = this.fieldSlotIndex(slot);
            return Number.isInteger(index) && index >= 0 && index < 3 && !this.fieldSlots(sideName)[index];
        },

        firstOpenFieldSlot(sideName) {
            return this.fieldSlots(sideName).findIndex((card) => !card);
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
                "player-energy",
                "player-max-energy",
                "player-deck-count",
                "player-discard-count",
                "bot-hp",
                "bot-hp-fill",
                "bot-energy",
                "bot-max-energy",
                "bot-deck-count",
                "bot-discard-count",
                "turn-number",
                "bot-profile-label",
            "bot-card",
            "focus-card",
            "player-battlefield",
            "bot-battlefield",
                "evolution-panel",
                "evolution-status",
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
                "tactics-strip",
                "ability-events",
                "reward-panel",
                "result-panel",
                "turn-log",
                "turn-log-panel",
                "turn-log-toggle",
                "phase-label",
                "guide-rule-label",
                "guide-rule-title",
                "guide-rule-copy",
                "guide-combine-label",
                "guide-combine-title",
                "guide-combine-copy",
                "coach-panel",
                "coach-badge",
                "coach-title",
                "coach-copy"
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
                    headers: {
                        "Content-Type": "application/json",
                        "X-Rebirth-CSRF": window.REBIRTH_CSRF || ""
                    },
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
            const safe = this.safeInsets();
            const navHeight = this.globalNavHeight();
            const safeWidth = Math.max(1, width - safe.left - safe.right);
            const safeHeight = Math.max(1, height - safe.top - safe.bottom - navHeight);
            const desktop = width >= 1180 && height >= 680;
            const baseWidth = desktop ? 1180 : RebirthConfig.boardWidth;
            const baseHeight = desktop ? 760 : RebirthConfig.boardHeight;
            document.documentElement.style.setProperty("--rb-board-width", `${baseWidth}px`);
            document.documentElement.style.setProperty("--rb-board-height", `${baseHeight}px`);
            document.documentElement.style.setProperty("--rb-safe-offset-x", `${(safe.left - safe.right) / 2}px`);
            document.documentElement.style.setProperty("--rb-safe-offset-y", `${(safe.top + navHeight - safe.bottom) / 2}px`);
            const scale = Math.min(safeWidth / baseWidth, safeHeight / baseHeight);
            document.documentElement.style.setProperty("--rb-scale", String(scale));
            window.scrollTo(0, 0);
        },

        globalNavHeight() {
            if (!document.body || !document.body.classList.contains("rb-game-page")) return 0;
            const nav = document.querySelector("[data-rebirth-global-nav]");
            return nav ? Math.ceil(nav.getBoundingClientRect().height) + 10 : 0;
        },

        safeInsets() {
            const styles = window.getComputedStyle(document.documentElement);
            const read = (name) => {
                const value = parseFloat(styles.getPropertyValue(name));
                return Number.isFinite(value) ? value : 0;
            };
            return {
                top: read("--rb-safe-top"),
                right: read("--rb-safe-right"),
                bottom: read("--rb-safe-bottom"),
                left: read("--rb-safe-left")
            };
        }
    };

    const RebirthStatus = {
        names(statuses) {
            return Object.keys(statuses || {}).filter((name) => {
                const status = statuses[name];
                return status && Number(status.turns || 0) !== 0;
            });
        },

        className(statuses) {
            const names = this.names(statuses);
            return names.map((name) => ` is-${String(name).toLowerCase()}`).join("");
        },

        badges(statuses) {
            const names = this.names(statuses);
            if (!names.length) return "";
            return '<div class="rb-status-strip">' + names.slice(0, 3).map((name) => {
                const status = statuses[name] || {};
                const turns = status.turns == null ? "" : " " + RebirthText.escape(status.turns);
                return '<span data-status="' + RebirthText.escape(name) + '">' + RebirthText.escape(name) + turns + "</span>";
            }).join("") + "</div>";
        },

        miniBadge(statuses) {
            const name = this.names(statuses)[0];
            return name ? '<span class="rb-mini-status">' + RebirthText.escape(name) + "</span>" : "";
        }
    };

    function renderTurnPhase(phase) {
        const phaseValue = String(phase || "MAIN_PHASE").toUpperCase();
        const phases = {
            DRAW_PHASE: { label: "Draw", tone: "draw", title: "Draw Phase" },
            MAIN_PHASE: { label: "Main", tone: "main", title: "Main Phase" },
            COMBAT_PHASE: { label: "Combat", tone: "combat", title: "Combat Phase" },
            END_PHASE: { label: "End", tone: "end", title: "End Phase" },
            CHOOSE: { label: "Main", tone: "main", title: "Main Phase" },
            RESULT: { label: "End", tone: "end", title: "End Phase" },
            FINISHED: { label: "Done", tone: "finished", title: "Match Finished" }
        };
        const meta = phases[phaseValue] || phases.MAIN_PHASE;
        const element = RebirthStore.elements["phase-label"];
        const board = RebirthStore.elements["rebirth-board"];
        if (element) {
            element.textContent = meta.label;
            element.classList.add("rb-turn-phase-pill");
            element.dataset.turnPhase = meta.tone;
            element.setAttribute("title", meta.title);
            element.setAttribute("aria-label", meta.title);
        }
        if (board) {
            board.dataset.turnPhase = meta.tone;
        }
        return meta;
    }

    const RebirthParallax = {
        selector: ".rb-tcg-card, .rb-mini-card, .rb-main-card, .rb-bot-card, .rb-card-back, .rb-field-card",
        bound: false,

        init() {
            const board = RebirthStore.elements["rebirth-board"];
            if (!board || this.bound) return;
            this.bound = true;
            board.addEventListener("pointermove", (event) => this.move(event), { passive: true });
            board.addEventListener("pointerleave", () => this.resetAll(), { passive: true });
            board.addEventListener("pointercancel", () => this.resetAll(), { passive: true });
            board.addEventListener("touchend", () => this.resetAll(), { passive: true });
        },

        move(event) {
            const card = event.target && event.target.closest ? event.target.closest(this.selector) : null;
            const board = RebirthStore.elements["rebirth-board"];
            if (!card || !board || !board.contains(card)) return;
            if (card.classList.contains("is-locked")) {
                this.reset(card);
                return;
            }
            const rect = card.getBoundingClientRect();
            if (!rect.width || !rect.height) return;
            const x = (event.clientX - rect.left) / rect.width;
            const y = (event.clientY - rect.top) / rect.height;
            const tiltY = (x - 0.5) * 12;
            const tiltX = (0.5 - y) * 12;
            card.style.setProperty("--tilt-x", `${tiltX.toFixed(2)}deg`);
            card.style.setProperty("--tilt-y", `${tiltY.toFixed(2)}deg`);
            card.style.setProperty("--glare-x", `${Math.round(x * 100)}%`);
            card.style.setProperty("--glare-y", `${Math.round(y * 100)}%`);
            card.classList.add("is-parallaxing");
        },

        reset(card) {
            if (!card) return;
            card.style.setProperty("--tilt-x", "0deg");
            card.style.setProperty("--tilt-y", "0deg");
            card.style.setProperty("--glare-x", "50%");
            card.style.setProperty("--glare-y", "50%");
            card.classList.remove("is-parallaxing");
        },

        resetAll() {
            const board = RebirthStore.elements["rebirth-board"];
            if (!board) return;
            board.querySelectorAll(this.selector).forEach((card) => this.reset(card));
        }
    };

    function triggerScreenShake(intensity) {
        const viewport = document.querySelector(".rb-game-viewport");
        const board = RebirthStore.elements["rebirth-board"];
        const target = viewport || board;
        const reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (!target || reducedMotion) return;
        const shake = Math.max(1, Number(intensity || 1));
        target.style.setProperty("--shake-intensity", `${shake}px`);
        target.style.setProperty("--shake-intensity-negative", `${shake * -1}px`);
        target.style.setProperty("--shake-intensity-soft", `${shake * 0.55}px`);
        target.style.setProperty("--shake-intensity-soft-negative", `${shake * -0.55}px`);
        target.classList.remove("is-screen-shaking");
        void target.offsetWidth;
        target.classList.add("is-screen-shaking");
        window.setTimeout(() => {
            target.classList.remove("is-screen-shaking");
        }, 420);
    }

    const RebirthAssets = {
        manifest: null,
        seen: new Set(),
        temporaryPools: {
            FIRE: [
                "https://images.unsplash.com/photo-1523861751938-121b5323b48b?auto=format&fit=crop&w=900&q=82",
                "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=900&q=82"
            ],
            WATER: [
                "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=900&q=82",
                "https://images.unsplash.com/photo-1439405326854-014607f694d7?auto=format&fit=crop&w=900&q=82"
            ],
            EARTH: [
                "https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=900&q=82",
                "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=82"
            ],
            SHADOW: [
                "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?auto=format&fit=crop&w=900&q=82",
                "https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=900&q=82"
            ],
            ARCANE: [
                "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?auto=format&fit=crop&w=900&q=82",
                "https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?auto=format&fit=crop&w=900&q=82"
            ],
            HIDDEN: [
                "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?auto=format&fit=crop&w=900&q=82",
                "https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=900&q=82"
            ]
        },

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
            const cardImage = this.cardImageUrl(card);
            if (cardImage) {
                this.preloadUrl(cardImage);
                return;
            }
            this.preloadUrl(this.temporaryArtUrl(card));
        },

        preloadState(state) {
            if (!state) return;
            ((state.player && state.player.hand) || []).forEach((card) => this.preloadCard(card));
            (state.player_field || (state.player && state.player.field) || (state.player && state.player.battlefield) || []).filter(Boolean).forEach((card) => this.preloadCard(card));
            (state.bot_field || (state.bot && state.bot.field) || (state.bot && state.bot.battlefield) || []).filter(Boolean).forEach((card) => this.preloadCard(card));
            this.preloadCard(state.player && state.player.played_card);
            this.preloadCard(state.bot && state.bot.played_card);
        },

        artStyle(card) {
            const background = this.artBackground(card);
            return background ? `style="${background}"` : "";
        },

        hexRgba(hex, alpha) {
            const match = String(hex || "").trim().match(/^#?([0-9a-f]{6})$/i);
            if (!match) return `rgba(244, 173, 38, ${alpha})`;
            const value = match[1];
            const red = parseInt(value.slice(0, 2), 16);
            const green = parseInt(value.slice(2, 4), 16);
            const blue = parseInt(value.slice(4, 6), 16);
            return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
        },

        artBackground(card) {
            const palette = card && card.palette ? card.palette : {};
            const accent = /^#[0-9a-f]{6}$/i.test(String(palette.accent || "")) ? palette.accent : "#f4ad26";
            const secondary = /^#[0-9a-f]{6}$/i.test(String(palette.secondary || "")) ? palette.secondary : "#58d6ff";
            const layers = [
                "linear-gradient(180deg, rgba(0, 0, 0, 0.02), rgba(0, 0, 0, 0.3))",
                `radial-gradient(circle at 50% 58%, ${this.hexRgba(accent, 0.42)}, rgba(0, 0, 0, 0) 58%)`,
                `linear-gradient(135deg, ${this.hexRgba(secondary, 0.18)}, rgba(0, 0, 0, 0) 64%)`
            ];
            const cardImage = this.cardImageUrl(card);
            if (cardImage) {
                layers.push(`url('${RebirthText.escape(cardImage)}')`);
            }
            const temporary = cardImage ? "" : this.temporaryArtUrl(card);
            if (temporary) {
                layers.push(`url('${RebirthText.escape(temporary)}')`);
            }
            if (!cardImage && RebirthConfig.assets.fallbackCardArt) {
                layers.push(`url('${RebirthText.escape(RebirthConfig.assets.fallbackCardArt)}')`);
            }
            return layers.length > 1 ? `background-image:${layers.join(",")}` : "";
        },

        cardImageUrl(card) {
            if (!card) return "";
            const manifestCards = (this.manifest && this.manifest.cards) || {};
            if (manifestCards[card.id]) {
                return manifestCards[card.id];
            }
            const digits = parseInt(String(card.id || "").replace(/\D/g, ""), 10);
            if (digits > 0) {
                return `/static/img/cards/baralho/${digits}.png`;
            }
            return card.art || RebirthConfig.assets.fallbackCardArt || "";
        },

        temporaryArtUrl(card) {
            if (!card) return "";
            const element = String(card.element || card.family || card.type || "").trim().toUpperCase();
            const family = String(card.family || "").trim().toUpperCase();
            const type = String(card.type || card.card_type || "").trim().toUpperCase();
            const key = this.temporaryPools[element]
                ? element
                : this.temporaryPools[family]
                    ? family
                    : type === "TRAP"
                        ? "HIDDEN"
                        : type === "SPELL"
                            ? "ARCANE"
                            : "SHADOW";
            const pool = this.temporaryPools[key] || this.temporaryPools.SHADOW;
            const digits = parseInt(String(card.id || card.instance_id || "0").replace(/\D/g, ""), 10) || 0;
            return pool[Math.max(0, digits - 1) % pool.length];
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
            const source = this.cardImageUrl(card);
            if (!source) return "";
            const fallback = this.temporaryArtUrl(card) || RebirthConfig.assets.fallbackCardArt || "";
            return `<img data-rebirth-art data-art-key="${RebirthText.escape(card && card.art_key ? card.art_key : "fallback")}" data-fallback-src="${RebirthText.escape(fallback)}" src="${RebirthText.escape(source)}" alt="" loading="eager">`;
        },

        bindFallbacks(root) {
            const host = root || document;
            host.querySelectorAll("img[data-rebirth-art]").forEach((image) => {
                image.addEventListener("error", () => {
                    const frame = image.closest(".rb-card-art, .rb-mini-art, .rb-field-art, .rb-evolution-thumb");
                    const fallback = image.dataset.fallbackSrc || "";
                    if (frame) {
                        frame.classList.add("rb-temp-art");
                    }
                    if (fallback && image.dataset.fallbackApplied !== "true") {
                        image.dataset.fallbackApplied = "true";
                        image.src = fallback;
                        return;
                    }
                    image.hidden = true;
                    if (frame) {
                        frame.classList.add("rb-asset-fallback");
                    }
                }, { once: true });
            });
        }
    };

    const RebirthMarkup = {
        cardTierName(card) {
            return Number(card && card.tier || 1) > 1 ? "Apex" : "Base";
        },

        cardRole(card) {
            const attack = Number(card && (card.attack || card.power) || 0);
            const guard = Number(card && card.guard || 0);
            const ability = String(card && card.ability_key || "");
            if (Number(card && card.tier || 1) > 1) return "Finisher";
            if (ability.includes("guard") || ability === "brace" || ability === "bulwark" || guard >= attack + 2) return "Sentinel";
            if (attack >= 7 || ability.includes("bite") || ability.includes("rend")) return "Striker";
            if (ability.includes("fade") || ability.includes("pursuit") || ability.includes("mark")) return "Tempo";
            return "Duelist";
        },

        card(card, statuses) {
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
                ${RebirthStatus.badges(statuses)}
                <div class="rb-card-rule">
                    <strong>${RebirthText.escape(card.ability_name || "Clash")}</strong>
                    <p>${RebirthText.escape(card.ability_text || card.flavor)}</p>
                    <div class="rb-card-tags">
                        <span>${RebirthText.escape(this.cardTierName(card))}</span>
                        <span>${RebirthText.escape(card.element || "Void")}</span>
                        <span>${RebirthText.escape(this.cardRole(card))}</span>
                    </div>
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
            const recommended = options && options.recommended ? " is-recommended" : "";
            const locked = options && options.locked ? " is-locked" : "";
            const lockedReason = options && options.lockedReason ? String(options.lockedReason) : "";
            const disabled = locked ? `disabled aria-disabled="true" title="${RebirthText.escape(lockedReason)}"` : "";
            const statuses = options && options.statuses ? options.statuses : null;
            const statusClass = RebirthStatus.className(statuses);
            return `
                <button class="${this.cardShellClasses(card, "rb-mini-card")}${selected}${recommended}${locked}${statusClass}" type="button" data-card-instance="${RebirthText.escape(card.instance_id)}" data-art-key="${RebirthText.escape(card.art_key || card.id)}" style="${RebirthAssets.cssVars(card)}" aria-pressed="${selected ? "true" : "false"}" aria-label="${lockedReason ? RebirthText.escape(lockedReason) + ". " : ""}Select ${RebirthText.escape(card.name)}, attack ${RebirthText.escape(card.attack)}, guard ${RebirthText.escape(card.guard)}" ${disabled}>
                    <span class="rb-card-frame-layer" aria-hidden="true"></span>
                    <b class="rb-card-cost">${RebirthText.escape(this.cardCost(card))}</b>
                    ${RebirthStatus.miniBadge(statuses)}
                    <div class="rb-card-titlebar rb-mini-copy rb-card-hud-layer">
                        <strong class="rb-card-nameplate">${RebirthText.escape(card.name)}</strong>
                        <span>${RebirthText.escape(card.element)} - T${RebirthText.escape(card.tier)}</span>
                    </div>
                    <span class="rb-card-image-layer rb-mini-art">
                        ${RebirthAssets.imageMarkup(card)}
                    </span>
                    <div class="rb-card-statline rb-mini-stats rb-card-hud-layer">
                        <span class="rb-card-stat is-atk"><b>${RebirthText.escape(card.attack || card.power)}</b><small>ATK</small></span>
                        <span class="rb-card-stat is-guard"><b>${RebirthText.escape(card.guard || 0)}</b><small>GUARD</small></span>
                    </div>
                </button>
            `;
        },

        cardCost(card) {
            const type = String((card && (card.type || card.card_type)) || "MONSTER").toUpperCase();
            if (type === "MONSTER") {
                return Math.max(1, Math.min(10, Number(card.cost || card.tier || 1)));
            }
            return Math.max(0, Number(card && card.cost || 0));
        },

        cardType(card) {
            return String((card && (card.type || card.card_type)) || "MONSTER").toUpperCase();
        },

        isMonster(card) {
            return this.cardType(card) === "MONSTER";
        },

        elementClass(card) {
            const element = String((card && (card.element || card.family)) || "Shadow").trim().toLowerCase();
            const safeElement = element.replace(/[^a-z0-9-]/g, "-") || "shadow";
            return ` is-element-${safeElement}`;
        },

        rarityClass(card) {
            const rarity = String((card && card.rarity) || "COMMON").trim().toLowerCase();
            const safeRarity = rarity.replace(/[^a-z0-9-]/g, "-") || "common";
            const premium = ["rare", "epic", "legendary", "mythic"].includes(safeRarity) ? " is-premium-rarity" : "";
            return ` is-rarity-${safeRarity}${premium}`;
        },

        cardShellClasses(card, baseClass) {
            const evolved = Number(card && card.tier || 1) > 1 ? " is-evolved" : "";
            return `${baseClass} rb-tcg-card${this.elementClass(card)}${this.rarityClass(card)}${evolved}`;
        },

        fieldCard(card, side, selected, statuses) {
            const guard = Number(card.current_guard != null ? card.current_guard : card.guard || 0);
            const maxGuard = Number(card.max_guard || card.guard || 1);
            const guardScale = Math.max(0, Math.min(1, guard / maxGuard));
            const exhausted = card.exhausted || card.has_attacked ? " is-exhausted" : "";
            const selectedClass = selected ? " is-selected" : "";
            const statusClass = RebirthStatus.className(statuses);
            const targetAttr = side === "bot"
                ? `data-target-instance="${RebirthText.escape(card.instance_id)}"`
                : `data-attacker-instance="${RebirthText.escape(card.instance_id)}"`;
            return `
                <button class="${this.cardShellClasses(card, "rb-field-card rb-monster-card")}${selectedClass}${exhausted}${statusClass}" type="button" ${targetAttr} data-art-key="${RebirthText.escape(card.art_key || card.id)}" style="${RebirthAssets.cssVars(card)}; --guard-scale: ${guardScale}" aria-label="${RebirthText.escape(card.name)} on ${side} battlefield">
                    <span class="rb-card-frame-layer" aria-hidden="true"></span>
                    ${RebirthStatus.miniBadge(statuses)}
                    <b class="rb-card-cost">${RebirthText.escape(this.cardCost(card))}</b>
                    <span class="rb-card-titlebar rb-card-hud-layer">
                        <strong class="rb-card-nameplate">${RebirthText.escape(card.name)}</strong>
                        <small>${RebirthText.escape(card.element || card.family || "Void")} - T${RebirthText.escape(card.tier || 1)}</small>
                    </span>
                    <span class="rb-card-image-layer rb-field-art">
                        ${RebirthAssets.imageMarkup(card)}
                    </span>
                    <span class="rb-card-statline">
                        <span class="rb-card-stat is-atk"><b>${RebirthText.escape(card.attack || card.power)}</b><small>ATK</small></span>
                        <span class="rb-card-stat is-guard"><b>${RebirthText.escape(guard)}</b><small>GUARD</small></span>
                    </span>
                    <i class="rb-guard-meter" aria-label="${RebirthText.escape(guard)}/${RebirthText.escape(maxGuard)} Guard"></i>
                </button>
            `;
        },

        emptyFieldSlot(copy, options) {
            const direct = options && options.direct;
            const summonSlot = options && options.summonSlot;
            const summonTarget = options && options.summonTarget ? " is-summon-target" : "";
            const selected = options && options.selected ? " is-selected" : "";
            const locked = options && options.locked ? " is-locked" : "";
            const disabled = locked && !direct ? "disabled aria-disabled=\"true\"" : "";
            const slotAttr = Number.isInteger(summonSlot) && summonTarget ? `data-summon-slot="${summonSlot}"` : "";
            return `<button class="rb-field-slot-empty${summonTarget}${selected}${locked}" type="button" ${direct ? "data-direct-attack=\"true\"" : ""} ${slotAttr} ${disabled}><span>${RebirthText.escape(copy)}</span></button>`;
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
                    <strong>Living Battle Zone</strong>
                    <p>Summoned monsters stay until their Guard is broken.</p>
                </div>
                <div class="rb-card-stats">
                    <span><i class="rb-stat-sword"></i><b>0</b></span>
                    <span><i class="rb-stat-crest"></i></span>
                    <span><i class="rb-stat-shield"></i><b>0</b></span>
                </div>
            `;
        }
    };

    const RebirthTactics = {
        botIntent(profile) {
            const id = profile && profile.id;
            if (id === "aggressive") {
                return { label: "Pressure", copy: "Likely to race attack and force quick HP trades.", tone: "danger" };
            }
            if (id === "opportunist") {
                return { label: "Trap Window", copy: "Likely to chase ability value when the line opens.", tone: "warning" };
            }
            return { label: "Guard Line", copy: "Likely to absorb first and punish low attack.", tone: "guard" };
        },

        selectedRead(card) {
            if (!card) {
                return { label: "No Card", copy: "Select a monster to see tempo, role and risk." };
            }
            const attack = Number(card.attack || card.power || 0);
            const guard = Number(card.guard || 0);
            const tempo = attack * 2 + guard + Number(card.tier || 1) * 3;
            const role = RebirthMarkup.cardRole(card);
            const label = tempo >= 25 ? "Power Line" : tempo >= 18 ? "Stable Line" : "Setup Line";
            return {
                label,
                copy: `${role}: ${attack} attack / ${guard} guard. Tempo ${tempo}.`
            };
        },

        advantage(state) {
            if (!state) return { label: "Even", copy: "Match not loaded." };
            const hpDelta = Number(state.player.hp || 0) - Number(state.bot.hp || 0);
            const handDelta = Number((state.player.hand || []).length) - Number(state.bot.hand_count || 0);
            const deckDelta = Number(state.player.deck_count || 0) - Number(state.bot.deck_count || 0);
            const score = hpDelta + handDelta * 2 + deckDelta;
            if (score >= 6) return { label: "Advantage", copy: `You lead by ${score} tempo.` };
            if (score <= -6) return { label: "Under Fire", copy: `Bot leads by ${Math.abs(score)} tempo.` };
            return { label: "Even Board", copy: "HP, hand and deck pressure are close." };
        }
    };

    const RebirthFeel = {
        reducedMotion() {
            return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        },

        resultSignature(state) {
            if (!state || !state.result || !state.last_clash) return "";
            const player = state.last_clash.player_card || {};
            const bot = state.last_clash.bot_card || {};
            return [state.turn, state.result.outcome, player.instance_id || player.id, bot.instance_id || bot.id].join(":");
        },

        impactCard(state) {
            const clash = (state && state.last_clash) || {};
            const result = (state && state.result) || {};
            if (result.winner === "bot") return clash.bot_card || null;
            if (result.winner === "player") return clash.player_card || null;
            return clash.player_card || clash.bot_card || null;
        },

        accent(card) {
            return (card && card.palette && card.palette.accent) || "#f4ad26";
        },

        abilityKey(card) {
            return (card && card.ability_key) || "base_clash";
        },

        pulse(state) {
            const panel = RebirthStore.elements["result-panel"];
            const focus = RebirthStore.elements["focus-card"];
            const bot = RebirthStore.elements["bot-card"];
            const card = this.impactCard(state);
            const key = this.abilityKey(card);
            const accent = this.accent(card);

            [panel, focus, bot].forEach((element) => {
                if (!element) return;
                element.classList.remove("is-impacting");
                element.style.setProperty("--impact-accent", accent);
                element.setAttribute("data-ability-key", key);
            });
            if (panel) {
                panel.setAttribute("data-outcome", (state.result && state.result.outcome) || "Clash");
                panel.classList.add("is-impacting");
            }
            if (focus) focus.classList.add("is-impacting");
            if (bot) bot.classList.add("is-impacting");

            window.setTimeout(() => {
                [panel, focus, bot].forEach((element) => {
                    if (element) element.classList.remove("is-impacting");
                });
            }, 620);

            this.haptics(state.result);
            this.tone(card, state.result);
            this.screenShake(state.result);
        },

        haptics(result) {
            if (this.reducedMotion() || !navigator.vibrate || !result) return;
            if (result.outcome === "Clash") {
                navigator.vibrate(18);
            } else {
                navigator.vibrate([18, 24, 18]);
            }
        },

        tone(card, result) {
            if (this.reducedMotion() || !window.AudioContext || !result) return;
            try {
                const context = new window.AudioContext();
                const oscillator = context.createOscillator();
                const gain = context.createGain();
                const key = this.abilityKey(card);
                const base = result.outcome === "Defeat" ? 154 : result.outcome === "Clash" ? 220 : 330;
                oscillator.frequency.value = base + (key.length % 7) * 24;
                oscillator.type = "triangle";
                gain.gain.setValueAtTime(0.0001, context.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.035, context.currentTime + 0.018);
                gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.16);
                oscillator.connect(gain);
                gain.connect(context.destination);
                oscillator.start();
                oscillator.stop(context.currentTime + 0.18);
                oscillator.addEventListener("ended", () => context.close());
            } catch (_error) {}
        },

        screenShake(result) {
            if (!result || this.reducedMotion()) return;
            const damage = result.damage || {};
            const playerDamage = Number(damage.player || 0);
            const botDamage = Number(damage.bot || 0);
            const totalDamage = Math.max(0, playerDamage) + Math.max(0, botDamage);
            if (!totalDamage) return;
            triggerScreenShake(Math.min(10, 2 + totalDamage));
        }
    };

    const RebirthCoach = {
        progression() {
            return (RebirthConfig.player && RebirthConfig.player.progression) || {};
        },

        account() {
            return (RebirthConfig.player && RebirthConfig.player.account) || {};
        },

        shouldGuideFirstMatch() {
            const params = new URLSearchParams(window.location.search || "");
            const progress = this.progression();
            return Boolean(
                params.has("firstRun") ||
                params.has("tutorial") ||
                (this.account().authenticated && !progress.tutorial_complete && Number(progress.clashes || 0) === 0)
            );
        },

        score(card) {
            if (!card) return -1;
            const ability = {
                inferno_bite: 8,
                apex_rend: 7,
                molten_bite: 6,
                rending_strike: 5,
                silent_pursuit: 5,
                storm_dive: 5,
                high_guard: 4,
                bleed_mark: 4,
                fade_cut: 3,
                fortress_hit: 3,
                immovable: 2,
                bulwark: 2,
                brace: 1
            }[card.ability_key] || 0;
            return Number(card.attack || card.power || 0) * 3 + Number(card.guard || 0) + Number(card.tier || 1) * 4 + ability;
        },

        recommendedCard() {
            const hand = (RebirthStore.state && RebirthStore.state.player && RebirthStore.state.player.hand) || [];
            if (!hand.length) return null;
            return hand.slice().sort((a, b) => {
                return this.score(b) - this.score(a) || String(a.name).localeCompare(String(b.name));
            })[0];
        },

        insight() {
            const state = RebirthStore.state;
            if (!state) {
                return { badge: "Coach", title: "Loading arena.", copy: "Preparing your first hand." };
            }
            if (!this.account().authenticated) {
                return {
                    badge: "Visitante",
                    title: "A mesa esta liberada.",
                    copy: "Use Login / Registro no topo quando quiser guardar colecao e recompensas."
                };
            }
            if (state.is_finished) {
                const won = state.winner === "player";
                return {
                    badge: won ? "Victory" : "Next",
                    title: won ? "Lock in the reward." : "Review the reward, then rebuild.",
                    copy: "Open Rewards for XP progress, or Cards to tune your loadout before the next match."
                };
            }
            if (state.phase === "result") {
                const reward = RebirthStore.reward;
                if (reward && reward.daily && reward.daily.ready) {
                    return { badge: "Reward", title: "Daily reward is ready.", copy: "After this match, claim the daily XP on Rewards." };
                }
                return { badge: "Read", title: "Read the result before moving.", copy: "The log explains damage, ability triggers and why combat resolved that way." };
            }
            const evolution = RebirthStore.firstEvolution();
            const selected = RebirthStore.selectedCard();
            const recommended = this.recommendedCard();
            if (evolution && (!selected || selected.id === evolution.card_id)) {
                return {
                    badge: "Evolve",
                    title: "Evolve now for a stronger line.",
                    copy: `${evolution.name} x${evolution.count} can merge before you commit. That usually adds attack, guard and pressure.`
                };
            }
            if (!selected) {
                return { badge: "Choose", title: "Pick a card or attacker.", copy: "Summon from hand, or select a ready monster on the field to declare an attack." };
            }
            if (recommended && selected.instance_id === recommended.instance_id) {
                return {
                    badge: "Good",
                    title: `${selected.name} is the clean read.`,
                    copy: `Best pressure in hand: ${selected.attack} attack, ${selected.guard} guard. Commit it unless you want to bait with defense.`
                };
            }
            if (RebirthStore.selectedAttackerId) {
                return {
                    badge: "Attack",
                    title: `${selected.name} is ready.`,
                    copy: "Click a bot defender to attack it, or click the bot HP lane if the field is clear."
                };
            }
            if (Number(selected.guard || 0) <= 2) {
                return {
                    badge: "Risky",
                    title: `${selected.name} can get punished.`,
                    copy: "Low guard hits fast, but it can fold if the bot answers with a bigger attack."
                };
            }
            if (Number(selected.attack || 0) <= 3) {
                return {
                    badge: "Risky",
                    title: `${selected.name} may stall into high guard.`,
                    copy: "Defensive cards reduce damage, but they usually need an ability trigger or wounded target to swing the turn."
                };
            }
            return {
                badge: "Plan",
                title: `${selected.name} is playable.`,
                copy: recommended ? `${recommended.name} has a stronger projected line, but this card can still set up pressure.` : "Commit when the attack and guard fit your plan."
            };
        }
    };

    const RebirthRenderer = {
        render() {
            if (!RebirthStore.state) return;
            const state = RebirthStore.state;
            const board = RebirthStore.elements["rebirth-board"];
            if (board) {
                board.dataset.phase = state.phase;
                board.dataset.winner = state.winner || "";
                board.dataset.botProfile = (state.bot_profile && state.bot_profile.id) || "defensive";
            }
            renderTurnPhase(state.turn_phase || state.phase);
            RebirthAssets.preloadState(state);
            RebirthDom.setText("player-hp", state.player.hp);
            RebirthDom.setText("bot-hp", state.bot.hp);
            RebirthDom.setText("player-energy", state.player.energy);
            RebirthDom.setText("player-max-energy", state.player.max_energy);
            RebirthDom.setText("bot-energy", state.bot.energy);
            RebirthDom.setText("bot-max-energy", state.bot.max_energy);
            RebirthDom.setText("player-deck-count", `Deck ${state.player.deck_count || 0}`);
            RebirthDom.setText("player-discard-count", `Void ${state.player.discard_count || 0}`);
            RebirthDom.setText("bot-deck-count", `Deck ${state.bot.deck_count || 0}`);
            RebirthDom.setText("bot-discard-count", `Void ${state.bot.discard_count || 0}`);
            RebirthDom.setText("turn-number", String(state.turn).padStart(2, "0"));
            RebirthDom.setText("bot-profile-label", (state.bot_profile && state.bot_profile.name) || "Bot Profile");
            this.hpBars();
            this.battlefield();
            this.focusCard();
            this.botCard();
            this.evolutionPanel();
            this.hand();
            this.coach();
            this.result();
            this.tactics();
            this.guide();
            this.log();
            this.buttons();
            RebirthAssets.bindFallbacks(RebirthStore.elements["rebirth-board"]);
            RebirthParallax.resetAll();
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

        battlefield() {
            const playerHost = RebirthStore.elements["player-battlefield"];
            const botHost = RebirthStore.elements["bot-battlefield"];
            const state = RebirthStore.state;
            if (!playerHost || !botHost || !state) return;
            const playerSlots = RebirthStore.fieldSlots("player");
            const botSlots = RebirthStore.fieldSlots("bot");
            const botCards = RebirthStore.fieldCards("bot");
            const playerStatuses = (state.player && state.player.statuses) || {};
            const botStatuses = (state.bot && state.bot.statuses) || {};
            const selectedHandCard = RebirthStore.handCard(RebirthStore.selectedInstanceId);
            const selectedCost = RebirthMarkup.cardCost(selectedHandCard);
            const selectedEnergy = Number((state.player && state.player.energy) || 0);
            const summonLockCopy = !selectedHandCard
                ? "Select Card"
                : selectedEnergy < selectedCost
                    ? "No Mana"
                    : state.phase !== "choose" || state.is_finished || RebirthStore.pending
                        ? "Locked"
                        : "Open Slot";
            const canSummonSelected = selectedHandCard
                && RebirthMarkup.isMonster(selectedHandCard)
                && state.phase === "choose"
                && !state.is_finished
                && !RebirthStore.pending
                && selectedEnergy >= selectedCost;
            playerHost.innerHTML = playerSlots.map((card, index) => {
                if (card) {
                    return RebirthMarkup.fieldCard(card, "player", card.instance_id === RebirthStore.selectedAttackerId, playerStatuses);
                }
                return RebirthMarkup.emptyFieldSlot(canSummonSelected ? `Slot ${index + 1}` : summonLockCopy, {
                    summonSlot: index,
                    summonTarget: Boolean(canSummonSelected),
                    selected: RebirthStore.selectedSummonSlot === index,
                    locked: !canSummonSelected
                });
            }).join("");
            botHost.innerHTML = botSlots.map((card, index) => {
                if (card) {
                    return RebirthMarkup.fieldCard(card, "bot", false, botStatuses);
                }
                return RebirthMarkup.emptyFieldSlot(botCards.length ? "Guard Line" : (index === 1 ? "Direct HP" : "No Defender"), {
                    direct: !botCards.length && index === 1
                });
            }).join("");
        },

        focusCard() {
            const host = RebirthStore.elements["focus-card"];
            if (!host) return;
            const card = RebirthStore.selectedCard();
            if (!card) {
                host.className = "rb-main-card rb-monster-card rb-monster-card-main rb-empty-card";
                host.removeAttribute("data-element");
                host.removeAttribute("data-art-key");
                host.removeAttribute("data-statuses");
                host.removeAttribute("style");
                host.innerHTML = RebirthMarkup.emptyFocus();
                return;
            }
            const statuses = (RebirthStore.state.player && RebirthStore.state.player.statuses) || {};
            host.className = `rb-main-card rb-monster-card rb-monster-card-main${Number(card.tier || 1) > 1 ? " is-evolved" : ""}${RebirthStatus.className(statuses)}`;
            host.setAttribute("data-element", card.element);
            host.setAttribute("data-art-key", card.art_key || card.id);
            host.setAttribute("data-statuses", RebirthStatus.names(statuses).join(" "));
            host.setAttribute("style", RebirthAssets.cssVars(card));
            host.innerHTML = RebirthMarkup.card(card, statuses);
        },

        botCard() {
            const host = RebirthStore.elements["bot-card"];
            if (!host) return;
            const card = RebirthStore.state.bot.played_card;
            if (!card) {
                host.className = "rb-bot-card rb-card-back";
                host.removeAttribute("data-element");
                host.removeAttribute("data-art-key");
                host.removeAttribute("data-statuses");
                host.removeAttribute("style");
                host.innerHTML = "<span>Bot's Card</span>";
                return;
            }
            const statuses = (RebirthStore.state.bot && RebirthStore.state.bot.statuses) || {};
            host.className = `rb-bot-card rb-monster-card rb-bot-revealed${RebirthStatus.className(statuses)}`;
            host.setAttribute("data-element", card.element);
            host.setAttribute("data-art-key", card.art_key || card.id);
            host.setAttribute("data-statuses", RebirthStatus.names(statuses).join(" "));
            host.setAttribute("style", RebirthAssets.cssVars(card));
            host.innerHTML = RebirthMarkup.card(card, statuses);
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
                RebirthDom.setText("evolution-status", RebirthStore.state.phase === "choose" ? "No Duplicate" : "Locked");
                RebirthDom.setText("evolution-name", "No duplicate");
                if (thumb) {
                    thumb.style.backgroundImage = "";
                    thumb.classList.add("rb-asset-fallback");
                }
                return;
            }

            RebirthDom.setText("evolution-status", "Duplicate Found");
            RebirthDom.setText("evolution-name", `${evolution.name} x${evolution.count}`);
            const sourceCard = (RebirthStore.state.player.hand || []).find((card) => card.id === evolution.card_id);
            if (thumb && sourceCard) {
                thumb.classList.remove("rb-asset-fallback");
                thumb.setAttribute("style", `${RebirthAssets.artBackground(sourceCard)}; --card-accent: ${(sourceCard.palette && sourceCard.palette.accent) || "#f4ad26"}`);
                thumb.style.setProperty("--card-accent", (sourceCard.palette && sourceCard.palette.accent) || "#f4ad26");
            }
        },

        hand() {
            const host = RebirthStore.elements["player-hand"];
            if (!host) return;
            const state = RebirthStore.state;
            const hand = RebirthStore.state.player.hand || [];
            const recommended = RebirthCoach.recommendedCard();
            RebirthDom.setText("hand-count", `${hand.length} cards`);
            const canChoose = state.phase === "choose" && !state.is_finished && !RebirthStore.pending;
            const energy = Number((state.player && state.player.energy) || 0);
            const hasOpenSlot = RebirthStore.firstOpenFieldSlot("player") >= 0;
            host.innerHTML = hand.map((card) => RebirthMarkup.miniCard(card, {
                selected: card.instance_id === RebirthStore.selectedInstanceId,
                recommended: recommended && card.instance_id === recommended.instance_id,
                statuses: card.instance_id === RebirthStore.selectedInstanceId ? RebirthStore.state.player.statuses : null,
                locked: !canChoose || energy < RebirthMarkup.cardCost(card) || (RebirthMarkup.isMonster(card) && !hasOpenSlot),
                lockedReason: !canChoose
                    ? "Action unavailable outside your main phase"
                    : energy < RebirthMarkup.cardCost(card)
                        ? `Not enough mana: needs ${RebirthMarkup.cardCost(card)}`
                        : RebirthMarkup.isMonster(card) && !hasOpenSlot
                            ? "No empty monster slot"
                            : ""
            })).join("");
        },

        coach() {
            const panel = RebirthStore.elements["coach-panel"];
            if (!panel) return;
            const insight = RebirthCoach.insight();
            panel.dataset.coachTone = String(insight.badge || "Coach").toLowerCase();
            RebirthDom.setText("coach-badge", insight.badge || "Coach");
            RebirthDom.setText("coach-title", insight.title || "Build your field.");
            RebirthDom.setText("coach-copy", insight.copy || "I will call out the safest line before you commit.");
        },

        result() {
            const state = RebirthStore.state;
            const result = state.result;
            const panel = RebirthStore.elements["result-panel"];
            if (panel) {
                panel.classList.remove("is-victory", "is-defeat", "is-clash");
            }
            this.abilityEvents(result);
            this.rewardPanel();
            if (state.is_finished) {
                const won = state.winner === "player";
                const tied = state.winner === "clash";
                if (panel) {
                    panel.classList.add(tied ? "is-clash" : won ? "is-victory" : "is-defeat");
                }
                RebirthDom.setText("result-label", tied ? "Clash" : won ? "Victory" : "Defeat");
                RebirthDom.setText("result-title", tied ? "Both sides fell." : won ? "You won the duel." : "Bot won the duel.");
                RebirthDom.setText("result-copy", result && result.message ? result.message : "Start a new match when ready.");
                this.resultImpact();
                return;
            }
            if (result) {
                if (panel) {
                    panel.classList.add(`is-${String(result.outcome || "clash").toLowerCase()}`);
                }
                RebirthDom.setText("result-label", result.outcome);
                RebirthDom.setText("result-title", result.outcome === "Clash" ? "No damage." : result.outcome);
                RebirthDom.setText("result-copy", result.message);
                this.resultImpact();
                return;
            }
            RebirthStore.lastResultSignature = null;
            RebirthDom.setText("result-label", "Waiting");
            RebirthDom.setText("result-title", "Build your field.");
            RebirthDom.setText("result-copy", "Summon monsters, then select a ready ally and choose its target.");
        },

        tactics() {
            const host = RebirthStore.elements["tactics-strip"];
            const state = RebirthStore.state;
            if (!host || !state) return;
            const selected = RebirthStore.selectedCard();
            const intent = RebirthTactics.botIntent(state.bot_profile || {});
            const read = RebirthTactics.selectedRead(selected);
            const advantage = RebirthTactics.advantage(state);
            const botHand = state.bot.hand_count == null ? "?" : state.bot.hand_count;
            host.dataset.intentTone = intent.tone;
            host.innerHTML = [
                `<span><b>${RebirthText.escape(intent.label)}</b>${RebirthText.escape(intent.copy)}</span>`,
                `<span><b>${RebirthText.escape(read.label)}</b>${RebirthText.escape(read.copy)}</span>`,
                `<span><b>${RebirthText.escape(advantage.label)}</b>${RebirthText.escape(advantage.copy)}</span>`,
                `<span><b>Enemy Hand</b>${RebirthText.escape(botHand)} hidden cards</span>`
            ].join("");
        },

        guide() {
            const state = RebirthStore.state;
            const result = state && state.result;
            const evolution = RebirthStore.firstEvolution();
            if (!state) return;

            if (state.is_finished) {
                const title = state.winner === "player" ? "Duel secured" : state.winner === "bot" ? "Bot secured it" : "Final clash";
                RebirthDom.setText("guide-rule-label", "Match");
                RebirthDom.setText("guide-rule-title", title);
                RebirthDom.setText("guide-rule-copy", result && result.message ? result.message : "Start a new match when ready.");
                RebirthDom.setText("guide-combine-label", "Next");
                RebirthDom.setText("guide-combine-title", "New match");
                RebirthDom.setText("guide-combine-copy", "The current duel is locked. Start fresh to test another line.");
                return;
            }

            if (result) {
                const events = result.ability_events || [];
                RebirthDom.setText("guide-rule-label", "Result");
                RebirthDom.setText("guide-rule-title", result.outcome === "Clash" ? "No damage" : result.outcome);
                RebirthDom.setText("guide-rule-copy", result.message || "Advance to the next turn.");
                RebirthDom.setText("guide-combine-label", events.length ? "Ability" : "Next");
                RebirthDom.setText("guide-combine-title", events.length ? "Triggered" : "Next turn");
                RebirthDom.setText("guide-combine-copy", events.length ? events[0] : "Advance to refill hands and continue the duel.");
                return;
            }

            RebirthDom.setText("guide-rule-label", "Rule");
            RebirthDom.setText("guide-rule-title", "Summon and attack");
            RebirthDom.setText("guide-rule-copy", "Monsters stay on the field until their Guard reaches zero.");
            RebirthDom.setText("guide-combine-label", evolution ? "Combine Ready" : "Combine");
            RebirthDom.setText("guide-combine-title", evolution ? `${evolution.name} x${evolution.count}` : "Duplicates evolve");
            RebirthDom.setText("guide-combine-copy", evolution ? "Merge the pair now, or keep both bodies for later pressure." : "Two matching monsters merge into their Rebirth form.");
        },

        resultImpact() {
            const signature = RebirthFeel.resultSignature(RebirthStore.state);
            if (!signature || signature === RebirthStore.lastResultSignature) return;
            RebirthStore.lastResultSignature = signature;
            RebirthFeel.pulse(RebirthStore.state);
        },

        abilityEvents(result) {
            const host = RebirthStore.elements["ability-events"];
            if (!host) return;
            const events = (result && result.ability_events) || [];
            if (!result) {
                host.innerHTML = "";
                return;
            }
            if (!events.length) {
                host.innerHTML = '<span class="rb-ability-chip is-muted">Base combat</span>';
                return;
            }
            host.innerHTML = events.slice(0, 2).map((event) => {
                return '<span class="rb-ability-chip">' + RebirthText.escape(event) + "</span>";
            }).join("");
        },

        rewardPanel() {
            const host = RebirthStore.elements["reward-panel"];
            if (!host) return;
            const reward = RebirthStore.reward;
            if (!reward) {
                host.innerHTML = "";
                host.hidden = true;
                return;
            }
            host.hidden = false;
            if (!reward.persisted) {
                host.innerHTML = '<span class="rb-reward-muted">' + RebirthText.escape(reward.message) + "</span>";
                return;
            }
            const achievements = (reward.achievements || []).map((item) => item.name).join(", ");
            const dailyLabel = reward.daily && reward.daily.state === "claimed"
                ? "Daily claimed"
                : reward.daily && reward.daily.ready
                    ? "Daily ready"
                    : "";
            const nextLabel = reward.xp_to_next != null
                ? RebirthText.escape(reward.xp_to_next) + " XP to next level"
                : "";
            host.innerHTML = [
                '<span class="rb-reward-xp">+' + RebirthText.escape(reward.xp) + " XP</span>",
                "<span>Level " + RebirthText.escape(reward.level) + (reward.level_up ? " up" : "") + "</span>",
                nextLabel ? "<span>" + nextLabel + "</span>" : "",
                achievements ? "<span>" + RebirthText.escape(achievements) + "</span>" : "",
                dailyLabel ? '<span class="rb-reward-daily">' + RebirthText.escape(dailyLabel) + "</span>" : "",
                reward.next_goal ? "<span>" + RebirthText.escape(reward.next_goal) + "</span>" : ""
            ].join("");
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
            const canNext = (state.phase === "result" || state.phase === "choose") && !state.is_finished && !RebirthStore.pending;
            const evolution = RebirthStore.firstEvolution();
            const selected = RebirthStore.selectedInstanceId
                ? (state.player.hand || []).find((card) => card.instance_id === RebirthStore.selectedInstanceId)
                : null;
            const selectedAttacker = RebirthStore.selectedAttackerId
                ? RebirthStore.fieldCard(RebirthStore.selectedAttackerId)
                : null;
            const energy = Number((state.player && state.player.energy) || 0);
            const cost = selected ? RebirthMarkup.cardCost(selected) : 0;
            const canPay = !selected || energy >= cost;
            const attackerReady = selectedAttacker && !selectedAttacker.exhausted && !selectedAttacker.has_attacked;
            if (RebirthStore.elements["play-button"]) {
                if (selectedAttacker) {
                    RebirthStore.elements["play-button"].innerHTML = '<i class="rb-action-sword"></i>Attack';
                    RebirthStore.elements["play-button"].disabled = !canChoose || !attackerReady;
                } else {
                    const emptySlot = RebirthStore.firstOpenFieldSlot("player");
                    const isMonster = selected && RebirthMarkup.isMonster(selected);
                    RebirthStore.elements["play-button"].innerHTML = `<i class="rb-action-sword"></i>${isMonster ? "Summon Slot" : "Play"}${selected ? ` ${cost}` : ""}`;
                    RebirthStore.elements["play-button"].disabled = !canChoose || !RebirthStore.selectedInstanceId || !canPay || (isMonster && emptySlot < 0);
                }
            }
            if (RebirthStore.elements["next-turn-button"]) {
                if (state.phase === "result") {
                    RebirthStore.elements["next-turn-button"].innerHTML = '<i class="rb-action-loop"></i>Next Turn';
                    RebirthStore.elements["next-turn-button"].disabled = !canNext;
                    RebirthDom.setText("secondary-action-copy", "Ready your battlefield");
                } else if (state.is_finished) {
                    RebirthStore.elements["next-turn-button"].innerHTML = '<i class="rb-action-loop"></i>Finished';
                    RebirthStore.elements["next-turn-button"].disabled = true;
                    RebirthDom.setText("secondary-action-copy", "Start a new match");
                } else {
                    RebirthStore.elements["next-turn-button"].innerHTML = '<i class="rb-action-loop"></i>End Turn';
                    RebirthStore.elements["next-turn-button"].disabled = !canNext;
                    RebirthDom.setText("secondary-action-copy", evolution ? "You can still evolve before ending" : "Pass to refill energy next turn");
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
                if (RebirthStore.state) {
                    RebirthRenderer.render();
                } else {
                    RebirthRenderer.buttons();
                }
            }
        },

        applyState(state) {
            RebirthStore.setState(state);
            RebirthRenderer.render();
        },

        async startMatch() {
            await this.request(async () => {
                RebirthStore.guidedFirstMatch = RebirthCoach.shouldGuideFirstMatch();
                RebirthStore.tutorialCompletionSent = false;
                const payload = await RebirthApi.post(RebirthConfig.endpoints.start, {
                    tutorial: RebirthStore.guidedFirstMatch
                });
                RebirthStore.selectedInstanceId = null;
                RebirthStore.selectedSummonSlot = null;
                RebirthStore.reward = null;
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
                RebirthStore.selectedSummonSlot = null;
                this.applyState(payload.state);
            });
        },

        async playSelectedCard(fieldSlot) {
            if (!RebirthStore.selectedInstanceId || !RebirthStore.state) return;
            if (RebirthStore.state.is_finished || RebirthStore.state.phase !== "choose") {
                RebirthErrors.show("Cards can only be played during your main phase.");
                RebirthRenderer.buttons();
                return;
            }
            const selectedCard = RebirthStore.handCard(RebirthStore.selectedInstanceId);
            if (!selectedCard) return;
            const energy = Number((RebirthStore.state.player && RebirthStore.state.player.energy) || 0);
            const cost = RebirthMarkup.cardCost(selectedCard);
            if (energy < cost) {
                RebirthErrors.show(`Not enough energy to summon ${selectedCard.name}.`);
                RebirthRenderer.buttons();
                return;
            }
            const isMonster = RebirthMarkup.isMonster(selectedCard);
            const requestedSlot = RebirthStore.fieldSlotIndex(fieldSlot);
            const selectedSlot = RebirthStore.fieldSlotIndex(RebirthStore.selectedSummonSlot);
            const slot = requestedSlot !== null
                ? requestedSlot
                : selectedSlot !== null
                    ? selectedSlot
                    : null;
            if (isMonster && !RebirthStore.fieldSlotOpen("player", slot)) {
                RebirthErrors.show("Choose an empty monster slot first.");
                RebirthRenderer.render();
                return;
            }
            await this.request(async () => {
                const summonedInstanceId = selectedCard.instance_id;
                const requestPayload = {
                    match_id: RebirthStore.state.match_id,
                    card_instance_id: selectedCard.instance_id,
                    card_id: selectedCard.id
                };
                if (isMonster) {
                    requestPayload.field_slot = slot;
                }
                const payload = await RebirthApi.post(RebirthConfig.endpoints.playCard, requestPayload);
                RebirthStore.selectedInstanceId = null;
                RebirthStore.selectedSummonSlot = null;
                RebirthStore.selectedAttackerId = isMonster ? summonedInstanceId : null;
                RebirthStore.reward = payload.match_reward || null;
                this.applyState(payload.state);
                this.completeTutorialIfNeeded(payload.state);
            });
        },

        async attackTarget(targetInstanceId) {
            if (!RebirthStore.selectedAttackerId || !RebirthStore.state || !RebirthStore.fieldCard(RebirthStore.selectedAttackerId)) {
                RebirthStore.selectedAttackerId = null;
                RebirthErrors.show("Select one ready monster on your battlefield first.");
                RebirthRenderer.render();
                return;
            }
            if (RebirthStore.state.is_finished || !["choose", "result"].includes(RebirthStore.state.phase)) {
                RebirthErrors.show("Attacks are not available in this phase.");
                RebirthRenderer.buttons();
                return;
            }
            const attacker = RebirthStore.fieldCard(RebirthStore.selectedAttackerId);
            if (attacker && (attacker.exhausted || attacker.has_attacked)) {
                RebirthErrors.show("That monster has already attacked this turn.");
                RebirthRenderer.buttons();
                return;
            }
            const botField = RebirthStore.fieldCards("bot");
            if (!targetInstanceId && botField.length) {
                RebirthErrors.show("Choose a defender before attacking.");
                RebirthRenderer.render();
                return;
            }
            if (targetInstanceId && !botField.some((card) => card.instance_id === targetInstanceId)) {
                RebirthErrors.show("That defender is no longer on the field.");
                RebirthRenderer.render();
                return;
            }
            await this.request(async () => {
                const payload = await RebirthApi.post(RebirthConfig.endpoints.attack, {
                    match_id: RebirthStore.state.match_id,
                    attacker_instance_id: RebirthStore.selectedAttackerId,
                    target_instance_id: targetInstanceId || null
                });
                RebirthStore.selectedAttackerId = null;
                RebirthStore.reward = payload.match_reward || null;
                this.applyState(payload.state);
                this.completeTutorialIfNeeded(payload.state);
            });
        },

        async clashSelectedAttacker() {
            const attacker = RebirthStore.fieldCard(RebirthStore.selectedAttackerId);
            if (!RebirthStore.selectedAttackerId || !RebirthStore.state || !attacker) {
                RebirthErrors.show("Select one ready monster on your battlefield first.");
                RebirthRenderer.buttons();
                return;
            }
            if (attacker.exhausted || attacker.has_attacked) {
                RebirthErrors.show("That monster has already attacked this turn.");
                RebirthRenderer.buttons();
                return;
            }
            const botField = RebirthStore.fieldCards("bot");
            const firstDefender = botField[0] || null;
            await this.attackTarget(firstDefender ? firstDefender.instance_id : null);
        },

        async nextTurn() {
            if (!RebirthStore.state) return;
            await this.request(async () => {
                const payload = await RebirthApi.post(RebirthConfig.endpoints.nextTurn, {
                    match_id: RebirthStore.state.match_id
                });
                RebirthStore.reward = null;
                RebirthStore.selectedAttackerId = null;
                RebirthStore.selectedSummonSlot = null;
                this.applyState(payload.state);
                this.completeTutorialIfNeeded(payload.state);
            });
        },

        completeTutorialIfNeeded(state) {
            if (!RebirthStore.guidedFirstMatch || RebirthStore.tutorialCompletionSent || !state || !state.is_finished) {
                return;
            }
            if (!RebirthConfig.endpoints.completeTutorial || !RebirthCoach.account().authenticated) {
                return;
            }
            RebirthStore.tutorialCompletionSent = true;
            RebirthApi.post(RebirthConfig.endpoints.completeTutorial, { step: 4 })
                .then((payload) => {
                    if (payload.tutorial && payload.tutorial.progression) {
                        RebirthConfig.player.progression = payload.tutorial.progression;
                    }
                })
                .catch(() => {
                    RebirthStore.tutorialCompletionSent = false;
                });
        }
    };

    async function initiateMobilePurchase(productId) {
        const capacitor = window.Capacitor || null;
        const nativePlatform = capacitor && typeof capacitor.getPlatform === "function"
            ? capacitor.getPlatform()
            : "web";
        const platform = nativePlatform === "ios" ? "ios" : "google_play";
        const receipt = [
            "simulated",
            nativePlatform,
            String(productId || "coins_100"),
            Date.now(),
            Math.random().toString(16).slice(2)
        ].join("-");
        const payload = {
            platform,
            product_id: productId || "coins_100",
            receipt
        };
        const endpoint = RebirthConfig.endpoints.verifyReceipt || "/api/rebirth/shop/verify-receipt";

        if (capacitor && capacitor.Plugins && capacitor.Plugins.Haptics && typeof capacitor.Plugins.Haptics.impact === "function") {
            capacitor.Plugins.Haptics.impact({ style: "medium" }).catch(() => {});
        }

        return RebirthApi.post(endpoint, payload);
    }

    const RebirthInput = {
        bind() {
            this.bindLogToggle();
            RebirthParallax.init();

            document.querySelectorAll("[data-new-match]").forEach((button) => {
                button.addEventListener("click", () => RebirthFlow.startMatch());
            });

            const playButton = RebirthStore.elements["play-button"];
            if (playButton) {
                playButton.addEventListener("click", () => {
                    if (RebirthStore.selectedAttackerId) {
                        RebirthFlow.clashSelectedAttacker();
                        return;
                    }
                    RebirthFlow.playSelectedCard();
                });
            }

            const nextButton = RebirthStore.elements["next-turn-button"];
            if (nextButton) {
                nextButton.addEventListener("click", () => {
                    if (!RebirthStore.state) return;
                    if (RebirthStore.state.phase === "choose" || RebirthStore.state.phase === "result") {
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
                    if (!button || button.disabled || RebirthStore.pending || !RebirthStore.state || RebirthStore.state.phase !== "choose") return;
                    RebirthStore.selectedInstanceId = button.getAttribute("data-card-instance");
                    RebirthStore.selectedAttackerId = null;
                    RebirthStore.selectedSummonSlot = null;
                    RebirthErrors.clear();
                    RebirthRenderer.render();
                });
            }

            const playerField = RebirthStore.elements["player-battlefield"];
            if (playerField) {
                playerField.addEventListener("click", (event) => {
                    const summonSlot = event.target.closest("[data-summon-slot]");
                    if (summonSlot && !summonSlot.disabled && RebirthStore.state && !RebirthStore.state.is_finished) {
                        const slot = Number(summonSlot.getAttribute("data-summon-slot"));
                        RebirthStore.selectedSummonSlot = slot;
                        RebirthErrors.clear();
                        RebirthRenderer.render();
                        RebirthFlow.playSelectedCard(slot);
                        return;
                    }
                    const button = event.target.closest("[data-attacker-instance]");
                    if (!button || !RebirthStore.state || RebirthStore.state.is_finished) return;
                    RebirthStore.selectedInstanceId = null;
                    RebirthStore.selectedSummonSlot = null;
                    RebirthStore.selectedAttackerId = button.getAttribute("data-attacker-instance");
                    RebirthErrors.clear();
                    RebirthRenderer.render();
                });
            }

            const botField = RebirthStore.elements["bot-battlefield"];
            if (botField) {
                botField.addEventListener("click", (event) => {
                    const direct = event.target.closest("[data-direct-attack]");
                    const target = event.target.closest("[data-target-instance]");
                    if (!direct && !target) return;
                    if (!RebirthStore.state || RebirthStore.state.is_finished) return;
                    RebirthFlow.attackTarget(target ? target.getAttribute("data-target-instance") : null);
                });
            }
        },

        bindLogToggle() {
            const panel = RebirthStore.elements["turn-log-panel"] || document.querySelector(".rb-turn-log");
            if (!panel) return;
            panel.id = panel.id || "turn-log-panel";
            panel.classList.remove("is-open");
            RebirthStore.elements["turn-log-panel"] = panel;

            const head = panel.querySelector(".rb-log-head");
            if (!head) return;

            let button = RebirthStore.elements["turn-log-toggle"] || panel.querySelector("[data-turn-log-toggle]");
            if (!button) {
                button = document.createElement("button");
                button.id = "turn-log-toggle";
                button.className = "rb-log-toggle";
                button.type = "button";
                button.dataset.turnLogToggle = "true";
                button.setAttribute("aria-controls", panel.id);
                button.setAttribute("aria-label", "Open turn history");
                button.innerHTML = '<i aria-hidden="true"></i><span>History</span>';
                head.appendChild(button);
                RebirthStore.elements["turn-log-toggle"] = button;
            }

            button.setAttribute("aria-expanded", "false");
            button.addEventListener("click", () => {
                const isOpen = !panel.classList.contains("is-open");
                panel.classList.toggle("is-open", isOpen);
                button.setAttribute("aria-expanded", isOpen ? "true" : "false");
                button.setAttribute("aria-label", isOpen ? "Close turn history" : "Open turn history");
            });
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

    window.initiateMobilePurchase = initiateMobilePurchase;
    window.renderTurnPhase = renderTurnPhase;
    window.triggerScreenShake = triggerScreenShake;

    document.addEventListener("DOMContentLoaded", init);
})();
