(function () {
    "use strict";

    const RebirthConfig = {
        endpoints: window.REBIRTH_ENDPOINTS || {},
        assets: window.REBIRTH_ASSETS || {},
        player: window.REBIRTH_PLAYER_CONTEXT || {},
        boardWidth: 852,
        boardHeight: 1846
    };
    const FIELD_SLOT_COUNT = 3;

    const RebirthStore = {
        state: null,
        selectedInstanceId: null,
        selectedAttackerId: null,
        reward: null,
        campaignReward: null,
        lastResultSignature: null,
        lastResultTextSignature: null,
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
            if (!this.selectedInstanceId && !this.selectedAttackerId && state && state.phase === "choose" && state.player && state.player.hand.length) {
                const preferred = this.defaultHandCard(state);
                this.selectedInstanceId = preferred ? preferred.instance_id : state.player.hand[0].instance_id;
            }
        },

        defaultHandCard(state) {
            const hand = (state && state.player && state.player.hand) || [];
            if (!hand.length) return null;
            const evolution = ((state && state.available_evolutions) || [])[0] || null;
            if (evolution) {
                const fusionSource = hand.find((card) => card.id === evolution.card_id);
                if (fusionSource) return fusionSource;
            }
            return hand.slice().sort((a, b) => {
                return this.cardScore(b) - this.cardScore(a) || String(a.name).localeCompare(String(b.name));
            })[0];
        },

        cardScore(card) {
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
            const slots = new Array(FIELD_SLOT_COUNT).fill(null);
            if (!this.state) return slots;
            const rootField = sideName === "player" ? this.state.player_field : this.state.bot_field;
            if (!Array.isArray(rootField)) return slots;
            rootField.slice(0, FIELD_SLOT_COUNT).forEach((card, index) => {
                slots[index] = card || null;
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
            const slots = this.fieldSlots(sideName);
            return Number.isInteger(index) && index >= 0 && index < slots.length && !slots[index];
        },

        firstOpenFieldSlot(sideName) {
            return this.fieldSlots(sideName).findIndex((card) => !card);
        },

        firstEvolution() {
            return ((this.state && this.state.available_evolutions) || [])[0] || null;
        },

        firstFieldFusion() {
            if (!this.state || !this.state.player || this.state.is_finished || this.state.phase !== "choose") return null;
            const slots = this.fieldSlots("player");
            for (let index = 0; index < FIELD_SLOT_COUNT - 1; index += 1) {
                const left = slots[index];
                const right = slots[index + 1];
                if (!left || !right) continue;
                const leftCatalog = left.catalog_id || left.id;
                const rightCatalog = right.catalog_id || right.id;
                const leftHp = Number(left.current_guard != null ? left.current_guard : left.guard || 0);
                const rightHp = Number(right.current_guard != null ? right.current_guard : right.guard || 0);
                if (!leftCatalog || leftCatalog !== rightCatalog || leftHp <= 0 || rightHp <= 0 || !left.evolution_id) continue;
                return {
                    side: "player",
                    sourceName: left.name,
                    resultingCatalogId: left.evolution_id,
                    resultingSlot: 1,
                    materialIds: [left.instance_id, right.instance_id],
                    materialCatalogIds: [leftCatalog, rightCatalog],
                    sourceCards: [left, right]
                };
            }
            return null;
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
                "phase-hud-label",
            "bot-card",
            "focus-card",
            "player-battlefield",
            "bot-battlefield",
                "evolution-panel",
                "evolution-status",
                "evolution-name",
                "evolution-card-thumbnail",
                "evolve-button",
                "rebirth-action-bar",
                "player-hand",
                "hand-count",
                "play-button",
                "primary-action-copy",
                "action-selected-card",
                "action-mana-label",
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
                "phase-timeline",
                "priority-label",
                "chain-label",
                "interrupt-label",
                "guide-rule-label",
                "guide-rule-title",
                "guide-rule-copy",
                "guide-combine-label",
                "guide-combine-title",
                "guide-combine-copy",
                "coach-panel",
                "coach-badge",
                "coach-title",
                "coach-copy",
                "rematch-button",
                "result-actions",
                "progression-tease"
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
                throw this.error("missing_endpoint", "O endpoint Rebirth não está configurado.");
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
                throw this.error("network_error", error.message || "Falha na requisição de rede.");
            }

            let payload = null;
            try {
                payload = await response.json();
            } catch (_error) {
                throw this.error("malformed_response", "O servidor retornou uma resposta ilegível.");
            }

            if (!response.ok || !payload || payload.ok !== true) {
                const serverError = payload && payload.error ? payload.error : {};
            throw this.error(serverError.code || "rebirth_error", serverError.message || "A requisição Rebirth falhou.");
            }

            return payload;
        },

        error(code, message) {
            const error = new Error(message);
            error.code = code;
            return error;
        }
    };

    function wait(ms) {
        return new Promise((resolve) => window.setTimeout(resolve, ms));
    }

    function nextFrame() {
        return new Promise((resolve) => {
            const frame = window.requestAnimationFrame || ((callback) => window.setTimeout(callback, 16));
            frame(() => resolve());
        });
    }

    function restartClass(node, className) {
        if (!node) return;
        node.classList.remove(className);
        nextFrame().then(() => {
            if (node.isConnected !== false) node.classList.add(className);
        });
    }

    function escapeSelectorValue(value) {
        const text = String(value == null ? "" : value);
        if (window.CSS && typeof window.CSS.escape === "function") {
            return window.CSS.escape(text);
        }
        return text.replace(/\\/g, "\\\\").replace(/"/g, "\\\"");
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    const RebirthBoardScaler = {
        init() {
            this.scale();
            window.addEventListener("resize", () => this.scale(), { passive: true });
            if (window.visualViewport) {
                window.visualViewport.addEventListener("resize", () => this.scale(), { passive: true });
                window.visualViewport.addEventListener("scroll", () => this.scale(), { passive: true });
            }
            window.addEventListener("wheel", (event) => {
                if (!this.isNativeMobile()) {
                    event.preventDefault();
                }
            }, { passive: false });
            window.addEventListener("touchmove", (event) => {
                if (this.isNativeMobile()) {
                    return;
                }
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
            const nativeMobile = width <= 760;
            document.body.classList.toggle("rb-mobile-native", nativeMobile);
            document.documentElement.style.setProperty("--rb-mobile-nav-height", `${navHeight}px`);
            if (nativeMobile) {
                document.documentElement.style.setProperty("--rb-board-width", "100%");
                document.documentElement.style.setProperty("--rb-board-height", "auto");
                document.documentElement.style.setProperty("--rb-safe-offset-x", "0px");
                document.documentElement.style.setProperty("--rb-safe-offset-y", "0px");
                document.documentElement.style.setProperty("--rb-nav-clearance", "0px");
                document.documentElement.style.setProperty("--rb-scale", "1");
                return;
            }
            const safeWidth = Math.max(1, width - safe.left - safe.right);
            const navClearance = navHeight + 8;
            const safeHeight = Math.max(1, height - safe.top - safe.bottom - navClearance);
            const desktop = width >= 1180 && height >= 680;
            const baseWidth = desktop ? 1180 : RebirthConfig.boardWidth;
            const baseHeight = desktop ? 760 : RebirthConfig.boardHeight;
            document.documentElement.style.setProperty("--rb-board-width", `${baseWidth}px`);
            document.documentElement.style.setProperty("--rb-board-height", `${baseHeight}px`);
            document.documentElement.style.setProperty("--rb-safe-offset-x", `${(safe.left - safe.right) / 2}px`);
            document.documentElement.style.setProperty("--rb-nav-clearance", `${navClearance}px`);
            const scale = Math.min(safeWidth / baseWidth, safeHeight / baseHeight);
            document.documentElement.style.setProperty("--rb-scale", String(scale));
            window.scrollTo(0, 0);
        },

        isNativeMobile() {
            return window.matchMedia("(max-width: 760px)").matches;
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
        label(name) {
            return {
                burn: "Queimadura",
                decay: "Deterioração",
                shield: "Escudo",
                weaken: "Fraqueza",
                freeze: "Congelamento"
            }[String(name || "").toLowerCase()] || name;
        },

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
                return '<span data-status="' + RebirthText.escape(name) + '">' + RebirthText.escape(this.label(name)) + turns + "</span>";
            }).join("") + "</div>";
        },

        miniBadge(statuses) {
            const name = this.names(statuses)[0];
            return name ? '<span class="rb-mini-status">' + RebirthText.escape(this.label(name)) + "</span>" : "";
        }
    };

    function renderTurnPhase(phase) {
        const phaseValue = String(phase || "MAIN_PHASE").toUpperCase();
        const phases = {
            DRAW_PHASE: { label: "Compra", tone: "draw", title: "Fase de Compra" },
            MAIN_PHASE: { label: "Principal", tone: "main", title: "Fase Principal" },
            COMBAT_PHASE: { label: "Combate", tone: "combat", title: "Fase de Combate" },
            END_PHASE: { label: "Fim", tone: "end", title: "Fase Final" },
            CHOOSE: { label: "Principal", tone: "main", title: "Fase Principal" },
            RESULT: { label: "Fim", tone: "end", title: "Fase Final" },
            FINISHED: { label: "Concluído", tone: "finished", title: "Partida encerrada" }
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
        RebirthDom.setText("phase-hud-label", meta.label);
        const track = RebirthStore.elements["phase-timeline"];
        if (track) {
            const order = ["draw", "main", "combat", "end"];
            const index = Math.max(0, order.indexOf(meta.tone === "finished" ? "end" : meta.tone));
            track.querySelectorAll("[data-phase-step]").forEach((step, stepIndex) => {
                step.classList.toggle("is-current", stepIndex === index);
                step.classList.toggle("is-complete", stepIndex < index);
            });
        }
        if (board) {
            board.dataset.turnPhase = meta.tone;
        }
        return meta;
    }

    let screenShakeTimer = null;

    function triggerScreenShake(profileOrIntensity) {
        const viewport = document.querySelector(".rb-game-viewport");
        const board = RebirthStore.elements["rebirth-board"];
        const target = viewport || board;
        const reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (!target || reducedMotion) return;

        let profile = "normal";
        let intensity = 3;
        if (typeof profileOrIntensity === "string") {
            profile = profileOrIntensity;
            intensity = profile === "heavy" ? 5 : profile === "subtle" ? 2 : 3;
        } else {
            const n = Math.min(5, Math.max(1, Number(profileOrIntensity || 3)));
            intensity = n;
            profile = n >= 5 ? "heavy" : n <= 2 ? "subtle" : "normal";
        }

        target.style.setProperty("--shake-intensity", `${intensity}px`);
        target.style.setProperty("--shake-intensity-negative", `${intensity * -1}px`);
        target.style.setProperty("--shake-intensity-soft", `${intensity * 0.55}px`);
        target.style.setProperty("--shake-intensity-soft-negative", `${intensity * -0.55}px`);

        target.classList.remove("is-screen-shaking", "vfx-screen-shake", "vfx-screen-shake-heavy");
        if (screenShakeTimer) window.clearTimeout(screenShakeTimer);
        const frame = window.requestAnimationFrame || ((callback) => window.setTimeout(callback, 16));
        frame(() => {
            target.classList.add("is-screen-shaking", "vfx-screen-shake");
            if (profile === "heavy") {
                target.classList.add("vfx-screen-shake-heavy");
            }
        });

        const duration = profile === "heavy" ? 180 : 160;
        screenShakeTimer = window.setTimeout(() => {
            target.classList.remove("is-screen-shaking", "vfx-screen-shake", "vfx-screen-shake-heavy");
            screenShakeTimer = null;
        }, duration);
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
            (state.player_field || []).slice(0, FIELD_SLOT_COUNT).filter(Boolean).forEach((card) => this.preloadCard(card));
            (state.bot_field || []).slice(0, FIELD_SLOT_COUNT).filter(Boolean).forEach((card) => this.preloadCard(card));
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
                return `/static/img/cards/baralho/${digits}.webp`;
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
                        ? "OCULTO"
                        : type === "SPELL"
                            ? "ARCANO"
                            : "SOMBRA";
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
            return `<img data-rebirth-art data-art-key="${RebirthText.escape(card && card.art_key ? card.art_key : "fallback")}" data-fallback-src="${RebirthText.escape(fallback)}" src="${RebirthText.escape(source)}" alt="" loading="lazy" decoding="async">`;
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
            return Number(card && card.tier || 1) > 1 ? "Ápice" : "Base";
        },

        cardRole(card) {
            const attack = Number(card && (card.attack || card.power) || 0);
            const guard = Number(card && card.guard || 0);
            const ability = String(card && card.ability_key || "");
            if (Number(card && card.tier || 1) > 1) return "Finalizador";
            if (ability.includes("guard") || ability === "brace" || ability === "bulwark" || guard >= attack + 2) return "Sentinela";
            if (attack >= 7 || ability.includes("bite") || ability.includes("rend")) return "Atacante";
            if (ability.includes("fade") || ability.includes("pursuit") || ability.includes("mark")) return "Tempo";
            return "Duelista";
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
                    <strong>${RebirthText.escape(card.ability_name || "Combate")}</strong>
                    <p>${RebirthText.escape(card.ability_text || card.flavor)}</p>
                    <div class="rb-card-tags">
                        <span>${RebirthText.escape(this.cardTierName(card))}</span>
                        <span>${RebirthText.escape(card.element || "Vazio")}</span>
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
            const ability = this.abilitySummary(card);
            return `
                <button class="${this.cardShellClasses(card, "rb-mini-card")}${selected}${recommended}${locked}${statusClass}" type="button" data-card-instance="${RebirthText.escape(card.instance_id)}" data-art-key="${RebirthText.escape(card.art_key || card.id)}" style="${RebirthAssets.cssVars(card)}" aria-pressed="${selected ? "true" : "false"}" aria-label="${lockedReason ? RebirthText.escape(lockedReason) + ". " : ""}Selecionar ${RebirthText.escape(card.name)}, ataque ${RebirthText.escape(card.attack)}, guarda ${RebirthText.escape(card.guard)}" ${disabled}>
                    <span class="rb-card-frame-layer" aria-hidden="true"></span>
                    <b class="rb-card-cost">${RebirthText.escape(this.cardCost(card))}</b>
                    ${options && options.recommended ? '<span class="rb-recommendation-badge">BEST PLAY</span>' : ""}
                    ${RebirthStatus.miniBadge(statuses)}
                    <span class="rb-card-image-layer rb-mini-art">
                        ${RebirthAssets.imageMarkup(card)}
                    </span>
                    <div class="rb-card-titlebar rb-mini-copy rb-card-hud-layer">
                        <strong class="rb-card-nameplate">${RebirthText.escape(card.name)}</strong>
                        <span>${RebirthText.escape(card.element)} - T${RebirthText.escape(card.tier)}</span>
                    </div>
                    <div class="rb-card-textbox rb-mini-textbox rb-card-hud-layer">
                        <strong>${RebirthText.escape(ability.name)}</strong>
                        <p>${RebirthText.escape(ability.copy)}</p>
                    </div>
                    <div class="rb-card-statline rb-mini-stats rb-card-hud-layer">
                        <span class="rb-card-stat is-atk"><b>${RebirthText.escape(card.attack || card.power)}</b><small>ATK</small></span>
                        <span class="rb-card-stat is-guard"><b>${RebirthText.escape(card.guard || 0)}</b><small>GUARD</small></span>
                    </div>
                </button>
            `;
        },

        cardCost(card) {
            if (!card) return 0;
            const type = String((card && (card.type || card.card_type)) || "MONSTER").toUpperCase();
            if (type === "MONSTER") {
                return Math.max(1, Math.min(10, Number(card.cost || card.tier || 1)));
            }
            return Math.max(0, Number(card && card.cost || 0));
        },

        abilitySummary(card) {
            return {
                name: card && (card.ability_name || this.cardRole(card) || "Combate"),
                copy: card && (card.ability_text || card.flavor || "Declare ataques, quebre a Guarda e pressione o HP.")
            };
        },

        cardType(card) {
            return String((card && (card.type || card.card_type)) || "MONSTER").toUpperCase();
        },

        isMonster(card) {
            return this.cardType(card) === "MONSTER";
        },

        elementClass(card) {
            // v55 Fase 3: prefere card.family (chave estável EN: "FIRE",
            // "WATER", "EARTH", "SHADOW") sobre card.element (que veio
            // traduzido pro pt-BR em commits recentes — "Fogo", "Agua").
            // Fallback pra element só se family ausente, mantendo compat
            // com payloads antigos.
            const raw = String((card && (card.family || card.element)) || "shadow").trim().toLowerCase();
            // Mapeia variações pt-BR caso ainda venham (defesa em
            // profundidade): "fogo"→"fire", "agua"/"água"→"water" etc.
            const ptToEn = {
                "fogo": "fire", "agua": "water", "água": "water",
                "terra": "earth", "sombra": "shadow",
            };
            const normalized = ptToEn[raw] || raw;
            const safeElement = normalized.replace(/[^a-z0-9-]/g, "-") || "shadow";
            return ` is-element-${safeElement}`;
        },

        rarityClass(card) {
            const rarity = String((card && card.rarity) || "COMMON").trim().toLowerCase();
            const safeRarity = rarity.replace(/[^a-z0-9-]/g, "-") || "common";
            const premium = safeRarity === "uncommon" ? " is-premium-rarity" : "";
            return ` is-rarity-${safeRarity}${premium}`;
        },

        cardShellClasses(card, baseClass) {
            const evolved = Number(card && card.tier || 1) > 1 ? " is-evolved" : "";
            return `${baseClass} rb-tcg-card${this.elementClass(card)}${this.rarityClass(card)}${evolved}`;
        },

        fieldCard(card, side, selected, statuses, options) {
            const guard = Number(card.current_guard != null ? card.current_guard : card.guard || 0);
            const maxGuard = Number(card.max_guard || card.guard || 1);
            const guardScale = Math.max(0, Math.min(1, guard / maxGuard));
            const exhausted = card.exhausted || card.has_attacked || card.has_acted ? " is-exhausted" : "";
            const selectedClass = selected ? " is-selected" : "";
            const attackingClass = side === "player" && selected ? " is-attacking" : "";
            const targetableClass = options && options.targetable ? " is-targetable" : "";
            const statusClass = RebirthStatus.className(statuses);
            const risk = options && options.risk ? options.risk : null;
            const riskClass = risk ? ` is-risk-${RebirthText.escape(risk.tone || "neutral")}` : "";
            const fusionClass = options && options.fusionSource ? " is-fusion-source" : "";
            const ability = this.abilitySummary(card);
            // F4: tooltip nativo com nome + habilidade pra quando o texto da
            // carta no slot for cortado pelo line-clamp.
            const fullTitle = `${card.name} — ${ability.name}${ability.copy ? ": " + ability.copy : ""}`;
            const riskAttrs = risk
                ? ` data-risk-tone="${RebirthText.escape(risk.tone || "neutral")}" data-risk-label="${RebirthText.escape(risk.label || "")}" title="${RebirthText.escape((risk.label || "") + (risk.copy ? " - " + risk.copy : ""))}"`
                : ` title="${RebirthText.escape(fullTitle)}"`;
            const targetAttr = side === "bot"
                ? `data-target-instance="${RebirthText.escape(card.instance_id)}"`
                : `data-attacker-instance="${RebirthText.escape(card.instance_id)}"`;
            return `
                <button class="${this.cardShellClasses(card, "rb-field-card rb-monster-card")}${selectedClass}${attackingClass}${targetableClass}${riskClass}${fusionClass}${exhausted}${statusClass}" type="button" ${targetAttr}${riskAttrs} data-art-key="${RebirthText.escape(card.art_key || card.id)}" style="${RebirthAssets.cssVars(card)}; --guard-scale: ${guardScale}" aria-label="${RebirthText.escape(card.name)} no campo ${side === "player" ? "do jogador" : "do bot"}">
                    <span class="rb-card-frame-layer" aria-hidden="true"></span>
                    ${RebirthStatus.miniBadge(statuses)}
                    ${risk ? `<span class="rb-risk-badge" data-risk-tone="${RebirthText.escape(risk.tone || "neutral")}">${RebirthText.escape(risk.label || "Risk")}</span>` : ""}
                    <b class="rb-card-cost">${RebirthText.escape(this.cardCost(card))}</b>
                    <span class="rb-card-image-layer rb-field-art">
                        ${RebirthAssets.imageMarkup(card)}
                    </span>
                    <span class="rb-card-titlebar rb-card-hud-layer">
                        <strong class="rb-card-nameplate">${RebirthText.escape(card.name)}</strong>
                        <small>${RebirthText.escape(card.element || card.family || "Vazio")} - T${RebirthText.escape(card.tier || 1)}</small>
                    </span>
                    <span class="rb-card-textbox rb-field-textbox rb-card-hud-layer">
                        <strong>${RebirthText.escape(ability.name)}</strong>
                        <p>${RebirthText.escape(ability.copy)}</p>
                    </span>
                    <span class="rb-card-statline">
                        <span class="rb-card-stat is-atk"><b>${RebirthText.escape(card.attack || card.power)}</b><small>ATK</small></span>
                        <span class="rb-card-stat is-guard"><b>${RebirthText.escape(guard)}</b><small>GUARD</small></span>
                    </span>
                    <i class="rb-guard-meter" aria-label="${RebirthText.escape(guard)}/${RebirthText.escape(maxGuard)} Guarda"></i>
                </button>
            `;
        },

        emptyFieldSlot(copy, options) {
            const direct = options && options.direct;
            const summonTarget = options && options.summonTarget ? " is-summon-target" : "";
            const selected = options && options.selected ? " is-selected" : "";
            const locked = options && options.locked ? " is-locked" : "";
            const disabled = locked && !direct ? "disabled aria-disabled=\"true\"" : "";
            const summonAttr = summonTarget ? 'data-summon-action="true"' : "";
            const reason = options && options.reason ? String(options.reason) : String(copy || "");
            return `<button class="rb-field-slot-empty${summonTarget}${selected}${locked}" type="button" ${direct ? "data-direct-attack=\"true\"" : ""} ${summonAttr} ${disabled} title="${RebirthText.escape(reason)}" aria-label="${RebirthText.escape(reason)}"><span>${RebirthText.escape(copy)}</span></button>`;
        },

        emptyFocus() {
            return `
                <div class="rb-card-topline">
                    <div>
                        <strong>Selecione um monstro</strong>
                        <span>Pronto</span>
                    </div>
                    <b class="rb-card-rank">?</b>
                </div>
                <div class="rb-card-art rb-asset-fallback">
                    <span>Escolha</span>
                </div>
                <div class="rb-card-rule">
                    <strong>Zona de Batalha</strong>
                    <p>Monstros invocados permanecem até a Guarda ser quebrada.</p>
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
                return { label: "Pressão", copy: "Tende a correr no ataque e forçar trocas rápidas de HP.", tone: "danger" };
            }
            if (id === "opportunist") {
                return { label: "Janela de armadilha", copy: "Tende a buscar valor de habilidade quando abrir brecha.", tone: "warning" };
            }
            return { label: "Linha defensiva", copy: "Tende a absorver primeiro e punir ataques fracos.", tone: "guard" };
        },

        selectedRead(card) {
            if (!card) {
                return { label: "Sem carta", copy: "Selecione um monstro para ver tempo, papel e risco." };
            }
            const attack = Number(card.attack || card.power || 0);
            const guard = Number(card.guard || 0);
            const tempo = attack * 2 + guard + Number(card.tier || 1) * 3;
            const role = RebirthMarkup.cardRole(card);
            const label = tempo >= 25 ? "Linha de poder" : tempo >= 18 ? "Linha estável" : "Linha de setup";
            return {
                label,
                copy: `${role}: ${attack} ataque / ${guard} guarda. Tempo ${tempo}.`
            };
        },

        clashRisk(attacker, defender) {
            if (window.RebirthHotfixUI && typeof window.RebirthHotfixUI.clashRisk === "function") {
                return window.RebirthHotfixUI.clashRisk(attacker, defender);
            }
            if (!attacker) return { tone: "neutral", label: "Sem atacante", copy: "Selecione um monstro pronto.", score: 0 };
            if (!defender) return { tone: "favorable", label: "Vantagem forte", copy: "Linha aberta para dano direto.", score: 4 };
            const attack = Number(attacker.attack || attacker.power || 0);
            const guard = Number(attacker.current_guard != null ? attacker.current_guard : attacker.guard || 0);
            const defense = Number(defender.current_guard != null ? defender.current_guard : defender.guard || 0);
            const counter = Number(defender.attack || defender.power || 0);
            if (attack >= defense + 2 && guard >= counter) {
                return { tone: "favorable", label: "Vantagem forte", copy: "Seu monstro deve vencer a troca.", score: 3 };
            }
            if (attack >= defense || guard >= counter - 1) {
                return { tone: "risky", label: "Troca provável", copy: "Troca possível, mas com perda de Guarda.", score: 1 };
            }
            return { tone: "losing", label: "Alto risco de perder", copy: "O defensor parece favorito.", score: -2 };
        },

        selectedAttackRisk(state) {
            if (!state || !RebirthStore.selectedAttackerId) return null;
            const attacker = RebirthStore.fieldCard(RebirthStore.selectedAttackerId);
            if (!attacker) return null;
            const defenders = RebirthStore.fieldCards("bot");
            if (!defenders.length) {
                return this.clashRisk(attacker, null);
            }
            return defenders
                .map((defender) => this.clashRisk(attacker, defender))
                .sort((a, b) => Number(a.score || 0) - Number(b.score || 0))[0] || null;
        },

        advantage(state) {
            if (!state) return { label: "Equilíbrio", copy: "Partida não carregada." };
            const hpDelta = Number(state.player.hp || 0) - Number(state.bot.hp || 0);
            const handDelta = Number((state.player.hand || []).length) - Number(state.bot.hand_count || 0);
            const deckDelta = Number(state.player.deck_count || 0) - Number(state.bot.deck_count || 0);
            const score = hpDelta + handDelta * 2 + deckDelta;
            if (score >= 6) return { label: "Vantagem", copy: `Você lidera por ${score} de tempo.` };
            if (score <= -6) return { label: "Sob pressão", copy: `O bot lidera por ${Math.abs(score)} de tempo.` };
            return { label: "Campo equilibrado", copy: "HP, mão e baralho estão próximos." };
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

        applyAccent(state) {
            const panel = RebirthStore.elements["result-panel"];
            const focus = RebirthStore.elements["focus-card"];
            const bot = RebirthStore.elements["bot-card"];
            const card = this.impactCard(state);
            const key = this.abilityKey(card);
            const accent = this.accent(card);

            [panel, focus, bot].forEach((element) => {
                if (!element) return;
                element.style.setProperty("--impact-accent", accent);
                element.setAttribute("data-ability-key", key);
            });
            if (panel) {
                panel.setAttribute("data-outcome", (state && state.result && state.result.outcome) || "Clash");
            }
            return { panel, focus, bot, card, key, accent };
        },

        pulse(state) {
            const targets = this.applyAccent(state);
            const panel = targets.panel;
            const focus = targets.focus;
            const bot = targets.bot;

            [panel, focus, bot].forEach((element) => {
                if (!element) return;
                element.classList.remove("is-impacting");
            });
            if (panel) panel.classList.add("is-impacting");
            if (focus) focus.classList.add("is-impacting");
            if (bot) bot.classList.add("is-impacting");

            window.setTimeout(() => {
                [panel, focus, bot].forEach((element) => {
                    if (element) element.classList.remove("is-impacting");
                });
            }, 620);

            this.haptics(state.result);
            this.audioEvents(state);
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

        audioEvents(state) {
            if (!window.RebirthAudioManager || !state) return;
            window.RebirthAudioManager.observeEvents(state.events || [], {
                hitPauseMs: RebirthCombatMotion.hitPauseMs || 0,
                replayAudioMutedMode: Boolean(state.replay_audio_muted_mode)
            });
        },

        screenShake(result) {
            if (!result || this.reducedMotion()) return false;
            const damage = result.damage || {};
            const playerDamage = Number(damage.player || 0);
            const botDamage = Number(damage.bot || 0);
            const totalDamage = Math.max(0, playerDamage) + Math.max(0, botDamage);
            const outcome = String(result.outcome || "").toLowerCase();
            if (outcome === "clash") {
                triggerScreenShake("heavy");
                return true;
            }
            if (totalDamage >= 5) {
                triggerScreenShake("heavy");
                return true;
            }
            if (totalDamage > 0) {
                triggerScreenShake("normal");
                return true;
            }
            if (outcome === "victory" || outcome === "defeat") {
                triggerScreenShake("normal");
                return true;
            }
            return false;
        }
    };

    const RebirthCombatMotion = {
        impactMs: 108,
        hitPauseMs: 52,
        shatterMs: 210,
        dissolveMs: 320,
        returnHoldMs: 64,
        settleMs: 76,

        attacker(attackerId) {
            const host = RebirthStore.elements["player-battlefield"];
            if (!host || !attackerId) return null;
            return host.querySelector(`[data-attacker-instance="${escapeSelectorValue(attackerId)}"]`);
        },

        target(targetId) {
            const host = RebirthStore.elements["bot-battlefield"];
            if (!host) return null;
            if (targetId) {
                return host.querySelector(`[data-target-instance="${escapeSelectorValue(targetId)}"]`);
            }
            return host.querySelector("[data-direct-attack]") || host.querySelector("[data-target-instance]");
        },

        boardScale() {
            const styles = window.getComputedStyle(document.documentElement);
            const scale = parseFloat(styles.getPropertyValue("--rb-scale"));
            return Number.isFinite(scale) && scale > 0 ? scale : 1;
        },

        vector(attacker, target) {
            if (!attacker || !target) {
                return { x: 0, y: -92 };
            }
            const scale = this.boardScale();
            const attackerRect = attacker.getBoundingClientRect();
            const targetRect = target.getBoundingClientRect();
            const attackerX = attackerRect.left + attackerRect.width / 2;
            const attackerY = attackerRect.top + attackerRect.height / 2;
            const targetX = targetRect.left + targetRect.width / 2;
            const targetY = targetRect.top + targetRect.height / 2;
            return {
                x: clamp(((targetX - attackerX) / scale) * 0.62, -320, 320),
                y: clamp(((targetY - attackerY) / scale) * 0.62, -190, 190)
            };
        },

        markImpact(target, state) {
            if (target) {
                restartClass(target, "is-taking-hit");
            }
            const result = state && state.result;
            RebirthFeel.haptics(result);
            RebirthFeel.audioEvents(state);
            if (!RebirthFeel.screenShake(result)) {
                triggerScreenShake("normal");
            }
        },

        // v55 Combat Juice — encontra criaturas que sobreviveram mas perderam
        // current_guard no choque (comparando RebirthStore.state PRÉ-resolve
        // com resolvedState PÓS-resolve) e dispara o estilhaço.
        triggerShieldShatter(resolvedState) {
            const previous = RebirthStore.state;
            if (!previous || !resolvedState || RebirthFeel.reducedMotion()) return;
            const destroyedIds = new Set(
                ((resolvedState.events || [])
                    .filter((e) => e && ["UNIT_DESTROYED", "MONSTER_DESTROYED"].includes(e.type))
                    .map((e) => (e.payload || {}).instance_id))
                    .filter(Boolean)
            );

            const sides = [
                { name: "player", host: RebirthStore.elements["player-battlefield"], attr: "data-attacker-instance" },
                { name: "bot", host: RebirthStore.elements["bot-battlefield"], attr: "data-target-instance" },
            ];
            sides.forEach(({ name, host, attr }) => {
                if (!host) return;
                const prevField = (name === "player" ? previous.player_field : previous.bot_field) || [];
                const nextField = (name === "player" ? resolvedState.player_field : resolvedState.bot_field) || [];
                const nextByInst = new Map(nextField.filter(Boolean).map((card) => [card.instance_id, card]));
                prevField.forEach((prevCard) => {
                    if (!prevCard || !prevCard.instance_id) return;
                    if (destroyedIds.has(prevCard.instance_id)) return;  // morreu, não estilhaça (vira dissolve)
                    const nextCard = nextByInst.get(prevCard.instance_id);
                    if (!nextCard) return;
                    const prevGuard = Number(prevCard.current_guard != null ? prevCard.current_guard : prevCard.guard || 0);
                    const newGuard = Number(nextCard.current_guard != null ? nextCard.current_guard : nextCard.guard || 0);
                    if (newGuard >= prevGuard) return;  // guarda não caiu
                    const node = host.querySelector(`[${attr}="${escapeSelectorValue(prevCard.instance_id)}"]`);
                    if (!node) return;
                    this.spawnShatter(node);
                });
            });
        },

        spawnShatter(node) {
            // Injeta um elemento dedicado de estilhaço — separa CSS do card
            // pra não conflitar com o hit-flash::before já aplicado em paralelo.
            const fx = document.createElement("span");
            fx.className = "vfx-shield-shatter";
            fx.setAttribute("aria-hidden", "true");
            // 6 shards distribuídos em ângulo via custom property
            for (let i = 0; i < 6; i += 1) {
                const shard = document.createElement("b");
                shard.className = "vfx-shield-shatter__shard";
                shard.style.setProperty("--shard-angle", `${i * 60}deg`);
                fx.appendChild(shard);
            }
            node.appendChild(fx);
            window.setTimeout(() => {
                if (fx.parentNode) fx.parentNode.removeChild(fx);
            }, this.shatterMs);
        },

        // v55 Combat Juice — varre eventos MONSTER_DESTROYED e marca os DOM
        // nodes com .is-dead-dissolve. Como play() é awaited antes do
        // applyState, a animação roda inteira antes do replace do HTML.
        triggerDeathDissolve(resolvedState) {
            if (!resolvedState || RebirthFeel.reducedMotion()) return [];
            const destroyedIds = (resolvedState.events || [])
                .filter((e) => e && ["UNIT_DESTROYED", "MONSTER_DESTROYED"].includes(e.type))
                .map((e) => (e.payload || {}).instance_id)
                .filter(Boolean);
            if (!destroyedIds.length) return [];

            const hosts = [
                { host: RebirthStore.elements["player-battlefield"], attr: "data-attacker-instance" },
                { host: RebirthStore.elements["bot-battlefield"], attr: "data-target-instance" },
            ];
            const marked = [];
            destroyedIds.forEach((instanceId) => {
                hosts.forEach(({ host, attr }) => {
                    if (!host) return;
                    const node = host.querySelector(`[${attr}="${escapeSelectorValue(instanceId)}"]`);
                    if (!node) return;
                    const removeDestroyedCard = (event) => {
                        if (event && event.target !== node) return;
                        node.remove();
                    };
                    node.classList.add("is-dead-dissolve");
                    node.addEventListener("animationend", removeDestroyedCard, { once: true });
                    window.setTimeout(removeDestroyedCard, this.dissolveMs + 40);
                    marked.push(node);
                });
            });
            return marked;
        },

        cleanup(attacker, target) {
            const board = RebirthStore.elements["rebirth-board"];
            if (board) {
                board.classList.remove("is-resolving-attack");
            }
            [attacker, target].forEach((element) => {
                if (!element) return;
                element.classList.remove("is-attack-primed", "is-attack-lunging", "is-taking-hit", "is-target-locked");
                element.style.removeProperty("--attack-x");
                element.style.removeProperty("--attack-y");
            });
        },

        async play(attackerId, targetId, resolvedState) {
            const attacker = this.attacker(attackerId);
            const target = this.target(targetId);
            if (!attacker || RebirthFeel.reducedMotion()) {
                this.markImpact(target, resolvedState);
                await wait(80);
                if (target) target.classList.remove("is-taking-hit");
                return;
            }

            const board = RebirthStore.elements["rebirth-board"];
            const vector = this.vector(attacker, target);
            attacker.style.setProperty("--attack-x", `${vector.x.toFixed(1)}px`);
            attacker.style.setProperty("--attack-y", `${vector.y.toFixed(1)}px`);
            attacker.classList.add("is-attack-primed");
            if (target) target.classList.add("is-target-locked");
            if (board) board.classList.add("is-resolving-attack");
            await nextFrame();

            attacker.classList.add("is-attack-lunging");
            await wait(this.impactMs);

            this.markImpact(target, resolvedState);
            if (window.RebirthHotfixFX && typeof window.RebirthHotfixFX.clashImpact === "function") {
                window.RebirthHotfixFX.clashImpact({ attacker, target, resolvedState });
            }

            if (window.RebirthHotfixFX && typeof window.RebirthHotfixFX.hitStop === "function") {
                await window.RebirthHotfixFX.hitStop(board || attacker, this.hitPauseMs);
            } else {
                await wait(this.hitPauseMs);
            }

            // v55 Combat Juice — SHIELD SHATTER + DEATH DISSOLVE
            // Disparados DEPOIS do markImpact pra coexistirem com o hit
            // flash e o screen shake. Shatter em sobreviventes que perderam
            // guard; dissolve em quem morreu. Ambos rodam em paralelo com
            // o resto da animação, e só esperam o tempo extra de dissolve
            // se houve morte (pra que applyState não substitua o HTML
            // antes da brasa terminar).
            this.triggerShieldShatter(resolvedState);
            const dyingNodes = this.triggerDeathDissolve(resolvedState);

            await wait(this.returnHoldMs);
            attacker.classList.remove("is-attack-lunging");
            await wait(this.settleMs);
            this.cleanup(attacker, target);

            if (dyingNodes.length) {
                // Já passamos impactMs + hitPauseMs + returnHoldMs + settleMs
                // (~620ms). O dissolve dura ~720ms, então precisamos do delta.
                const elapsed = this.returnHoldMs + this.settleMs;
                const remaining = Math.max(0, this.dissolveMs - elapsed);
                await wait(remaining);
            }
        }
    };

    /* v55 Fase 4 — Signature Identity: assinaturas visuais de evolução,
       dano direto no herói e telas de VITÓRIA/DERROTA. Cada módulo
       expõe play()/show()/animate() que retorna Promise — o flow
       awaita antes de chamar applyState pra a animação acontecer
       em cima do DOM antigo (que ainda casa visualmente com a ação). */

    const RebirthEvolutionMotion = {
        phase1Ms: 360,   // overlay aparece
        phase2Ms: 520,   // convergência
        phase3Ms: 380,   // runa visível antes do flash
        phase4Ms: 560,   // explosão + restauração

        snapshotSources(cardId) {
            // Acha as DOM nodes dos 2 cards na mão que vão fundir. O JS
            // gera data-card-instance no formato "player-NN-card_XXX".
            // Filtramos via suffix.
            const hand = RebirthStore.elements["player-hand"];
            if (!hand) return [];
            const candidates = Array.from(hand.querySelectorAll(
                `[data-card-instance$="-${cardId}"]`
            ));
            return candidates.slice(0, 2).map((node) => {
                const rect = node.getBoundingClientRect();
                return {
                    node,
                    rect,
                    html: node.outerHTML,
                };
            });
        },

        async play(sources, evolvedCard) {
            const stage = document.getElementById("rebirth-evolution-stage");
            if (!stage || RebirthFeel.reducedMotion() || !sources.length) {
                // sem stage ou reduced motion: pula a cinemática
                await wait(60);
                return;
            }
            const stageRect = stage.getBoundingClientRect();
            const cx = stageRect.left + stageRect.width / 2;
            const cy = stageRect.top + stageRect.height / 2;

            // Limpa qualquer execução anterior
            stage.innerHTML = "";
            stage.classList.remove("is-active", "is-rune-active", "is-burst-active");

            // Monta o stage: overlay + 2 clones convergentes + runa + burst
            const overlay = document.createElement("div");
            overlay.className = "vfx-evolution-overlay";
            stage.appendChild(overlay);

            const clones = sources.map((source, index) => {
                const wrapper = document.createElement("div");
                wrapper.className = "vfx-evolution-clone";
                // Posiciona o clone exatamente onde está o card original
                wrapper.style.left = `${source.rect.left - stageRect.left}px`;
                wrapper.style.top = `${source.rect.top - stageRect.top}px`;
                wrapper.style.width = `${source.rect.width}px`;
                wrapper.style.height = `${source.rect.height}px`;
                wrapper.innerHTML = source.html;
                // Vetor para o centro do stage
                const cardCx = source.rect.left + source.rect.width / 2;
                const cardCy = source.rect.top + source.rect.height / 2;
                wrapper.style.setProperty("--target-x", `${(cx - cardCx).toFixed(1)}px`);
                wrapper.style.setProperty("--target-y", `${(cy - cardCy).toFixed(1)}px`);
                wrapper.style.setProperty("--converge-rot", `${index === 0 ? -8 : 8}deg`);
                stage.appendChild(wrapper);
                return wrapper;
            });

            const rune = document.createElement("div");
            rune.className = "vfx-evolution-rune";
            stage.appendChild(rune);

            const burst = document.createElement("div");
            burst.className = "vfx-evolution-burst";
            stage.appendChild(burst);

            // FASE 1: ativa overlay
            stage.classList.add("is-active");
            stage.setAttribute("aria-hidden", "false");
            await wait(this.phase1Ms);

            // FASE 2: clones convergem para o centro
            clones.forEach((clone) => clone.classList.add("is-converging"));
            await wait(this.phase2Ms);

            // FASE 3: runa surge sobre os clones
            stage.classList.add("is-rune-active");
            await wait(this.phase3Ms);

            // FASE 4: clones somem num clarão + burst gigante
            clones.forEach((clone) => {
                clone.classList.remove("is-converging");
                clone.classList.add("is-vanishing");
            });
            stage.classList.add("is-burst-active");
            // shake do board pra entregar o impacto
            triggerScreenShake("heavy");
            await wait(this.phase4Ms);

            // Restaura iluminação: tira a classe de ativo, depois limpa DOM
            stage.classList.remove("is-active", "is-rune-active", "is-burst-active");
            stage.setAttribute("aria-hidden", "true");
            // Aguarda overlay fade-out (transition 360ms) antes de purgar
            await wait(360);
            stage.innerHTML = "";
        },
    };

    const RebirthFusionMotion = {
        convergeMs: 240,
        flashMs: 180,
        spawnMs: 460,
        handledKeys: new Set(),

        eventKey(event) {
            const payload = event && event.payload ? event.payload : {};
            return [
                event && (event.event_id || event.id || event.sequence_id || event.replay_frame) || "",
                payload.resulting_instance_id || "",
                event && event.effect_chain_id || ""
            ].join(":");
        },

        markHandled(event) {
            const key = this.eventKey(event);
            if (!key.trim()) return false;
            if (this.handledKeys.has(key)) return false;
            this.handledKeys.add(key);
            if (this.handledKeys.size > 30) {
                this.handledKeys = new Set(Array.from(this.handledKeys).slice(-18));
            }
            return true;
        },

        latestEvent(state) {
            return ((state && state.events) || [])
                .slice()
                .reverse()
                .find((event) => String(event.event_type || event.type || "") === "MONSTERS_FUSED") || null;
        },

        snapshotSources(instanceIds) {
            const wanted = new Set((instanceIds || []).filter(Boolean));
            if (!wanted.size) return [];
            const hosts = [
                { host: RebirthStore.elements["player-battlefield"], attr: "data-attacker-instance" },
                { host: RebirthStore.elements["bot-battlefield"], attr: "data-target-instance" },
            ];
            const sources = [];
            wanted.forEach((instanceId) => {
                hosts.forEach(({ host, attr }) => {
                    if (!host || sources.some((item) => item.instanceId === instanceId)) return;
                    const node = host.querySelector(`[${attr}="${escapeSelectorValue(instanceId)}"]`);
                    if (!node) return;
                    sources.push({
                        instanceId,
                        node,
                        rect: node.getBoundingClientRect(),
                        html: node.outerHTML
                    });
                });
            });
            return sources;
        },

        resultSlotRect(payload) {
            const host = RebirthStore.elements["player-battlefield"];
            const slot = Math.max(0, Math.min(2, Number(payload && payload.resulting_slot != null ? payload.resulting_slot : 1)));
            const node = host && host.children ? host.children[slot] : null;
            return node ? node.getBoundingClientRect() : null;
        },

        resultNode(event) {
            const payload = event && event.payload ? event.payload : {};
            const instanceId = payload.resulting_instance_id;
            if (!instanceId) return null;
            const hosts = [
                { host: RebirthStore.elements["player-battlefield"], attr: "data-attacker-instance" },
                { host: RebirthStore.elements["bot-battlefield"], attr: "data-target-instance" },
            ];
            for (const { host, attr } of hosts) {
                if (!host) continue;
                const node = host.querySelector(`[${attr}="${escapeSelectorValue(instanceId)}"]`);
                if (node) return node;
            }
            return null;
        },

        playAudio(event) {
            if (!window.RebirthAudioManager || !event) return;
            window.RebirthAudioManager.observeEvents([event], { hitPauseMs: 0, replayAudioMutedMode: false });
        },

        burstResult(event) {
            const node = this.resultNode(event);
            if (!node || RebirthFeel.reducedMotion()) return;
            restartClass(node, "is-fusion-born");
            window.setTimeout(() => {
                node.classList.remove("is-fusion-born");
            }, this.spawnMs + 80);
        },

        async play(sources, event, applyNextState) {
            if (!event || !this.markHandled(event)) {
                if (applyNextState) applyNextState();
                return;
            }
            this.playAudio(event);
            const stage = document.getElementById("rebirth-evolution-stage");
            const payload = event.payload || {};
            if (!stage || RebirthFeel.reducedMotion() || !sources.length) {
                if (applyNextState) applyNextState();
                this.burstResult(event);
                return;
            }

            const stageRect = stage.getBoundingClientRect();
            const targetRect = this.resultSlotRect(payload);
            const targetX = targetRect ? targetRect.left + targetRect.width / 2 : stageRect.left + stageRect.width / 2;
            const targetY = targetRect ? targetRect.top + targetRect.height / 2 : stageRect.top + stageRect.height / 2;

            stage.innerHTML = "";
            stage.classList.remove("is-active", "is-rune-active", "is-burst-active", "is-fusion-active", "is-fusion-flash");
            const overlay = document.createElement("div");
            overlay.className = "vfx-fusion-overlay";
            stage.appendChild(overlay);

            sources.forEach((source, index) => {
                if (source.node) source.node.classList.add("is-fusion-material-live");
                const wrapper = document.createElement("div");
                wrapper.className = "vfx-fusion-clone";
                wrapper.style.left = `${source.rect.left - stageRect.left}px`;
                wrapper.style.top = `${source.rect.top - stageRect.top}px`;
                wrapper.style.width = `${source.rect.width}px`;
                wrapper.style.height = `${source.rect.height}px`;
                wrapper.innerHTML = source.html;
                const sourceX = source.rect.left + source.rect.width / 2;
                const sourceY = source.rect.top + source.rect.height / 2;
                wrapper.style.setProperty("--target-x", `${(targetX - sourceX).toFixed(1)}px`);
                wrapper.style.setProperty("--target-y", `${(targetY - sourceY).toFixed(1)}px`);
                wrapper.style.setProperty("--fusion-rot", `${index === 0 ? -12 : 12}deg`);
                stage.appendChild(wrapper);
            });

            const flash = document.createElement("div");
            flash.className = "vfx-fusion-slot-flash";
            flash.style.left = `${(targetX - stageRect.left).toFixed(1)}px`;
            flash.style.top = `${(targetY - stageRect.top).toFixed(1)}px`;
            stage.appendChild(flash);

            const burst = document.createElement("div");
            burst.className = "vfx-fusion-burst";
            burst.style.left = `${(targetX - stageRect.left).toFixed(1)}px`;
            burst.style.top = `${(targetY - stageRect.top).toFixed(1)}px`;
            stage.appendChild(burst);

            stage.classList.add("is-active", "is-fusion-active");
            stage.setAttribute("aria-hidden", "false");
            await wait(40);
            stage.querySelectorAll(".vfx-fusion-clone").forEach((clone) => clone.classList.add("is-converging"));
            await wait(this.convergeMs);
            triggerScreenShake("heavy");
            stage.classList.add("is-fusion-flash");
            await wait(this.flashMs);

            if (applyNextState) applyNextState();
            this.burstResult(event);
            await wait(this.spawnMs);
            sources.forEach((source) => {
                if (source.node) source.node.classList.remove("is-fusion-material-live");
            });
            stage.classList.remove("is-active", "is-fusion-active", "is-fusion-flash");
            stage.setAttribute("aria-hidden", "true");
            await wait(120);
            stage.innerHTML = "";
        },

        observeStateEvents(previousState, nextState) {
            if (!nextState || previousState === nextState) return;
            const event = this.latestEvent(nextState);
            if (!event || this.handledKeys.has(this.eventKey(event))) return;
            this.markHandled(event);
            this.playAudio(event);
            this.burstResult(event);
        }
    };

    const RebirthHeroDamage = {
        durationMs: 460,

        // Compara HP de cada lado pré vs pós e dispara VFX no orbe
        // afetado. Chamado pelo attackTarget e por qualquer mutação de HP.
        evaluate(previousState, nextState) {
            if (!previousState || !nextState) return;
            if (RebirthFeel.reducedMotion()) return;
            const sides = [
                { name: "player", hudSelector: ".rb-hud-player" },
                { name: "bot", hudSelector: ".rb-hud-bot" },
            ];
            sides.forEach(({ name, hudSelector }) => {
                const prevHp = Number(((previousState[name] || {}).hp) || 0);
                const nextHp = Number(((nextState[name] || {}).hp) || 0);
                if (nextHp >= prevHp) return;  // não perdeu HP
                const hud = document.querySelector(hudSelector);
                if (!hud) return;
                restartClass(hud, "vfx-hero-damage");
                window.setTimeout(() => {
                    hud.classList.remove("vfx-hero-damage");
                }, this.durationMs + 40);
            });
        },
    };

    const RebirthFinaleOverlay = {
        // Detecta transição não-finished → finished e dispara overlay.
        // Idempotente: só dispara uma vez por match_id+winner pra não
        // re-spawnar a animação a cada render.
        lastFiredKey: null,

        evaluate(previousState, nextState) {
            if (!nextState || !nextState.is_finished) return;
            const wasFinished = Boolean(previousState && previousState.is_finished);
            const key = `${nextState.match_id || ""}:${nextState.winner || ""}`;
            if (wasFinished && this.lastFiredKey === key) return;
            this.lastFiredKey = key;
            this.show(nextState.winner, { firstDuel: Boolean(nextState.first_duel) });
        },

        reset() {
            this.lastFiredKey = null;
            const overlay = document.getElementById("rebirth-finale-overlay");
            if (overlay) {
                overlay.classList.remove("is-active", "is-victory", "is-defeat", "is-first-duel");
                overlay.innerHTML = "";
                overlay.setAttribute("aria-hidden", "true");
            }
            document.querySelectorAll(".vfx-orb-crack").forEach((el) => el.classList.remove("vfx-orb-crack"));
            const board = RebirthStore.elements["rebirth-board"];
            if (board) board.classList.remove("vfx-board-shatter");
        },

        show(winner, options) {
            const overlay = document.getElementById("rebirth-finale-overlay");
            if (!overlay) return;
            const isVictory = winner === "player";
            const isDefeat = winner === "bot";
            if (!isVictory && !isDefeat) return;  // clash mútuo não merece premium screen

            const firstDuel = Boolean(options && options.firstDuel);
            overlay.classList.remove("is-victory", "is-defeat", "is-first-duel");
            const variant = isVictory ? "is-victory" : "is-defeat";
            overlay.classList.add(variant);
            if (firstDuel && isVictory) {
                overlay.classList.add("is-first-duel");
            }
            const headline = firstDuel && isVictory
                ? "Primeira Vitória"
                : isVictory ? "Vitória" : "Derrota";
            const sublineCopy = firstDuel && isVictory
                ? '<div class="vfx-finale-subtitle">Você dominou seu primeiro duelo</div>'
                : "";
            overlay.innerHTML = `
                <div class="vfx-finale-curtain"></div>
                <div class="vfx-finale-text">${headline}</div>
                ${sublineCopy}
            `;
            nextFrame().then(() => {
                if (overlay.isConnected !== false) overlay.classList.add("is-active");
            });
            overlay.setAttribute("aria-hidden", "false");

            // efeitos colaterais por variante
            const board = RebirthStore.elements["rebirth-board"];
            if (isVictory && board) {
                board.classList.add("vfx-board-shatter");
                window.setTimeout(() => board.classList.remove("vfx-board-shatter"), 1500);
            }
            if (isDefeat) {
                const playerHud = document.querySelector(".rb-hud-player");
                if (playerHud) {
                    playerHud.classList.add("vfx-orb-crack");
                    window.setTimeout(() => playerHud.classList.remove("vfx-orb-crack"), 800);
                }
            }

            // A mensagem permanece legivel sem cobrir a proxima decisao.
            const fadeMs = firstDuel && isVictory ? 4300 : 2800;
            window.setTimeout(() => {
                overlay.classList.remove("is-active");
                overlay.setAttribute("aria-hidden", "true");
            }, fadeMs);
        },
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
            return RebirthStore.cardScore(card);
        },

        recommendedCard() {
            return RebirthStore.defaultHandCard(RebirthStore.state);
        },

        insight() {
            const state = RebirthStore.state;
            if (!state) {
                return { badge: "Guia", title: "Carregando arena.", copy: "Preparando sua primeira mão." };
            }
            if (!this.account().authenticated) {
                return {
                    badge: "Visitante",
                    title: "A mesa está liberada.",
                    copy: "Use Entrar / Cadastrar no topo quando quiser salvar coleção e recompensas."
                };
            }
            if (state.is_finished) {
                const won = state.winner === "player";
                return {
                    badge: won ? "Vitória" : "Próxima",
                    title: won ? "Reivindique a recompensa." : "Revise a recompensa e reconstrua.",
                    copy: "Abra Recompensas para acompanhar XP ou Coleção para ajustar o baralho antes da próxima partida."
                };
            }
            if (state.phase === "result") {
                const reward = RebirthStore.reward;
                if (reward && reward.daily && reward.daily.ready) {
                    return { badge: "Recompensa", title: "Recompensa diária pronta.", copy: "Depois desta partida, resgate o XP diário em Recompensas." };
                }
                return { badge: "Leia", title: "Leia o resultado antes de continuar.", copy: "O histórico explica dano, habilidades acionadas e por que o combate resolveu assim." };
            }
            const evolution = RebirthStore.firstEvolution();
            const selected = RebirthStore.selectedCard();
            const selectedAttacker = RebirthStore.selectedAttackerId ? RebirthStore.fieldCard(RebirthStore.selectedAttackerId) : null;
            const recommended = this.recommendedCard();
            const energy = Number((state.player && state.player.energy) || 0);
            const selectedFromHand = Boolean(selected && RebirthStore.selectedInstanceId && selected.instance_id === RebirthStore.selectedInstanceId);
            const selectedCost = selectedFromHand ? RebirthMarkup.cardCost(selected) : 0;
            if (selectedAttacker) {
                const risk = RebirthTactics.selectedAttackRisk(state);
                return {
                    badge: "Atacar",
                    title: `${selectedAttacker.name} está pronto.`,
                    copy: risk
                        ? `${risk.label}: ${risk.copy} Ataque quando essa troca valer o corpo em campo.`
                        : "Escolha um alvo no lado inimigo para resolver o duelo agora."
                };
            }
            if (selectedFromHand && selectedCost > energy) {
                return {
                    badge: "Mana",
                    title: `${selected.name} custa ${selectedCost}.`,
                    copy: `Você tem ${energy} de mana agora. Escolha uma carta mais barata ou encerre o turno para recarregar.`
                };
            }
            if (evolution && (!selected || selected.id === evolution.card_id)) {
                return {
                    badge: "Evoluir",
                    title: `${evolution.name} x${evolution.count} pode virar Rebirth.`,
                    copy: "Fusão não resolve ataque sozinha: ela cria uma carta maior na mão. Confira a mana antes de invocar."
                };
            }
            if (!selected) {
                return { badge: "Escolher", title: "Escolha uma carta ou atacante.", copy: "Mana paga cartas da mão; monstros prontos no campo atacam. O botão principal muda com a seleção." };
            }
            if (recommended && selected.instance_id === recommended.instance_id) {
                return {
                    badge: "Ótimo",
                    title: `${selected.name} é a leitura limpa.`,
                    copy: `Custa ${selectedCost} de mana e pressiona com ${selected.attack} de ataque / ${selected.guard} de guarda.`
                };
            }
            if (Number(selected.guard || 0) <= 2) {
                return {
                    badge: "Risco",
                    title: `${selected.name} pode ser punido.`,
                    copy: "Pouca guarda ataca rápido, mas cai se o bot responder com mais ataque. Use quando precisar acelerar."
                };
            }
            if (Number(selected.attack || 0) <= 3) {
                return {
                    badge: "Risco",
                    title: `${selected.name} pode travar em guarda alta.`,
                    copy: "Carta defensiva segura dano, mas precisa de habilidade, alvo ferido ou tempo para virar pressão."
                };
            }
            return {
                badge: "Plano",
                title: `${selected.name} é jogável.`,
                copy: recommended ? `${recommended.name} projeta mais valor, mas essa carta cabe na mana e ainda monta campo.` : "Jogue quando ataque, guarda e custo couberem no plano."
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
                const risk = RebirthTactics.selectedAttackRisk(state);
                board.dataset.riskTone = risk ? risk.tone : "none";
                board.classList.toggle("is-choosing-attack", Boolean(RebirthStore.selectedAttackerId) && !state.is_finished && !RebirthStore.pending);
            }
            renderTurnPhase(state.turn_phase || state.phase);
            RebirthAssets.preloadState(state);
            RebirthDom.setText("player-hp", state.player.hp);
            RebirthDom.setText("bot-hp", state.bot.hp);
            RebirthDom.setText("player-energy", state.player.energy);
            RebirthDom.setText("player-max-energy", state.player.max_energy);
            RebirthDom.setText("bot-energy", state.bot.energy);
            RebirthDom.setText("bot-max-energy", state.bot.max_energy);
            RebirthDom.setText("player-deck-count", `Baralho ${state.player.deck_count || 0}`);
            RebirthDom.setText("player-discard-count", `Descarte ${state.player.discard_count || 0}`);
            RebirthDom.setText("bot-deck-count", `Baralho ${state.bot.deck_count || 0}`);
            RebirthDom.setText("bot-discard-count", `Descarte ${state.bot.discard_count || 0}`);
            RebirthDom.setText("turn-number", String(state.turn).padStart(2, "0"));
            const bossName = state.campaign && state.campaign.presentation && state.campaign.presentation.name;
            RebirthDom.setText("bot-profile-label", bossName || (state.bot_profile && state.bot_profile.name) || "Perfil do bot");
            this.hpBars();
            this.battlefield();
            this.focusCard();
            this.botCard();
            this.evolutionPanel();
            this.hand();
            this.coach();
            this.result();
            this.resolution();
            this.tactics();
            this.guide();
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
            this.lifeOrb("player", Number(state.player.hp || 0), playerMax, playerScale);
            this.lifeOrb("bot", Number(state.bot.hp || 0), botMax, botScale);
        },

        lifeOrb(sideName, hp, maxHp, ratio) {
            const fill = RebirthStore.elements[`${sideName}-hp-fill`];
            const hud = document.querySelector(`.rb-hud-${sideName}`);
            const meter = fill ? fill.closest(".rb-hp-meter") : null;
            const low = ratio > 0 && ratio < 0.3;
            const stateName = low ? "danger" : ratio <= 0 ? "empty" : "stable";
            [hud, meter].forEach((element) => {
                if (!element) return;
                element.classList.toggle("is-low-hp", low);
                element.dataset.healthState = stateName;
                element.style.setProperty("--hp-ratio", ratio.toFixed(3));
                element.style.setProperty("--hp-percent", `${Math.round(ratio * 100)}%`);
            });
            if (meter) {
                meter.dataset.hpCurrent = String(Math.max(0, hp));
                meter.dataset.hpMax = String(Math.max(1, maxHp));
            }
            if (fill) {
                fill.style.transform = `scaleY(${ratio})`;
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
            const firstTurnDirectLocked = Number(state.turn || 1) === 1 && !botCards.length;
            const choosingAttack = Boolean(RebirthStore.selectedAttackerId)
                && state.phase === "choose"
                && !state.is_finished
                && !RebirthStore.pending;
            const selectedAttacker = choosingAttack ? RebirthStore.fieldCard(RebirthStore.selectedAttackerId) : null;
            const playerStatuses = (state.player && state.player.statuses) || {};
            const botStatuses = (state.bot && state.bot.statuses) || {};
            const selectedHandCard = RebirthStore.handCard(RebirthStore.selectedInstanceId);
            const selectedCost = RebirthMarkup.cardCost(selectedHandCard);
            const selectedEnergy = Number((state.player && state.player.energy) || 0);
            const fieldFusion = RebirthStore.firstFieldFusion();
            const fusionMaterialIds = new Set((fieldFusion && fieldFusion.materialIds) || []);
            const summonLockCopy = !selectedHandCard
                ? "Selecione uma carta"
                : selectedEnergy < selectedCost
                    ? "Mana insuficiente"
                    : state.phase !== "choose" || state.is_finished || RebirthStore.pending
                        ? "Bloqueado"
                        : "Duelo ocupado";
            const canSummonSelected = selectedHandCard
                && RebirthMarkup.isMonster(selectedHandCard)
                && state.phase === "choose"
                && !state.is_finished
                && !RebirthStore.pending
                && selectedEnergy >= selectedCost;
            playerHost.innerHTML = playerSlots.map((card) => {
                if (card) {
                    return RebirthMarkup.fieldCard(card, "player", card.instance_id === RebirthStore.selectedAttackerId, playerStatuses, {
                        fusionSource: fusionMaterialIds.has(card.instance_id)
                    });
                }
                return RebirthMarkup.emptyFieldSlot(canSummonSelected ? "Invocar" : summonLockCopy, {
                    summonTarget: Boolean(canSummonSelected),
                    locked: !canSummonSelected,
                    reason: canSummonSelected ? `Invocar ${selectedHandCard.name}` : summonLockCopy
                });
            }).join("");
            // audit #15: só o PRIMEIRO slot vazio carrega o rótulo de ação
            // ("Protegido no turno 1" / "Dano direto"); os demais ficam
            // neutros pra não repetir a mesma mensagem 2-3x e poluir a zona.
            let leadEmptyShown = false;
            botHost.innerHTML = botSlots.map((card) => {
                if (card) {
                    return RebirthMarkup.fieldCard(card, "bot", choosingAttack, botStatuses, {
                        targetable: choosingAttack,
                        risk: choosingAttack ? RebirthTactics.clashRisk(selectedAttacker, card) : null
                    });
                }
                const isLead = !leadEmptyShown;
                leadEmptyShown = true;
                if (!isLead) {
                    return RebirthMarkup.emptyFieldSlot("", { reason: "Slot vazio do bot" });
                }
                return RebirthMarkup.emptyFieldSlot(botCards.length ? "Linha de guarda" : firstTurnDirectLocked ? "Protegido no turno 1" : "Dano direto", {
                    direct: !botCards.length && !firstTurnDirectLocked,
                    selected: choosingAttack && !botCards.length && !firstTurnDirectLocked,
                    locked: firstTurnDirectLocked,
                    reason: firstTurnDirectLocked
                        ? "Dano direto bloqueado no primeiro turno"
                        : botCards.length
                            ? "Slot vazio do bot"
                            : "Ataque direto"
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
                host.innerHTML = "<span>Carta do bot</span>";
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
            const fieldFusion = RebirthStore.firstFieldFusion();
            const evolution = RebirthStore.firstEvolution();
            const canFuse = Boolean(fieldFusion && RebirthStore.state.phase === "choose" && !RebirthStore.state.is_finished);
            const canEvolve = Boolean(evolution && RebirthStore.state.phase === "choose" && !RebirthStore.state.is_finished);
            const canUse = canFuse || canEvolve;
            panel.classList.toggle("is-empty", !canUse);
            button.disabled = !canUse || RebirthStore.pending;
            button.dataset.cardId = canEvolve ? evolution.card_id : "";
            button.dataset.mode = canFuse ? "fusion" : "evolution";
            button.hidden = canFuse;
            button.textContent = canFuse ? "Fundir" : "Evoluir";

            if (!canUse) {
                RebirthDom.setText("evolution-status", RebirthStore.state.phase === "choose" ? "Sem duplicata" : "Bloqueado");
                RebirthDom.setText("evolution-name", "Sem duplicata");
                if (thumb) {
                    thumb.style.backgroundImage = "";
                    thumb.classList.add("rb-asset-fallback");
                }
                return;
            }

            if (canFuse) {
                RebirthDom.setText("evolution-status", "Fusao pronta");
                RebirthDom.setText("evolution-name", `${fieldFusion.sourceName} x2`);
            } else {
                RebirthDom.setText("evolution-status", "Duplicata encontrada");
                RebirthDom.setText("evolution-name", `${evolution.name} x${evolution.count}`);
            }
            const sourceCard = canFuse
                ? fieldFusion.sourceCards[0]
                : (RebirthStore.state.player.hand || []).find((card) => card.id === evolution.card_id);
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
            RebirthDom.setText("hand-count", `${hand.length} ${hand.length === 1 ? "carta" : "cartas"}`);
            const canChoose = state.phase === "choose" && !state.is_finished && !RebirthStore.pending;
            const energy = Number((state.player && state.player.energy) || 0);
            const hasOpenSlot = RebirthStore.firstOpenFieldSlot("player") >= 0;
            host.innerHTML = hand.map((card) => RebirthMarkup.miniCard(card, {
                selected: card.instance_id === RebirthStore.selectedInstanceId,
                recommended: recommended && card.instance_id === recommended.instance_id,
                statuses: card.instance_id === RebirthStore.selectedInstanceId ? RebirthStore.state.player.statuses : null,
                locked: !canChoose || energy < RebirthMarkup.cardCost(card) || (RebirthMarkup.isMonster(card) && !hasOpenSlot),
                lockedReason: !canChoose
                    ? "Ação indisponível fora da sua fase principal"
                    : energy < RebirthMarkup.cardCost(card)
                        ? `Sem mana suficiente: precisa de ${RebirthMarkup.cardCost(card)}`
                        : RebirthMarkup.isMonster(card) && !hasOpenSlot
                            ? "Sem slot livre"
                            : ""
            })).join("");
        },

        coach() {
            const panel = RebirthStore.elements["coach-panel"];
            if (!panel) return;
            const insight = RebirthCoach.insight();
            panel.dataset.coachTone = String(insight.badge || "Guia").toLowerCase();
            RebirthDom.setText("coach-badge", insight.badge || "Guia");
            RebirthDom.setText("coach-title", insight.title || "Monte seu campo.");
            RebirthDom.setText("coach-copy", insight.copy || "Vou apontar a linha mais segura antes de você confirmar.");
        },

        feedbackHighlight() {
            const feedback = ((RebirthStore.state && RebirthStore.state.resolution_context && RebirthStore.state.resolution_context.feedback) || []);
            const readable = {
                DAMAGE_RESOLVED: { label: "Dano resolvido", title: "Impacto confirmado." },
                SHIELD_APPLIED: { label: "Escudo", title: "Dano prevenido." },
                SHIELD_GRANTED: { label: "Escudo", title: "Proteção aplicada." },
                SHIELD_BROKEN: { label: "Armadura quebrada", title: "Proteção rompida." },
                TRAP_TRIGGERED: { label: "Armadilha", title: "Resposta acionada." },
                UNIT_DESTROYED: { label: "Unidade destruída", title: "Combate resolvido." },
                UNIT_EXHAUSTED: { label: "Exausto", title: "Ação consumida." }
            };
            const highlighted = feedback.slice().reverse().find((event) => readable[event.event_type]);
            if (!highlighted) return null;
            return Object.assign({}, readable[highlighted.event_type], highlighted);
        },

        result() {
            const state = RebirthStore.state;
            const result = state.result;
            const panel = RebirthStore.elements["result-panel"];
            if (panel) {
                panel.classList.remove("is-victory", "is-defeat", "is-clash", "is-first-duel");
            }
            this.abilityEvents(result);
            this.rewardPanel();
            this.rematchCta(state);
            if (state.is_finished) {
                const won = state.winner === "player";
                const tied = state.winner === "clash";
                const firstDuel = Boolean(state.first_duel);
                const concise = window.RebirthHotfixUI && typeof window.RebirthHotfixUI.resultLine === "function"
                    ? window.RebirthHotfixUI.resultLine(state)
                    : "";
                if (panel) {
                    panel.classList.add(tied ? "is-clash" : won ? "is-victory" : "is-defeat");
                    if (firstDuel && won) panel.classList.add("is-first-duel");
                }
                const headlineLabel = firstDuel && won ? "Primeira vitória" : tied ? "Clash" : won ? "Vitória" : "Derrota";
                const headlineTitle = firstDuel && won
                    ? "Você dominou seu primeiro duelo."
                    : tied ? "Os dois lados caíram." : won ? "Você venceu o duelo." : "O bot venceu o duelo.";
                RebirthDom.setText("result-label", headlineLabel);
                RebirthDom.setText("result-title", headlineTitle);
                RebirthDom.setText("result-copy", concise || (result && result.message ? result.message : "Inicie uma nova partida quando quiser."));
                this.resultReadability(`finished:${state.turn}:${state.winner}:${result && result.message}`);
                this.resultImpact();
                return;
            }
            if (result) {
                const damage = result.damage || {};
                const guardTrade = result.outcome === "Clash"
                    && (Number(damage.player || 0) > 0 || Number(damage.bot || 0) > 0);
                if (panel) {
                    panel.classList.add(`is-${String(result.outcome || "clash").toLowerCase()}`);
                }
                const outcomeLabels = { Victory: "Confronto vencido", Defeat: "Unidade perdida", Clash: "Troca", Summon: "Invocação", Spell: "Magia", "Trap Armed": "Armadilha armada" };
                const outcomeTitles = {
                    Victory: "Pressão aplicada.",
                    Defeat: "Seu ataque foi contido.",
                    Clash: guardTrade ? "Troca de Guarda." : "Nenhum dano.",
                    Summon: "Unidade em campo.",
                    Spell: "Efeito resolvido.",
                    "Trap Armed": "Resposta preparada."
                };
                const outcome = outcomeLabels[result.outcome] || result.outcome;
                const concise = window.RebirthHotfixUI && typeof window.RebirthHotfixUI.resultLine === "function"
                    ? window.RebirthHotfixUI.resultLine(state)
                    : "";
                RebirthDom.setText("result-label", outcome);
                RebirthDom.setText("result-title", outcomeTitles[result.outcome] || outcome);
                RebirthDom.setText("result-copy", concise || result.message);
                this.resultReadability(`${state.turn}:${result.outcome}:${result.message}`);
                this.resultImpact();
                return;
            }
            const highlight = this.feedbackHighlight();
            if (highlight) {
                if (panel) {
                    panel.classList.add("is-clash");
                }
                RebirthDom.setText("result-label", highlight.label);
                RebirthDom.setText("result-title", highlight.title);
                RebirthDom.setText("result-copy", highlight.message || "A resolução foi concluída.");
                this.resultReadability(`feedback:${state.turn}:${highlight.event_type}:${highlight.message || ""}`);
                this.resultImpact();
                return;
            }
            RebirthStore.lastResultSignature = null;
            RebirthStore.lastResultTextSignature = null;
            RebirthDom.setText("result-label", "Aguardando");
            RebirthDom.setText("result-title", "Monte seu campo.");
            RebirthDom.setText("result-copy", "Invoque monstros, selecione um aliado pronto e escolha o alvo.");
        },

        tactics() {
            const host = RebirthStore.elements["tactics-strip"];
            const state = RebirthStore.state;
            if (!host || !state) return;
            const selected = RebirthStore.selectedCard();
            const intent = RebirthTactics.botIntent(state.bot_profile || {});
            const read = RebirthTactics.selectedRead(selected);
            const advantage = RebirthTactics.advantage(state);
            const risk = RebirthTactics.selectedAttackRisk(state);
            const botHand = state.bot.hand_count == null ? "?" : state.bot.hand_count;
            host.dataset.intentTone = intent.tone;
            host.dataset.riskTone = risk ? risk.tone : "none";
            const rows = [];
            if (risk) {
                rows.push(`<span class="rb-risk-chip" data-risk-tone="${RebirthText.escape(risk.tone)}"><b>${RebirthText.escape(risk.label)}</b>${RebirthText.escape(risk.copy)}</span>`);
            }
            rows.push(
                `<span><b>${RebirthText.escape(intent.label)}</b>${RebirthText.escape(intent.copy)}</span>`,
                `<span><b>${RebirthText.escape(read.label)}</b>${RebirthText.escape(read.copy)}</span>`,
                `<span><b>${RebirthText.escape(advantage.label)}</b>${RebirthText.escape(advantage.copy)}</span>`,
                `<span><b>Mão inimiga</b>${RebirthText.escape(botHand)} cartas ocultas</span>`
            );
            host.innerHTML = rows.join("");
        },

        guide() {
            const state = RebirthStore.state;
            const result = state && state.result;
            const evolution = RebirthStore.firstEvolution();
            if (!state) return;

            if (state.is_finished) {
                const title = state.winner === "player" ? "Duelo vencido" : state.winner === "bot" ? "Bot venceu" : "Clash final";
                RebirthDom.setText("guide-rule-label", "Partida");
                RebirthDom.setText("guide-rule-title", title);
                RebirthDom.setText("guide-rule-copy", result && result.message ? result.message : "Inicie uma nova partida quando quiser.");
                RebirthDom.setText("guide-combine-label", "Próxima");
                RebirthDom.setText("guide-combine-title", "Nova partida");
                RebirthDom.setText("guide-combine-copy", "Este duelo terminou. Comece outra para testar uma linha nova.");
                return;
            }

            if (result) {
                const events = result.ability_events || [];
                const damage = result.damage || {};
                const guardTrade = result.outcome === "Clash"
                    && (Number(damage.player || 0) > 0 || Number(damage.bot || 0) > 0);
                const outcomeLabels = { Victory: "Confronto vencido", Defeat: "Unidade perdida", Clash: guardTrade ? "Troca de Guarda" : "Sem dano", Summon: "Invocação", Spell: "Magia" };
                const outcomeTitle = outcomeLabels[result.outcome] || result.outcome;
                RebirthDom.setText("guide-rule-label", "Resultado");
                RebirthDom.setText("guide-rule-title", outcomeTitle);
                RebirthDom.setText("guide-rule-copy", result.message || "Avance para o próximo turno.");
                RebirthDom.setText("guide-combine-label", events.length ? "Habilidade" : "Próxima");
                RebirthDom.setText("guide-combine-title", events.length ? "Acionada" : "Próximo turno");
                RebirthDom.setText("guide-combine-copy", events.length ? events[0] : "Avance para recompor as mãos e continuar o duelo.");
                return;
            }

            const selected = RebirthStore.selectedCard();
            const selectedAttacker = RebirthStore.selectedAttackerId ? RebirthStore.fieldCard(RebirthStore.selectedAttackerId) : null;
            const energy = Number((state.player && state.player.energy) || 0);
            const selectedCost = selected && RebirthStore.selectedInstanceId ? RebirthMarkup.cardCost(selected) : 0;
            if (selectedAttacker) {
                const risk = RebirthTactics.selectedAttackRisk(state);
                RebirthDom.setText("guide-rule-label", "Ataque");
                RebirthDom.setText("guide-rule-title", risk ? risk.label : "Escolha o alvo");
                RebirthDom.setText("guide-rule-copy", risk ? `${risk.copy} Resolva só quando a troca favorecer seu plano.` : "Toque no inimigo ou no botão Atacar para resolver.");
                RebirthDom.setText("guide-combine-label", "Risco");
                RebirthDom.setText("guide-combine-title", "Corpo em campo vale tempo");
                RebirthDom.setText("guide-combine-copy", "Perder um monstro abre espaço, mas também entrega pressão ao bot.");
                return;
            }
            if (selected && RebirthStore.selectedInstanceId && selectedCost > energy) {
                RebirthDom.setText("guide-rule-label", "Mana");
                RebirthDom.setText("guide-rule-title", `${energy}/${Number((state.player && state.player.max_energy) || energy)} disponível`);
                RebirthDom.setText("guide-rule-copy", `${selected.name} custa ${selectedCost}. Encerre o turno para recarregar ou jogue uma carta mais barata.`);
                RebirthDom.setText("guide-combine-label", "Tempo");
                RebirthDom.setText("guide-combine-title", "Curva antes de força");
                RebirthDom.setText("guide-combine-copy", "Carta forte parada na mão não bloqueia dano. Monte campo com o que cabe agora.");
                return;
            }

            RebirthDom.setText("guide-rule-label", "Regra");
            RebirthDom.setText("guide-rule-title", "Mana, campo e ataque");
            RebirthDom.setText("guide-rule-copy", "Mana paga cartas da mão. Depois, selecione um monstro pronto no campo para atacar.");
            RebirthDom.setText("guide-combine-label", evolution ? "Combinar pronto" : "Combinar");
            RebirthDom.setText("guide-combine-title", evolution ? `${evolution.name} x${evolution.count}` : "Duplicatas evoluem");
            RebirthDom.setText("guide-combine-copy", evolution ? "Evoluir cria uma carta maior na mão; confira o custo antes de invocar." : "Dois monstros iguais se fundem em sua forma Rebirth antes da jogada.");
        },

        resultImpact() {
            const signature = RebirthFeel.resultSignature(RebirthStore.state);
            if (!signature || signature === RebirthStore.lastResultSignature) return;
            RebirthStore.lastResultSignature = signature;
            RebirthFeel.pulse(RebirthStore.state);
        },

        resultReadability(signature) {
            const panel = RebirthStore.elements["result-panel"];
            if (!panel || !signature || signature === RebirthStore.lastResultTextSignature) return;
            RebirthStore.lastResultTextSignature = signature;
            restartClass(panel, "is-result-reading");
        },

        abilityEvents(result) {
            const host = RebirthStore.elements["ability-events"];
            if (!host) return;
            const events = (result && result.ability_events) || [];
            const feedback = ((RebirthStore.state && RebirthStore.state.resolution_context && RebirthStore.state.resolution_context.feedback) || []);
            if (!result) {
                const labels = {
                    DAMAGE_RESOLVED: "Dano resolvido",
                    SHIELD_APPLIED: "Escudo",
                    SHIELD_GRANTED: "Escudo",
                    SHIELD_BROKEN: "Armadura quebrada",
                    TRAP_TRIGGERED: "Trap acionada",
                    UNIT_DESTROYED: "Unidade destruída",
                    UNIT_EXHAUSTED: "Unidade exausta",
                    STATUS_APPLIED: "Status aplicado"
                };
                host.innerHTML = feedback.slice(-3).map((event) => {
                    const label = event.message || labels[event.event_type] || event.event_type;
                    return '<span class="rb-ability-chip">' + RebirthText.escape(label) + "</span>";
                }).join("");
                return;
            }
            if (!events.length) {
                host.innerHTML = '<span class="rb-ability-chip is-muted">Combate básico</span>';
                return;
            }
            const narrated = String(result.message || "").toLowerCase();
            const novelEvents = events.filter((event) => !narrated.includes(String(event).toLowerCase()));
            if (!novelEvents.length) {
                host.innerHTML = "";
                return;
            }
            const visible = novelEvents.slice(0, 2).map((event) => {
                return '<span class="rb-ability-chip">' + RebirthText.escape(event) + "</span>";
            });
            if (novelEvents.length > 2) {
                visible.push('<span class="rb-ability-chip is-muted">+' + RebirthText.escape(novelEvents.length - 2) + " eventos</span>");
            }
            host.innerHTML = visible.join("");
        },

        resolution() {
            const context = RebirthStore.state && RebirthStore.state.resolution_context;
            if (!context) return;
            RebirthDom.setText("priority-label", `Prioridade: ${context.priority_label || "Resolvida"}`);
            const chainEventCount = Number(context.chain_event_count || 0) || 0;
            // audit #9: o id técnico ("EVENT-000001") vazava pra UI. O jogador
            // só precisa saber que há uma cadeia ativa e quantos efeitos ela
            // empilha — não o identificador interno.
            RebirthDom.setText(
                "chain-label",
                context.chain_id
                    ? (chainEventCount === 1 ? "Cadeia ativa · 1 efeito" : `Cadeia ativa · ${chainEventCount} efeitos`)
                    : "Sem cadeia ativa"
            );
            const chainLabel = RebirthStore.elements["chain-label"];
            if (chainLabel) {
                const chainActive = context.chain_state !== "resolvida" || context.current_phase === "COMBAT_PHASE";
                let intensity = "idle";
                if (chainActive && context.chain_id && chainEventCount >= 8) {
                    intensity = "heavy";
                } else if (chainActive && context.chain_id && chainEventCount >= 4) {
                    intensity = "rising";
                }
                chainLabel.dataset.intensity = intensity;
            }
            RebirthDom.setText("interrupt-label", context.interrupt_label || "Janela fechada");
            const interrupt = RebirthStore.elements["interrupt-label"];
            if (interrupt) {
                interrupt.dataset.interrupt = String(context.interrupt_label || "").toLowerCase().includes("trap") ? "resolved" : "closed";
            }
        },

        rewardPanel() {
            const host = RebirthStore.elements["reward-panel"];
            if (!host) return;
            const reward = RebirthStore.reward;
            const campaignReward = RebirthStore.campaignReward;
            if (!reward && !(campaignReward && campaignReward.applied)) {
                host.innerHTML = "";
                host.hidden = true;
                return;
            }
            host.hidden = false;
            if (!reward) {
                host.innerHTML = [
                    '<span class="rb-reward-xp">+' + RebirthText.escape(campaignReward.xp) + " XP</span>",
                    "<span>Encontro da campanha vencido</span>"
                ].join("");
                return;
            }
            if (!reward.persisted) {
                host.innerHTML = '<span class="rb-reward-muted">' + RebirthText.escape(reward.message) + "</span>";
                return;
            }
            const achievements = (reward.achievements || []).map((item) => item.name).join(", ");
            const dailyLabel = reward.daily && reward.daily.state === "claimed"
                ? "Diária resgatada"
                : reward.daily && reward.daily.ready
                    ? "Diária pronta"
                    : "";
            const nextLabel = reward.xp_to_next != null
                ? RebirthText.escape(reward.xp_to_next) + " XP até o próximo nível"
                : "";
            host.innerHTML = [
                '<span class="rb-reward-xp">+' + RebirthText.escape(reward.xp) + " XP</span>",
                "<span>Nível " + RebirthText.escape(reward.level) + (reward.level_up ? " alcançado" : "") + "</span>",
                nextLabel ? "<span>" + nextLabel + "</span>" : "",
                achievements ? "<span>" + RebirthText.escape(achievements) + "</span>" : "",
                dailyLabel ? '<span class="rb-reward-daily">' + RebirthText.escape(dailyLabel) + "</span>" : "",
                campaignReward && campaignReward.applied ? '<span class="rb-reward-daily">Campanha: +' + RebirthText.escape(campaignReward.xp) + " XP</span>" : "",
                reward.next_goal ? "<span>" + RebirthText.escape(reward.next_goal) + "</span>" : ""
            ].join("");
        },

        rematchCta(state) {
            const rematch = RebirthStore.elements["rematch-button"];
            const tease = RebirthStore.elements["progression-tease"];
            const actions = RebirthStore.elements["result-actions"];
            const isFinished = Boolean(state && state.is_finished);
            const won = state && state.winner === "player";
            const firstDuel = Boolean(state && state.first_duel);

            if (rematch) {
                rematch.hidden = !isFinished;
                rematch.disabled = RebirthStore.pending;
                const label = firstDuel && won
                    ? "Jogar de novo"
                    : isFinished
                        ? (won ? "Jogar de novo" : "Revanche")
                        : "Jogar de novo";
                rematch.innerHTML = `<i class="rb-action-loop" aria-hidden="true"></i>${RebirthText.escape(label)}`;
                rematch.classList.toggle("is-first-duel", firstDuel && won);
            }

            if (actions) {
                actions.classList.toggle("is-finished", isFinished);
            }

            if (!tease) return;
            if (!isFinished) {
                tease.hidden = true;
                tease.innerHTML = "";
                return;
            }

            // Tease pós-partida — destaca o ganho de XP, ofertas de evolução e
            // o próximo objetivo. Em primeiro duelo + vitória promovemos um
            // hook explícito de "próximo desbloqueio".
            const reward = RebirthStore.reward || {};
            const xp = reward.xp != null ? `+${RebirthText.escape(reward.xp)} XP garantidos` : "Recompensa pronta para resgate";
            const nextGoal = reward.next_goal
                ? RebirthText.escape(reward.next_goal)
                : firstDuel && won
                    ? "Próxima partida desbloqueia a curva real do bot"
                    : "Continue duelando pra subir de nível";
            const teaser = firstDuel && won
                ? `<strong class="rb-tease-headline">Estreia vencida</strong><span>${xp}</span><span>${nextGoal}</span>`
                : `<span>${xp}</span><span>${nextGoal}</span>`;
            tease.hidden = false;
            tease.innerHTML = teaser;
        },

        log() {
            const host = RebirthStore.elements["turn-log"];
            if (!host) return;
            host.innerHTML = (RebirthStore.state.log || [])
                .slice(-5)
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
            const fieldFusion = RebirthStore.firstFieldFusion();
            const selected = RebirthStore.selectedInstanceId
                ? (state.player.hand || []).find((card) => card.instance_id === RebirthStore.selectedInstanceId)
                : null;
            const selectedAttacker = RebirthStore.selectedAttackerId
                ? RebirthStore.fieldCard(RebirthStore.selectedAttackerId)
                : null;
            const energy = Number((state.player && state.player.energy) || 0);
            const cost = selected ? RebirthMarkup.cardCost(selected) : 0;
            const canPay = !selected || energy >= cost;
            const attackerReady = selectedAttacker && !selectedAttacker.exhausted && !selectedAttacker.has_attacked && !selectedAttacker.has_acted;
            const directLocked = Number(state.turn || 1) === 1 && RebirthStore.fieldCards("bot").length === 0;
            const attackRisk = selectedAttacker ? RebirthTactics.selectedAttackRisk(state) : null;
            const emptySlot = RebirthStore.firstOpenFieldSlot("player");
            const isMonster = selected && RebirthMarkup.isMonster(selected);
            const noOpenSlot = Boolean(isMonster && emptySlot < 0);
            let actionState = "choose";
            let actionCopyOverride = null;
            if (RebirthStore.elements["play-button"]) {
                const btn = RebirthStore.elements["play-button"];
                if (state.is_finished) {
                    actionState = "finished";
                    btn.innerHTML = '<i class="rb-action-sword"></i>Encerrado';
                    btn.disabled = true;
                    btn.title = "A partida foi encerrada.";
                } else if (state.phase === "result") {
                    actionState = "resolved";
                    btn.innerHTML = '<i class="rb-action-sword"></i>Resolvido';
                    btn.disabled = true;
                    btn.title = "Combate resolvido. Avance para o próximo turno.";
                } else if (fieldFusion) {
                    actionState = "fusion";
                    btn.innerHTML = '<i class="rb-action-loop"></i>Fundir';
                    btn.disabled = !canChoose;
                    btn.title = `Fundir ${fieldFusion.sourceName} x2 em uma forma evoluida.`;
                    actionCopyOverride = `Funda ${fieldFusion.sourceName} x2.`;
                } else if (selectedAttacker) {
                    actionState = attackRisk && attackRisk.tone ? `attack-${attackRisk.tone}` : "attack";
                    btn.innerHTML = '<i class="rb-action-sword"></i>Atacar';
                    btn.disabled = !canChoose || !attackerReady || directLocked;
                    btn.title = directLocked
                        ? "Dano direto bloqueado no primeiro turno. Encerre o turno para o bot responder."
                        : attackRisk && attackRisk.tone === "losing"
                            ? "Ataque arriscado: alta chance de perder a unidade."
                            : attackRisk && attackRisk.tone === "risky"
                                ? "Ataque equilibrado: troca provável."
                        : attackerReady
                        ? "Ataca o monstro inimigo ou diretamente se o campo adversário estiver vazio."
                        : "Esse monstro já atacou neste turno.";
                } else {
                    actionState = selected
                        ? !canPay
                            ? "no-mana"
                            : noOpenSlot
                                ? "no-slot"
                                : "play-card"
                        : "choose-card";
                    btn.innerHTML = `<i class="rb-action-sword"></i>${isMonster ? "Invocar" : "Jogar"}${selected ? ` ${cost}` : ""}`;
                    btn.disabled = !canChoose || !RebirthStore.selectedInstanceId || !canPay || noOpenSlot;
                    if (!RebirthStore.selectedInstanceId) {
                        btn.title = "Escolha uma carta da mão primeiro.";
                    } else if (noOpenSlot) {
                        btn.title = "Sem slot livre no seu campo.";
                    } else if (!canPay) {
                        btn.title = `Sem mana suficiente — precisa de ${cost}.`;
                    } else {
                        btn.title = isMonster ? "Invoca a carta selecionada." : "Joga a carta selecionada.";
                    }
                }
            }
            const actionCopy = window.RebirthHotfixUI && typeof window.RebirthHotfixUI.actionCopy === "function"
                ? (actionCopyOverride || window.RebirthHotfixUI.actionCopy({
                    state,
                    selected,
                    selectedAttacker,
                    risk: attackRisk,
                    cost,
                    energy,
                    canPay,
                    noOpenSlot,
                    pending: RebirthStore.pending,
                    directLocked,
                    attackerReady
                }))
                : (actionCopyOverride || (selectedAttacker
                    ? "Ataque a unidade inimiga."
                    : selected
                        ? `Jogue ${selected.name}.`
                        : "Escolha uma carta primeiro."));
            RebirthDom.setText("primary-action-copy", actionCopy);
            RebirthDom.setText("action-selected-card", selectedAttacker ? selectedAttacker.name : selected ? selected.name : "Escolha uma carta");
            RebirthDom.setText("action-mana-label", `Mana ${energy}/${Number((state.player && state.player.max_energy) || energy)}`);
            const actionBar = RebirthStore.elements["rebirth-action-bar"];
            if (actionBar) {
                actionBar.dataset.actionState = actionState;
                actionBar.dataset.riskTone = attackRisk ? attackRisk.tone : "none";
            }
            // Highlight turn advance when no card or ready attacker can act.
            const fieldCards = RebirthStore.fieldCards("player");
            const playerEnergy = Number((state.player && state.player.energy) || 0);
            const handHasPlayable = (state.player && state.player.hand || []).some((card) => {
                const cardCost = RebirthMarkup.cardCost(card);
                if (cardCost > playerEnergy) return false;
                if (RebirthMarkup.isMonster(card)) {
                    return RebirthStore.firstOpenFieldSlot("player") >= 0;
                }
                return true;  // spells/traps don't need slots
            });
            const readyAttacker = fieldCards.find((card) => card && !card.exhausted && !card.has_attacked && !card.has_acted);
            const evolutionAvailable = Boolean(evolution || fieldFusion);
            const deadEnd = canChoose
                && !handHasPlayable
                && !readyAttacker
                && !evolutionAvailable
                && !selected
                && !selectedAttacker;
            const nextButton = RebirthStore.elements["next-turn-button"];
            if (nextButton) {
                nextButton.classList.toggle("is-cta-pulse", deadEnd);
            }
            if (state.phase === "choose" && deadEnd && !state.is_finished) {
                // Don't spam — only set if there isn't a more-specific error already showing.
                const errEl = document.getElementById("rebirth-error");
                if (errEl && !errEl.textContent.trim()) {
                    RebirthErrors.show("Sem ações disponíveis neste turno. Encerre para o bot jogar.");
                }
            }
            if (nextButton) {
                if (state.phase === "result") {
                    nextButton.innerHTML = '<i class="rb-action-loop"></i>Próximo turno';
                    nextButton.disabled = !canNext;
                    nextButton.title = "Avance para preparar o próximo turno.";
                    RebirthDom.setText("secondary-action-copy", "Prepare seu campo");
                } else if (state.is_finished) {
                    nextButton.innerHTML = '<i class="rb-action-loop"></i>Encerrado';
                    nextButton.disabled = true;
                    nextButton.title = "A partida foi encerrada.";
                    RebirthDom.setText("secondary-action-copy", "Inicie uma nova partida");
                } else {
                    nextButton.innerHTML = '<i class="rb-action-loop"></i>Encerrar turno';
                    nextButton.disabled = !canNext;
                    nextButton.title = deadEnd
                        ? "Sem ações disponíveis — encerre o turno."
                        : "Encerre o turno para o bot agir e recarregar sua mana.";
                    RebirthDom.setText("secondary-action-copy", fieldFusion ? "Você ainda pode fundir antes de encerrar" : evolution ? "Você ainda pode evoluir antes de encerrar" : "Passe a vez para recarregar mana");
                }
            }
            if (RebirthStore.elements["evolve-button"]) {
                RebirthStore.elements["evolve-button"].disabled = !canChoose || !(evolution || fieldFusion);
            }
        }
    };

    const RebirthErrors = {
        show(message) {
            const error = RebirthStore.elements["rebirth-error"];
            if (!error) return;
            error.textContent = message || "Ação recusada.";
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
                RebirthErrors.show(error.message || "A ação falhou.");
                RebirthDom.setText("result-label", "Erro");
                RebirthDom.setText("result-title", "Ação recusada.");
                RebirthDom.setText("result-copy", error.message || "A ação falhou.");
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
            // v55 Fase 4 — captura estado anterior ANTES do setState pra
            // os módulos de assinatura compararem HP/finished. Roda em
            // microtask depois pra não bloquear o render.
            const previousState = RebirthStore.state;
            RebirthStore.setState(state);
            RebirthRenderer.render();
            try {
                RebirthFusionMotion.observeStateEvents(previousState, state);
                RebirthHeroDamage.evaluate(previousState, state);
                RebirthFinaleOverlay.evaluate(previousState, state);
                if (window.RebirthBossFX) window.RebirthBossFX.observe(previousState, state);
            } catch (err) {
                /* nunca deixa VFX falhar derrubar a UI */
                if (window.console) console.warn("[rebirth] signature VFX failed", err);
            }
        },

        async startMatch() {
            // v55 Fase 4 — limpa overlay de finale residual antes de
            // iniciar nova partida. Evita "Vitória" antigo aparecer por
            // um frame quando o usuário pede Nova Partida após vencer.
            RebirthFinaleOverlay.reset();
            if (window.RebirthBossFX) window.RebirthBossFX.reset();
            await this.request(async () => {
                const campaignNode = String(new URLSearchParams(window.location.search).get("campaign") || "").trim();
                const inCampaign = Boolean(campaignNode);
                RebirthStore.guidedFirstMatch = !inCampaign && RebirthCoach.shouldGuideFirstMatch();
                RebirthStore.tutorialCompletionSent = false;
                const endpoint = inCampaign ? RebirthConfig.endpoints.campaignStart : RebirthConfig.endpoints.start;
                const requestPayload = inCampaign
                    ? { node_id: campaignNode }
                    : { tutorial: RebirthStore.guidedFirstMatch };
                const payload = await RebirthApi.post(endpoint, requestPayload);
                RebirthStore.abandonmentSentForMatch = null;
                RebirthStore.selectedInstanceId = null;
                RebirthStore.reward = null;
                RebirthStore.campaignReward = null;
                this.applyState(payload.state);
            });
        },

        async evolveFirstDuplicate() {
            const fieldFusion = RebirthStore.firstFieldFusion();
            if (fieldFusion) {
                await this.fuseFieldPair(fieldFusion);
                return;
            }
            const evolution = RebirthStore.firstEvolution();
            if (!evolution || !RebirthStore.state) return;
            await this.request(async () => {
                // v55 Fase 4: snapshot dos DOM nodes ANTES do payload chegar.
                // O applyState vai destruir a mão atual; precisamos das
                // referências enquanto ainda existem.
                const sourceCards = RebirthEvolutionMotion.snapshotSources(evolution.card_id);
                const payload = await RebirthApi.post(RebirthConfig.endpoints.evolve, {
                    match_id: RebirthStore.state.match_id,
                    card_id: evolution.card_id
                });
                RebirthStore.campaignReward = payload.campaign_reward || null;
                RebirthStore.selectedInstanceId = payload.evolved ? payload.evolved.instance_id : null;
                // Roda a sequência cinematográfica (overlay → convergência
                // → runa → flash) antes do applyState, assim a UI antiga
                // sustenta o pano de fundo da animação.
                await RebirthEvolutionMotion.play(sourceCards, payload.evolved);
                this.applyState(payload.state);
            });
        },

        async fuseFieldPair(fusion) {
            if (!fusion || !RebirthStore.state) return;
            await this.request(async () => {
                const sourceCards = RebirthFusionMotion.snapshotSources(fusion.materialIds);
                const payload = await RebirthApi.post(RebirthConfig.endpoints.labsFusion || "/api/labs/fusion", {
                    match_id: RebirthStore.state.match_id,
                    player_id: "player",
                    source_instance_a: fusion.materialIds[0],
                    source_instance_b: fusion.materialIds[1]
                });
                const event = RebirthFusionMotion.latestEvent(payload.state);
                const resultingId = payload.fusion
                    && payload.fusion.resulting_card
                    && payload.fusion.resulting_card.instance_id;
                RebirthStore.selectedInstanceId = null;
                RebirthStore.selectedAttackerId = resultingId || null;
                await RebirthFusionMotion.play(sourceCards, event, () => {
                    this.applyState(payload.state);
                });
            });
        },

        async activateEvolutionOrFusion() {
            const fusion = RebirthStore.firstFieldFusion();
            if (fusion) {
                await this.fuseFieldPair(fusion);
                return;
            }
            await this.evolveFirstDuplicate();
        },

        async playSelectedCard() {
            if (!RebirthStore.selectedInstanceId || !RebirthStore.state) return;
            if (RebirthStore.state.is_finished || RebirthStore.state.phase !== "choose") {
                RebirthErrors.show("Cartas só podem ser jogadas na sua fase principal.");
                RebirthRenderer.buttons();
                return;
            }
            const selectedCard = RebirthStore.handCard(RebirthStore.selectedInstanceId);
            if (!selectedCard) return;
            const energy = Number((RebirthStore.state.player && RebirthStore.state.player.energy) || 0);
            const cost = RebirthMarkup.cardCost(selectedCard);
            if (energy < cost) {
                RebirthErrors.show(`Mana insuficiente para invocar ${selectedCard.name}.`);
                RebirthRenderer.buttons();
                return;
            }
            const isMonster = RebirthMarkup.isMonster(selectedCard);
            // v54: 3-slot duel. Let the backend pick the first empty slot.
            // The pre-check below only guards against ALL slots being full;
            // previously it pinned slot=0 and incorrectly blocked summons
            // even when slots 1 or 2 were free.
            if (isMonster && RebirthStore.firstOpenFieldSlot("player") < 0) {
                RebirthErrors.show("Todos os seus slots de monstro estão ocupados. Ataque ou encerre o turno.");
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
                const payload = await RebirthApi.post(RebirthConfig.endpoints.playCard, requestPayload);
                RebirthStore.selectedInstanceId = null;
                RebirthStore.selectedAttackerId = isMonster ? summonedInstanceId : null;
                RebirthStore.reward = payload.match_reward || null;
                RebirthStore.campaignReward = payload.campaign_reward || null;
                this.applyState(payload.state);
                this.completeTutorialIfNeeded(payload.state);
            });
        },

        async attackTarget(targetInstanceId) {
            if (!RebirthStore.selectedAttackerId || !RebirthStore.state || !RebirthStore.fieldCard(RebirthStore.selectedAttackerId)) {
                RebirthStore.selectedAttackerId = null;
                RebirthErrors.show("Selecione um monstro pronto no seu campo primeiro.");
                RebirthRenderer.render();
                return;
            }
            if (RebirthStore.state.is_finished || !["choose", "result"].includes(RebirthStore.state.phase)) {
                RebirthErrors.show("Ataques não disponíveis nesta fase.");
                RebirthRenderer.buttons();
                return;
            }
            const attacker = RebirthStore.fieldCard(RebirthStore.selectedAttackerId);
            if (attacker && (attacker.exhausted || attacker.has_attacked || attacker.has_acted)) {
                RebirthErrors.show("Esse monstro já atacou neste turno.");
                RebirthRenderer.buttons();
                return;
            }
            const botField = RebirthStore.fieldCards("bot");
            if (!targetInstanceId && !botField.length && Number(RebirthStore.state.turn || 1) === 1) {
                RebirthErrors.show("Dano direto bloqueado no primeiro turno. Encerre o turno para o bot responder.");
                RebirthRenderer.render();
                return;
            }
            const visualTargetId = targetInstanceId || (botField[0] && botField[0].instance_id) || null;
            if (targetInstanceId && !botField.some((card) => card.instance_id === targetInstanceId)) {
                RebirthErrors.show("Esse defensor não está mais em campo.");
                RebirthRenderer.render();
                return;
            }
            await this.request(async () => {
                const attackerInstanceId = RebirthStore.selectedAttackerId;
                const payload = await RebirthApi.post(RebirthConfig.endpoints.attack, {
                    match_id: RebirthStore.state.match_id,
                    attacker_instance_id: attackerInstanceId,
                    target_instance_id: targetInstanceId || null
                });
                await RebirthCombatMotion.play(attackerInstanceId, visualTargetId, payload.state);
                RebirthStore.selectedAttackerId = null;
                RebirthStore.reward = payload.match_reward || null;
                RebirthStore.campaignReward = payload.campaign_reward || null;
                const signature = RebirthFeel.resultSignature(payload.state);
                if (signature) {
                    RebirthStore.lastResultSignature = signature;
                    RebirthFeel.applyAccent(payload.state);
                }
                this.applyState(payload.state);
                this.completeTutorialIfNeeded(payload.state);
            });
        },

        async clashSelectedAttacker() {
            const attacker = RebirthStore.fieldCard(RebirthStore.selectedAttackerId);
            if (!RebirthStore.selectedAttackerId || !RebirthStore.state || !attacker) {
                RebirthErrors.show("Selecione um monstro pronto no seu campo primeiro.");
                RebirthRenderer.buttons();
                return;
            }
            if (attacker.exhausted || attacker.has_attacked || attacker.has_acted) {
                RebirthErrors.show("Esse monstro já atacou neste turno.");
                RebirthRenderer.buttons();
                return;
            }
            await this.attackTarget(null);
        },

        async nextTurn() {
            if (!RebirthStore.state) return;
            await this.request(async () => {
                const payload = await RebirthApi.post(RebirthConfig.endpoints.nextTurn, {
                    match_id: RebirthStore.state.match_id
                });
                RebirthStore.reward = null;
                RebirthStore.campaignReward = payload.campaign_reward || null;
                RebirthStore.selectedAttackerId = null;
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

    RebirthFlow.refreshAfterAuth = async function (detail) {
        const account = detail && detail.account ? detail.account : detail && detail.payload ? detail.payload.account : null;
        if (account) {
            RebirthConfig.player.account = account;
        }
        RebirthStore.selectedInstanceId = null;
        RebirthStore.selectedAttackerId = null;
        RebirthStore.reward = null;
        RebirthStore.campaignReward = null;
        RebirthStore.lastResultSignature = null;
        RebirthStore.lastResultTextSignature = null;
        RebirthStore.guidedFirstMatch = false;
        RebirthStore.tutorialCompletionSent = false;
        RebirthStore.setPending(false);
        await this.startMatch();
        return { handled: true };
    };

    async function initiateMobilePurchase(productId) {
        const error = new Error("Compras de Gemas permanecem desativadas ate a integracao oficial das lojas.");
        error.code = "monetization_disabled";
        throw error;
    }

    let parallaxRaf = null;

    const RebirthArenaLifecycle = {
        livingBoard: null,
        layers: [],
        parallaxMove: null,
        parallaxLeave: null,
        medallionBindings: [],

        reducedMotion() {
            return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        },

        activate(playButton, nextButton) {
            this.teardown();
            if (this.reducedMotion()) return;

            this.livingBoard = document.querySelector("[data-battlefield-living]");
            if (this.livingBoard) {
                this.layers = Array.from(this.livingBoard.querySelectorAll(".battlefield-layer[data-parallax-depth]"));
                this.parallaxMove = (event) => {
                    if (parallaxRaf !== null) return;
                    const clientX = event.clientX;
                    const clientY = event.clientY;
                    parallaxRaf = window.requestAnimationFrame(() => {
                        parallaxRaf = null;
                        if (!this.livingBoard) return;
                        const rect = this.livingBoard.getBoundingClientRect();
                        const nx = ((clientX - rect.left) / rect.width - 0.5) * 2;
                        const ny = ((clientY - rect.top) / rect.height - 0.5) * 2;
                        this.layers.forEach((layer) => {
                            const depth = Number(layer.getAttribute("data-parallax-depth") || 0);
                            layer.style.transform = `translate3d(${(nx * depth).toFixed(2)}px, ${(ny * depth).toFixed(2)}px, 0)`;
                        });
                    });
                };
                this.parallaxLeave = () => {
                    this.layers.forEach((layer) => {
                        layer.style.transform = "translate3d(0, 0, 0)";
                    });
                };
                this.livingBoard.addEventListener("mousemove", this.parallaxMove);
                this.livingBoard.addEventListener("mouseleave", this.parallaxLeave);
            }

            [playButton, nextButton].filter(Boolean).forEach((medallion) => {
                const move = (event) => {
                    const rect = medallion.getBoundingClientRect();
                    const dx = (event.clientX - (rect.left + rect.width / 2)) / (rect.width / 2);
                    const dy = (event.clientY - (rect.top + rect.height / 2)) / (rect.height / 2);
                    medallion.style.setProperty("--rb-tilt-y", `${Math.max(-12, Math.min(12, dx * 12)).toFixed(2)}deg`);
                    medallion.style.setProperty("--rb-tilt-x", `${Math.max(-9, Math.min(9, -dy * 9)).toFixed(2)}deg`);
                };
                const leave = () => {
                    medallion.style.removeProperty("--rb-tilt-x");
                    medallion.style.removeProperty("--rb-tilt-y");
                };
                medallion.addEventListener("mousemove", move);
                medallion.addEventListener("mouseleave", leave);
                this.medallionBindings.push({ medallion, move, leave });
            });
        },

        teardown() {
            if (this.livingBoard && this.parallaxMove) {
                this.livingBoard.removeEventListener("mousemove", this.parallaxMove);
                this.livingBoard.removeEventListener("mouseleave", this.parallaxLeave);
            }
            if (parallaxRaf !== null) {
                window.cancelAnimationFrame(parallaxRaf);
                parallaxRaf = null;
            }
            this.layers.forEach((layer) => {
                layer.style.transform = "translate3d(0, 0, 0)";
            });
            this.medallionBindings.forEach(({ medallion, move, leave }) => {
                medallion.removeEventListener("mousemove", move);
                medallion.removeEventListener("mouseleave", leave);
                medallion.style.removeProperty("--rb-tilt-x");
                medallion.style.removeProperty("--rb-tilt-y");
            });
            this.livingBoard = null;
            this.layers = [];
            this.parallaxMove = null;
            this.parallaxLeave = null;
            this.medallionBindings = [];
        }
    };

    function switchActivePage(pageKey) {
        const activeKey = String(pageKey || "");
        const containers = Array.from(document.querySelectorAll("[data-page-key], [data-view-key], [data-rebirth-view]"));
        const arena = document.querySelector("[data-rebirth-app]");
        if (arena && !containers.includes(arena)) {
            arena.setAttribute("data-page-key", "arena");
            containers.push(arena);
        }
        containers.forEach((container) => {
            const key = container.getAttribute("data-page-key")
                || container.getAttribute("data-view-key")
                || container.getAttribute("data-rebirth-view");
            const isActive = key === activeKey || (key === "arena" && activeKey === "rebirth");
            container.hidden = !isActive;
            container.classList.toggle("is-active", isActive);
            container.setAttribute("aria-hidden", isActive ? "false" : "true");
        });

        const arenaActive = activeKey === "arena" || activeKey === "rebirth";
        if (!arenaActive) {
            RebirthArenaLifecycle.teardown();
        } else if (arena) {
            RebirthArenaLifecycle.activate(
                RebirthStore.elements["play-button"],
                RebirthStore.elements["next-turn-button"]
            );
        }
        return activeKey;
    }

    const RebirthInput = {
        bind() {
            this.bindLogToggle();
            this.bindAnalystToggle();
            window.addEventListener("pagehide", () => {
                const state = RebirthStore.state;
                const endpoint = RebirthConfig.endpoints.telemetryBeacon || "/api/rebirth/telemetry/beacon";
                if (!endpoint || !state || state.is_finished || RebirthStore.abandonmentSentForMatch === state.match_id) {
                    return;
                }
                RebirthStore.abandonmentSentForMatch = state.match_id;
                const body = JSON.stringify({
                    event_type: "match_abandoned",
                    match_id: state.match_id,
                    reason: "pagehide",
                    csrf: window.REBIRTH_CSRF || ""
                });
                // navigator.sendBeacon is the right tool for pagehide: it's
                // queued by the browser and isn't aborted by navigation, so
                // QA stops seeing "request_failed" on the abandonment ping.
                // Fallback to keepalive fetch when sendBeacon isn't there
                // (older browsers / privacy modes).
                if (navigator.sendBeacon) {
                    try {
                        const blob = new Blob([body], { type: "application/json" });
                        if (navigator.sendBeacon(endpoint, blob)) return;
                    } catch (err) {
                        // fall through to fetch fallback below
                    }
                }
                window.fetch(endpoint, {
                    method: "POST",
                    credentials: "same-origin",
                    keepalive: true,
                    headers: { "Content-Type": "application/json" },
                    body
                }).catch(() => {});
            });

            document.querySelectorAll("[data-new-match]").forEach((button) => {
                button.addEventListener("click", () => {
                    if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                    RebirthFlow.startMatch();
                });
            });

            const playButton = RebirthStore.elements["play-button"];
            if (playButton) {
                playButton.addEventListener("click", () => {
                    if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                    if (RebirthStore.firstFieldFusion()) {
                        RebirthFlow.activateEvolutionOrFusion();
                        return;
                    }
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
                        if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                        RebirthFlow.nextTurn();
                    }
                });
            }

            const evolveButton = RebirthStore.elements["evolve-button"];
            if (evolveButton) {
                evolveButton.addEventListener("click", () => {
                    if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                    RebirthFlow.activateEvolutionOrFusion();
                });
            }

            switchActivePage("arena");

            const hand = RebirthStore.elements["player-hand"];
            if (hand) {
                hand.addEventListener("click", (event) => {
                    const button = event.target.closest("[data-card-instance]");
                    if (!button || button.disabled || RebirthStore.pending || !RebirthStore.state || RebirthStore.state.phase !== "choose") return;
                    RebirthStore.selectedInstanceId = button.getAttribute("data-card-instance");
                    RebirthStore.selectedAttackerId = null;
                    if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                    RebirthErrors.clear();
                    RebirthRenderer.render();
                });
            }

            const playerField = RebirthStore.elements["player-battlefield"];
            if (playerField) {
                playerField.addEventListener("click", (event) => {
                    const summonAction = event.target.closest("[data-summon-action]");
                    if (summonAction && !summonAction.disabled && RebirthStore.state && !RebirthStore.state.is_finished) {
                        RebirthErrors.clear();
                        RebirthRenderer.render();
                        if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                        RebirthFlow.playSelectedCard();
                        return;
                    }
                    const button = event.target.closest("[data-attacker-instance]");
                    if (!button || !RebirthStore.state || RebirthStore.state.is_finished) return;
                    RebirthStore.selectedInstanceId = null;
                    RebirthStore.selectedAttackerId = button.getAttribute("data-attacker-instance");
                    if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
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
                    if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                    RebirthFlow.attackTarget(target ? target.getAttribute("data-target-instance") : null);
                });
            }
        },

        bindAnalystToggle() {
            // F3: Análise tática colapsada por padrão. Persiste a preferência em
            // localStorage; jogador sênior abre uma vez e fica aberto.
            const toggle = document.querySelector("[data-rebirth-analyst-toggle]");
            const panel = document.querySelector("[data-rebirth-analyst-mode]");
            if (!toggle || !panel) return;
            let opened = false;
            try {
                opened = window.localStorage.getItem("rebirth.analystMode") === "1";
            } catch (e) { opened = false; }
            const apply = (state) => {
                toggle.setAttribute("aria-expanded", state ? "true" : "false");
                if (state) {
                    panel.removeAttribute("hidden");
                } else {
                    panel.setAttribute("hidden", "");
                }
            };
            apply(opened);
            toggle.addEventListener("click", () => {
                opened = !opened;
                apply(opened);
                try { window.localStorage.setItem("rebirth.analystMode", opened ? "1" : "0"); } catch (e) {}
            });
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
                button.setAttribute("aria-label", "Abrir histórico do turno");
                button.innerHTML = '<i aria-hidden="true"></i><span>Histórico</span>';
                head.appendChild(button);
                RebirthStore.elements["turn-log-toggle"] = button;
            }

            button.setAttribute("aria-expanded", "false");
            button.addEventListener("click", () => {
                const isOpen = !panel.classList.contains("is-open");
                panel.classList.toggle("is-open", isOpen);
                button.setAttribute("aria-expanded", isOpen ? "true" : "false");
                button.setAttribute("aria-label", isOpen ? "Fechar histórico do turno" : "Abrir histórico do turno");
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
    window.switchActivePage = switchActivePage;
    window.RebirthArena = {
        refreshAfterAuth(detail) {
            return RebirthFlow.refreshAfterAuth(detail);
        }
    };

    document.addEventListener("DOMContentLoaded", init);
})();
