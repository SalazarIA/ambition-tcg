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
        lastActionPopupSignature: null,
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
                "player-hero-name",
                "player-energy",
                "player-max-energy",
                "player-mana-coins",
                "player-deck-count",
                "player-discard-count",
                "bot-hp",
                "bot-hp-fill",
                "bot-hero-name",
                "bot-energy",
                "bot-max-energy",
                "bot-mana-coins",
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
                "mulligan-button",
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
                const missing = this.error("missing_endpoint", "O endpoint Rebirth não está configurado.");
                this.reportFailure(url, missing, { type: "api_missing_endpoint" });
                throw missing;
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
                const apiError = this.error("network_error", error.message || "Falha na requisição de rede.");
                this.reportFailure(url, apiError, { type: "api_network_error" });
                throw apiError;
            }

            let payload = null;
            try {
                payload = await response.json();
            } catch (_error) {
                const apiError = this.error("malformed_response", "O servidor retornou uma resposta ilegível.");
                this.reportFailure(url, apiError, { type: "api_malformed_response", status: response.status });
                throw apiError;
            }

            if (!response.ok || !payload || payload.ok !== true) {
                const serverError = payload && payload.error ? payload.error : {};
                const apiError = this.error(serverError.code || "rebirth_error", serverError.message || "A requisição Rebirth falhou.");
                this.reportFailure(url, apiError, { type: "api_failure", status: response.status });
                throw apiError;
            }

            return payload;
        },

        reportFailure(url, error, metadata) {
            const endpoint = (() => {
                try {
                    return new URL(url || "", window.location.href).pathname;
                } catch (_error) {
                    return String(url || "");
                }
            })();
            if (endpoint.indexOf("/api/rebirth/telemetry") === 0) return;
            if (!window.RebirthClientTelemetry || typeof window.RebirthClientTelemetry.report !== "function") return;
            window.RebirthClientTelemetry.report(error.message || "Falha de API Rebirth.", Object.assign({
                endpoint,
                code: error.code || "rebirth_error"
            }, metadata || {}));
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
            // #1 tablet fix: o cockpit mobile (dirigido por .rb-mobile-native)
            // cobre toda a faixa < 1180px. Antes era <= 760, deixando 761-1179
            // (tablets) numa zona morta entre mobile e o desktop-cheio (>=1180):
            // o board virava uma faixa estreita flutuante. Agora tablet usa o
            // cockpit vertical até o layout desktop assumir em 1180px.
            const nativeMobile = width < 1180;
            document.body.classList.toggle("rb-mobile-native", nativeMobile);
            // A classe acima muda a navegação de desktop para duas faixas no
            // mobile; meça somente depois dessa troca para obter a altura real.
            const navHeight = this.globalNavHeight();
            document.documentElement.style.setProperty("--rb-mobile-nav-height", `${navHeight}px`);
            // O cockpit mobile declara a variável no próprio body. Sem
            // sincronizá-la aqui, esse valor local vence o valor medido no
            // :root e o HUD começa por baixo da navegação fixa.
            document.body.style.setProperty("--rb-mobile-nav-height", `${navHeight}px`);
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
            // F20: o board desktop era 1180×760 fixo e ficava centralizado
            // com ~400px de vácuo em viewports grandes. Agora cresce com o
            // safeWidth (até 1720) — o CSS já migrou pra grid fluido.
            const desktopBaseWidth = Math.min(1720, Math.max(1180, Math.floor(safeWidth - 24)));
            const desktopBaseHeight = Math.min(960, Math.max(680, Math.floor(safeHeight - 12)));
            const baseWidth = desktop ? desktopBaseWidth : RebirthConfig.boardWidth;
            const baseHeight = desktop ? desktopBaseHeight : RebirthConfig.boardHeight;
            document.documentElement.style.setProperty("--rb-board-width", `${baseWidth}px`);
            document.documentElement.style.setProperty("--rb-board-height", `${baseHeight}px`);
            document.documentElement.style.setProperty("--rb-safe-offset-x", `${(safe.left - safe.right) / 2}px`);
            document.documentElement.style.setProperty("--rb-nav-clearance", `${navClearance}px`);
            const scale = Math.min(safeWidth / baseWidth, safeHeight / baseHeight);
            document.documentElement.style.setProperty("--rb-scale", String(scale));
            window.scrollTo(0, 0);
        },

        isNativeMobile() {
            return window.matchMedia("(max-width: 1179px)").matches;
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

    // K1: Sistema de keywords mecânicas. Mantém sincronizado com
    // services/rebirth_keywords.py (KEYWORD_LABELS e KEYWORD_COLORS).
    const RebirthKeywords = {
        LABELS: {
            RUSH:      "Investida",
            BURST:     "Detonação",
            LIFESTEAL: "Drenar",
            TAUNT:     "Provocar",
            SHIELD:    "Escudo",
            PIERCE:    "Perfurar",
            REGEN:     "Regenerar",
            EXECUTE:   "Executar",
            THORNS:    "Espinhos",
            ENTRENCH:  "Entrincheirar",
            SUNDER:    "Ruptura",
        },
        TOOLTIPS: {
            RUSH:      "Pode atacar no turno em que é invocado.",
            BURST:     "Causa 2 de dano direto ao oponente ao ser invocado.",
            LIFESTEAL: "Recupera HP igual ao dano causado em combate.",
            TAUNT:     "Inimigos devem atacar esta carta primeiro.",
            SHIELD:    "Ignora a primeira instância de dano recebida.",
            PIERCE:    "Dano excedente sobre Guarda vai direto pro HP.",
            REGEN:     "Restaura 1 de Guarda no início do turno do dono.",
            EXECUTE:   "Mata instantaneamente alvos com Guarda ≤ 1.",
            THORNS:    "Quem ataca esta carta sofre 2 de dano na Guarda.",
            ENTRENCH:  "Se não atacou no turno anterior, ganha +1 de Guarda permanente.",
            SUNDER:    "Com aliado de outra família, ganha +2 Ataque contra Provocar/Escudo e rompe Escudo.",
        },
        badges(card) {
            const kws = (card && card.keywords) || [];
            if (!kws.length) return "";
            const items = kws.map(k => {
                const label = this.LABELS[k] || k;
                const tip = this.TOOLTIPS[k] || "";
                return `<span class="rb-keyword-badge rb-kw-${k.toLowerCase()}" title="${RebirthText.escape(tip)}">${RebirthText.escape(label)}</span>`;
            });
            return `<span class="rb-keyword-strip" aria-label="Palavras-chave">${items.join("")}</span>`;
        },
    };

    function cssToken(value, fallback) {
        // Strings vindas do servidor ("Trap Armed") não podem virar classe com
        // espaço: classList.add lança exceção e derruba o render inteiro.
        const token = String(value == null ? "" : value).toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
        return token || String(fallback || "neutral");
    }

    function cardCanActNow(card) {
        if (!card) return false;
        if (card.exhausted || card.has_attacked || card.has_acted) return false;
        if (card.just_summoned && !((card.keywords || []).includes("RUSH"))) return false;
        return true;
    }

    function isDamageSpell(card) {
        if (!card || String(card.type || card.card_type).toUpperCase() !== "SPELL") return false;
        return (card.stack_effects || []).some((effect) => String(effect.type || "").toLowerCase() === "damage");
    }

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
        temporaryPools: {},


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
            // Placeholder local: produção não pode hotlinkar Unsplash (offline,
            // legal e identidade visual). Toda carta tem WebP no catálogo; o
            // fallback genérico cobre estados quebrados.
            if (!card) return "";
            return RebirthConfig.assets.fallbackCardArt || "";
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
            const inlineStyle = `${RebirthAssets.cssVars(card)};${options && options.style ? options.style : ""}`;
            return `
                <button class="${this.cardShellClasses(card, "rb-mini-card")}${selected}${recommended}${locked}${statusClass}" type="button" data-card-instance="${RebirthText.escape(card.instance_id)}" data-card-type="${RebirthText.escape(this.cardType(card))}" data-art-key="${RebirthText.escape(card.art_key || card.id)}" style="${inlineStyle}" aria-pressed="${selected ? "true" : "false"}" aria-label="${lockedReason ? RebirthText.escape(lockedReason) + ". " : ""}Selecionar ${RebirthText.escape(card.name)}, ataque ${RebirthText.escape(card.attack)}, guarda ${RebirthText.escape(card.guard)}" ${disabled}>
                    <span class="rb-card-frame-layer" aria-hidden="true"></span>
                    <b class="rb-card-cost">${RebirthText.escape(this.cardCost(card))}</b>
                    ${options && options.recommended ? '<span class="rb-recommendation-badge">MELHOR JOGADA</span>' : ""}
                    ${RebirthStatus.miniBadge(statuses)}
                    ${RebirthKeywords.badges(card)}
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
                    ${this.cardType(card) === "MONSTER" ? `<div class="rb-card-statline rb-mini-stats rb-card-hud-layer">
                        <span class="rb-card-stat is-atk"><b>${RebirthText.escape(card.attack || card.power)}</b><small>ATK</small></span>
                        <span class="rb-card-stat is-guard"><b>${RebirthText.escape(card.guard || 0)}</b><small>GUARD</small></span>
                    </div>` : ""}
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
            const copyBase = card && (card.ability_text || card.flavor || "Declare ataques, quebre a Guarda e pressione o HP.");
            const synergy = card && card.synergy_label ? ` Sinergia: ${card.synergy_label}` : "";
            return {
                name: card && (card.ability_name || this.cardRole(card) || "Combate"),
                copy: `${copyBase || ""}${synergy}`
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
            const sick = card.just_summoned && !((card.keywords || []).includes("RUSH")) ? " is-summoning-sick" : "";
            const selectedClass = selected ? " is-selected" : "";
            const attackingClass = side === "player" && selected ? " is-attacking" : "";
            const targetableClass = options && options.targetable ? " is-targetable" : "";
            const statusClass = RebirthStatus.className(statuses);
            const risk = options && options.risk ? options.risk : null;
            const riskClass = risk ? ` is-risk-${RebirthText.escape(risk.tone || "neutral")}` : "";
            const fusionClass = options && options.fusionSource ? " is-fusion-source" : "";
            const canActClass = options && options.canAct ? " can-act" : "";
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
                <button class="${this.cardShellClasses(card, "rb-field-card rb-monster-card")}${selectedClass}${attackingClass}${targetableClass}${riskClass}${fusionClass}${exhausted}${sick}${canActClass}${statusClass}" type="button" ${targetAttr}${riskAttrs} data-art-key="${RebirthText.escape(card.art_key || card.id)}" style="${RebirthAssets.cssVars(card)}; --guard-scale: ${guardScale}" aria-label="${RebirthText.escape(card.name)} no campo ${side === "player" ? "do jogador" : "do bot"}">
                    <span class="rb-card-frame-layer" aria-hidden="true"></span>
                    ${RebirthStatus.miniBadge(statuses)}
                    ${RebirthKeywords.badges(card)}
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
            const slotIndex = options && options.slotIndex != null ? Number(options.slotIndex) : null;
            const summonAttr = summonTarget
                ? `data-summon-action="true"${Number.isInteger(slotIndex) ? ` data-summon-slot="${slotIndex}"` : ""}`
                : "";
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
                return { label: "Reativo", copy: "Espera abrir brecha pra punir com habilidade.", tone: "warning" };
            }
            return { label: "Defensivo", copy: "Absorve o primeiro golpe e pune ataques fracos.", tone: "guard" };
        },

        selectedRead(card) {
            if (!card) {
                return { label: "Sem carta", copy: "Selecione um monstro para ver tempo, papel e risco." };
            }
            const attack = Number(card.attack || card.power || 0);
            const guard = Number(card.guard || 0);
            const tempo = attack * 2 + guard + Number(card.tier || 1) * 3;
            const role = RebirthMarkup.cardRole(card);
            const label = tempo >= 25 ? "Carta forte" : tempo >= 18 ? "Carta sólida" : "Carta de apoio";
            return {
                label,
                copy: `${role}: ${attack} de ataque, ${guard} de guarda.`
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
            if (score >= 6) return { label: "Você está à frente", copy: "HP, mão e baralho favorecem você." };
            if (score <= -6) return { label: "Bot à frente", copy: "Bot tem mais HP, mão ou baralho." };
            return { label: "Equilibrado", copy: "HP, mão e baralho estão parelhos." };
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

    const RebirthFloats = {
        layer() {
            return RebirthDom.byId("rebirth-float-layer");
        },

        boardPoint(node) {
            const board = RebirthStore.elements["rebirth-board"];
            const layer = this.layer();
            if (!board || !layer || !node) return null;
            const scale = RebirthCombatMotion.boardScale();
            const boardRect = board.getBoundingClientRect();
            const rect = node.getBoundingClientRect();
            return {
                x: (rect.left + rect.width / 2 - boardRect.left) / scale,
                y: (rect.top + rect.height * 0.28 - boardRect.top) / scale
            };
        },

        spawnAt(node, text, tone) {
            const point = this.boardPoint(node);
            if (!point) return;
            this.spawnXY(point.x, point.y, text, tone);
        },

        spawnXY(x, y, text, tone) {
            const layer = this.layer();
            if (!layer || RebirthFeel.reducedMotion()) return;
            const float = document.createElement("span");
            float.className = `rb-float rb-float-${cssToken(tone, "dmg")}`;
            float.textContent = String(text);
            float.style.left = `${Math.round(x)}px`;
            float.style.top = `${Math.round(y)}px`;
            layer.appendChild(float);
            window.setTimeout(() => float.remove(), 1100);
        },

        damageFromResult(state, attackerNode, targetNode) {
            const result = (state && state.result) || {};
            const damage = result.damage || {};
            const heroDamage = result.hero_damage || {};
            const botHit = Number(damage.bot || 0);
            const playerHit = Number(damage.player || 0);
            if (botHit > 0 && targetNode) this.spawnAt(targetNode, `-${botHit}`, "dmg");
            if (playerHit > 0 && attackerNode) this.spawnAt(attackerNode, `-${playerHit}`, "hurt");
            const botHero = Number(heroDamage.bot || 0);
            const playerHero = Number(heroDamage.player || 0);
            const botHud = document.querySelector(".rb-hud-bot");
            const playerHud = document.querySelector(".rb-hud-player");
            if (botHero > 0 && botHud) this.spawnAt(botHud, `-${botHero}`, "dmg");
            if (playerHero > 0 && playerHud) this.spawnAt(playerHud, `-${playerHero}`, "hurt");
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

            // A limpeza é inegociável: se qualquer fase falhar, o disco da
            // runa NÃO pode ficar congelado cobrindo o board (auditoria).
            try {
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
            } finally {
                // Restaura iluminação: tira a classe de ativo, depois limpa DOM
                stage.classList.remove("is-active", "is-rune-active", "is-burst-active");
                stage.setAttribute("aria-hidden", "true");
                // Aguarda overlay fade-out (transition 360ms) antes de purgar
                await wait(360);
                stage.innerHTML = "";
            }
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

    const RebirthGameFeel = {
        turnBannerTimer: null,
        actionPopupTimer: null,
        delayedPlayerTurnTimer: null,
        botPreviewHoldUntil: 0,
        activeSide: "player",

        layer() {
            const board = RebirthStore.elements["rebirth-board"];
            if (!board) return null;
            let layer = board.querySelector(".rb-feedback-layer");
            if (!layer) {
                layer = document.createElement("div");
                layer.className = "rb-feedback-layer";
                layer.setAttribute("aria-live", "polite");
                layer.setAttribute("aria-atomic", "true");
                layer.innerHTML = `
                    <div class="rb-turn-banner" hidden></div>
                    <div class="rb-action-popup" hidden></div>
                `;
                board.appendChild(layer);
            }
            return layer;
        },

        setActiveTurn(sideName) {
            const side = sideName === "bot" ? "bot" : "player";
            this.activeSide = side;
            const board = RebirthStore.elements["rebirth-board"];
            const playerHud = document.querySelector(".rb-hud-player");
            const botHud = document.querySelector(".rb-hud-bot");
            if (board) board.dataset.activeTurn = side;
            if (playerHud) playerHud.classList.toggle("is-active-turn", side === "player");
            if (botHud) botHud.classList.toggle("is-active-turn", side === "bot");
        },

        activeSideForState(state) {
            const phase = String((state && (state.turn_phase || state.phase)) || "").toLowerCase();
            if (phase.includes("bot") || phase.includes("enemy") || phase.includes("opponent")) {
                return "bot";
            }
            return "player";
        },

        showTurnBanner(sideName, copy) {
            const layer = this.layer();
            const banner = layer && layer.querySelector(".rb-turn-banner");
            if (!banner) return;
            const side = sideName === "bot" ? "bot" : "player";
            banner.textContent = copy || (side === "bot" ? "TURNO DO BOT" : "SEU TURNO");
            banner.dataset.turnSide = side;
            banner.hidden = false;
            restartClass(banner, "is-visible");
            if (this.turnBannerTimer) window.clearTimeout(this.turnBannerTimer);
            this.turnBannerTimer = window.setTimeout(() => {
                banner.classList.remove("is-visible");
                banner.hidden = true;
                this.turnBannerTimer = null;
            }, 1250);
        },

        previewBotTurn() {
            if (this.delayedPlayerTurnTimer) {
                window.clearTimeout(this.delayedPlayerTurnTimer);
                this.delayedPlayerTurnTimer = null;
            }
            this.setActiveTurn("bot");
            this.botPreviewHoldUntil = Date.now() + 650;
            this.showTurnBanner("bot", "TURNO DO BOT");
        },

        suppressPopupsUntil: 0,
        lastBattleTurn: null,

        showActionPopup(lines, tone, options) {
            const layer = this.layer();
            const popup = layer && layer.querySelector(".rb-action-popup");
            if (!popup || !lines || !lines.length) return;
            // Disciplina de balões: um canal por vez. Sem popup sobre o banner
            // de turno, durante a cena do bot ou logo depois dela (a cena já
            // narrou tudo com floats e lunges). A própria cena usa force.
            if (!(options && options.force)) {
                if (this.turnBannerTimer || BotTurnDirector.active) return;
                if (Date.now() < this.suppressPopupsUntil) return;
            }
            popup.dataset.tone = tone || "neutral";
            popup.innerHTML = lines
                .filter(Boolean)
                .slice(0, 3)
                .map((line) => `<span>${RebirthText.escape(line)}</span>`)
                .join("");
            popup.hidden = false;
            restartClass(popup, "is-visible");
            if (this.actionPopupTimer) window.clearTimeout(this.actionPopupTimer);
            this.actionPopupTimer = window.setTimeout(() => {
                popup.classList.remove("is-visible");
                popup.hidden = true;
                this.actionPopupTimer = null;
            }, 1550);
        },

        hpDrop(previousState, nextState, sideName) {
            if (!previousState || !nextState) return 0;
            const prevHp = Number(((previousState[sideName] || {}).hp) || 0);
            const nextHp = Number(((nextState[sideName] || {}).hp) || 0);
            return Math.max(0, prevHp - nextHp);
        },

        fieldCards(state, sideName) {
            if (!state) return [];
            const slots = sideName === "player" ? state.player_field : state.bot_field;
            return Array.isArray(slots) ? slots.filter(Boolean) : [];
        },

        shortName(card) {
            const raw = String((card && card.name) || "Unidade").trim();
            return raw.length > 16 ? `${raw.slice(0, 15)}...` : raw;
        },

        guardValue(card) {
            return Number(card && (card.current_guard != null ? card.current_guard : card.guard || 0)) || 0;
        },

        guardLossLines(previousState, nextState) {
            const lines = [];
            ["player", "bot"].forEach((sideName) => {
                const before = new Map(this.fieldCards(previousState, sideName).map((card) => [card.instance_id, card]));
                this.fieldCards(nextState, sideName).forEach((card) => {
                    const prev = before.get(card.instance_id);
                    if (!prev) return;
                    const loss = this.guardValue(prev) - this.guardValue(card);
                    if (loss > 0) lines.push(`${this.shortName(card)} -${loss}`);
                });
            });
            return lines;
        },

        resultLines(previousState, nextState) {
            if (!previousState || !nextState) return null;
            const result = nextState.result || null;
            const damage = (result && result.damage) || {};
            const clash = nextState.last_clash || {};
            const lines = [];
            let tone = "neutral";

            if (result && result.outcome === "Summon") {
                const played = (nextState.player && nextState.player.played_card) || null;
                lines.push(`${this.shortName(played)} invocada`);
                tone = "summon";
            }

            if (result && result.outcome === "Clash") {
                const playerDamage = Number(damage.player || 0);
                const botDamage = Number(damage.bot || 0);
                if (playerDamage > 0 && clash.player_card) lines.push(`${this.shortName(clash.player_card)} -${playerDamage}`);
                if (botDamage > 0 && clash.bot_card) lines.push(`${this.shortName(clash.bot_card)} -${botDamage}`);
                tone = "clash";
            }

            this.guardLossLines(previousState, nextState).forEach((line) => {
                if (!lines.includes(line)) lines.push(line);
            });

            const botHpDrop = this.hpDrop(previousState, nextState, "bot");
            const playerHpDrop = this.hpDrop(previousState, nextState, "player");
            if (botHpDrop > 0) {
                lines.unshift(`+${botHpDrop} dano direto`);
                tone = "success";
            }
            if (playerHpDrop > 0) {
                lines.unshift(`-${playerHpDrop} HP recebido`);
                tone = "danger";
            }

            if (!lines.length && result && result.message) {
                lines.push(result.message);
            }
            if (!lines.length) return null;
            return { lines: Array.from(new Set(lines)), tone };
        },

        actionResult(previousState, nextState) {
            const described = this.resultLines(previousState, nextState);
            if (!described) return;
            // Balão central é reservado a momentos de herói (HP mudou).
            const heroSwing = this.hpDrop(previousState, nextState, "player") + this.hpDrop(previousState, nextState, "bot");
            if (heroSwing <= 0) return;
            const signature = [
                nextState.match_id || "",
                nextState.turn || "",
                nextState.version || "",
                nextState.result && nextState.result.outcome,
                described.lines.join("|")
            ].join(":");
            if (signature === RebirthStore.lastActionPopupSignature) return;
            RebirthStore.lastActionPopupSignature = signature;
            this.showActionPopup(described.lines, described.tone);
        },

        damageFeedback(previousState, nextState) {
            if (!previousState || !nextState || RebirthFeel.reducedMotion()) return;
            let anyDamage = false;
            [
                { side: "player", selector: ".rb-hud-player" },
                { side: "bot", selector: ".rb-hud-bot" }
            ].forEach(({ side, selector }) => {
                if (this.hpDrop(previousState, nextState, side) <= 0) return;
                anyDamage = true;
                const hud = document.querySelector(selector);
                if (!hud) return;
                restartClass(hud, "is-taking-damage");
                window.setTimeout(() => hud.classList.remove("is-taking-damage"), 1120);
            });
            if (anyDamage) {
                const board = RebirthStore.elements["rebirth-board"];
                restartClass(board, "is-screen-hit");
                window.setTimeout(() => {
                    if (board) board.classList.remove("is-screen-hit");
                }, 220);
            }
        },

        turnTransition(previousState, nextState) {
            if (!previousState || !nextState || nextState.is_finished) return;
            const previousTurn = Number(previousState.turn || 0);
            const nextTurn = Number(nextState.turn || 0);
            if (!previousTurn || !nextTurn || previousTurn === nextTurn) return;
            if (this.delayedPlayerTurnTimer) window.clearTimeout(this.delayedPlayerTurnTimer);
            this.delayedPlayerTurnTimer = window.setTimeout(() => {
                this.setActiveTurn("player");
                this.showTurnBanner("player", "SEU TURNO");
                this.delayedPlayerTurnTimer = null;
            }, 620);
        },

        selectionPulse() {
            const selected = document.querySelector(".rb-hand .rb-mini-card.is-selected");
            if (selected) restartClass(selected, "is-selection-pulse");
        },

        evaluate(previousState, nextState) {
            if (!nextState) return;
            const turnChanged = previousState && Number(previousState.turn || 0) !== Number(nextState.turn || 0);
            const holdBotPreview = turnChanged && this.activeSide === "bot" && Date.now() < this.botPreviewHoldUntil;
            if (!holdBotPreview) {
                this.setActiveTurn(this.activeSideForState(nextState));
            }
            this.turnTransition(previousState, nextState);
            this.damageFeedback(previousState, nextState);
            this.actionResult(previousState, nextState);
        }
    };

    const BotTurnDirector = {
        active: false,
        skipRequested: false,

        botHost() {
            return RebirthStore.elements["bot-battlefield"];
        },

        playerNodeFor(instanceId) {
            if (!instanceId) return null;
            return document.querySelector(
                `#player-battlefield [data-attacker-instance="${escapeSelectorValue(instanceId)}"]`
            );
        },

        botNodeFor(instanceId) {
            if (!instanceId) return null;
            return document.querySelector(
                `#bot-battlefield [data-target-instance="${escapeSelectorValue(instanceId)}"]`
            );
        },

        injectSummon(payload) {
            const host = this.botHost();
            const card = payload && payload.card;
            if (!host || !card) return;
            const slot = Math.max(0, Math.min(2, Number(payload.field_slot != null ? payload.field_slot : card.field_slot || 0)));
            const shell = document.createElement("div");
            shell.innerHTML = RebirthMarkup.fieldCard(card, "bot", false, {}, {});
            const node = shell.firstElementChild;
            if (!node) return;
            node.classList.add("is-stage-enter");
            // Só ocupa um ALTAR VAZIO: children[slot] segue a ordem visual,
            // não o field_slot lógico — substituir às cegas roubava o lugar
            // de outra carta viva até o próximo render (auditoria: cartas
            // "sumindo" durante a cena do bot).
            const slotNode = host.children[slot];
            if (slotNode && slotNode.classList.contains("rb-field-slot-empty")) {
                host.replaceChild(node, slotNode);
            } else {
                const emptySlot = host.querySelector(".rb-field-slot-empty");
                if (emptySlot) {
                    host.replaceChild(node, emptySlot);
                } else {
                    host.appendChild(node);
                }
            }
            RebirthAssets.bindFallbacks(node);
            if (window.RebirthAudioManager) {
                window.RebirthAudioManager.observeEvents([{ type: "MONSTER_SUMMONED", payload: {} }], { hitPauseMs: 0, replayAudioMutedMode: false });
            }
        },

        lunge(attackerNode, targetNode) {
            if (!attackerNode) return;
            const fallback = document.querySelector(".rb-hud-player");
            const vector = RebirthCombatMotion.vector(attackerNode, targetNode || fallback);
            attackerNode.style.setProperty("--attack-x", `${vector.x.toFixed(1)}px`);
            attackerNode.style.setProperty("--attack-y", `${vector.y.toFixed(1)}px`);
            attackerNode.classList.add("is-attack-primed", "is-attack-lunging");
            window.setTimeout(() => {
                attackerNode.classList.remove("is-attack-lunging", "is-attack-primed");
            }, 460);
        },

        tickHp(payload) {
            if (!payload) return;
            if (payload.player_hp != null) RebirthDom.setText("player-hp", payload.player_hp);
            if (payload.bot_hp != null) RebirthDom.setText("bot-hp", payload.bot_hp);
        },

        wait(ms) {
            return this.skipRequested ? Promise.resolve() : wait(ms);
        },

        script(events) {
            const steps = [];
            for (const event of events || []) {
                const type = String(event.type || event.event_type || "");
                const actor = String(event.actor || "");
                const payload = event.payload || {};
                if (type === "TRAP_ARMED" && actor === "bot") {
                    steps.push(async () => {
                        RebirthFloats.spawnAt(document.querySelector(".rb-hud-bot"), "Armadilha armada", "info");
                        await this.wait(480);
                    });
                } else if (type === "CARD_PLAYED" && actor === "bot" && String(payload.type || "") === "SPELL") {
                    steps.push(async () => {
                        RebirthGameFeel.showActionPopup([event.message || "Bot lançou uma magia"], "danger", { force: true });
                        await this.wait(620);
                    });
                } else if (type === "MONSTER_SUMMONED" && actor === "bot") {
                    steps.push(async () => {
                        this.injectSummon(payload);
                        await this.wait(560);
                    });
                } else if (type === "ATTACK_DECLARED" && actor === "bot") {
                    steps.push(async () => {
                        const attacker = this.botNodeFor(payload.attacker_instance_id);
                        const target = this.playerNodeFor(payload.target_instance_id);
                        this.lunge(attacker, target);
                        await this.wait(380);
                    });
                } else if (type === "CLASH_RESOLVED" && actor !== "player") {
                    steps.push(async () => {
                        const damage = payload.damage || {};
                        const playerHit = Number(damage.player || 0);
                        const botHit = Number(damage.bot || 0);
                        const playerCard = payload.player_card || {};
                        const playerNode = this.playerNodeFor(playerCard.instance_id);
                        if (playerHit > 0) {
                            RebirthFloats.spawnAt(playerNode || document.querySelector(".rb-hud-player"), `-${playerHit}`, "hurt");
                            if (playerNode) restartClass(playerNode, "is-taking-hit");
                        }
                        if (botHit > 0) {
                            const botCard = payload.bot_card || {};
                            RebirthFloats.spawnAt(this.botNodeFor(botCard.instance_id), `-${botHit}`, "dmg");
                        }
                        triggerScreenShake(playerHit + botHit >= 5 ? "heavy" : "normal");
                        await this.wait(560);
                    });
                } else if (type === "DAMAGE_RESOLVED" && payload.direct) {
                    steps.push(async () => {
                        this.tickHp(payload);
                        const playerHit = Number(payload.player || 0);
                        if (playerHit > 0) {
                            RebirthFloats.spawnAt(document.querySelector(".rb-hud-player"), `-${playerHit}`, "hurt");
                            const hud = document.querySelector(".rb-hud-player");
                            if (hud) restartClass(hud, "is-taking-damage");
                        }
                        triggerScreenShake("normal");
                        await this.wait(540);
                    });
                } else if (type === "DAMAGE_RESOLVED" && !payload.direct) {
                    steps.push(async () => {
                        this.tickHp(payload);
                        await this.wait(140);
                    });
                } else if (type === "UNIT_DESTROYED") {
                    steps.push(async () => {
                        const node = this.playerNodeFor(payload.instance_id) || this.botNodeFor(payload.instance_id);
                        if (node) node.classList.add("is-dead-dissolve");
                        await this.wait(360);
                    });
                } else if (type === "FATIGUE_DAMAGE") {
                    steps.push(async () => {
                        const side = String(payload.side || "player");
                        RebirthFloats.spawnAt(document.querySelector(side === "bot" ? ".rb-hud-bot" : ".rb-hud-player"), `Fadiga -${payload.amount}`, "hurt");
                        await this.wait(420);
                    });
                } else if (type === "REGEN_TICK") {
                    steps.push(async () => {
                        RebirthFloats.spawnAt(this.botNodeFor(payload.instance_id) || this.playerNodeFor(payload.instance_id), `+${payload.amount}`, "heal");
                        await this.wait(300);
                    });
                }
            }
            return steps;
        },

        async stage(events) {
            if (RebirthFeel.reducedMotion()) return;
            const steps = this.script(events);
            if (!steps.length) return;
            this.active = true;
            this.skipRequested = false;
            const board = RebirthStore.elements["rebirth-board"];
            if (board) board.classList.add("is-bot-staging");
            // Clareza: enquanto a cena roda, o botão de turno explica a espera.
            const endTurn = document.getElementById("next-turn-button");
            const endTurnLabel = endTurn ? endTurn.innerHTML : null;
            if (endTurn) {
                endTurn.innerHTML = '<i class="rb-action-loop" aria-hidden="true"></i><span>Turno inimigo…</span>';
                endTurn.disabled = true;
            }
            try {
                for (const step of steps) {
                    if (this.skipRequested) break;
                    await step();
                }
            } finally {
                this.active = false;
                if (board) board.classList.remove("is-bot-staging");
                if (endTurn && endTurnLabel != null) {
                    endTurn.innerHTML = endTurnLabel;
                    endTurn.disabled = false;
                }
            }
        },

        bind() {
            const board = RebirthStore.elements["rebirth-board"];
            if (!board) return;
            board.addEventListener("pointerdown", () => {
                if (this.active) this.skipRequested = true;
            });
        }
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
                overlay.classList.remove("is-active", "is-victory", "is-defeat", "is-first-duel", "is-settled");
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
            // Cerimônia: o fim de partida tem resumo e próxima decisão, não
            // só um texto que evapora (auditoria: derrota seca, sem CTA).
            const state = RebirthStore.state || {};
            const summaryRows = [];
            if (state.turn) summaryRows.push(`<span>Turnos<strong>${RebirthText.escape(state.turn)}</strong></span>`);
            if (state.player && state.player.hp != null) summaryRows.push(`<span>Seu HP<strong>${RebirthText.escape(state.player.hp)}</strong></span>`);
            if (state.bot && state.bot.hp != null) summaryRows.push(`<span>HP do bot<strong>${RebirthText.escape(state.bot.hp)}</strong></span>`);
            const reward = RebirthStore.campaignReward || RebirthStore.reward || null;
            if (reward && (reward.xp || reward.gold)) {
                const parts = [];
                if (reward.xp) parts.push(`+${reward.xp} XP`);
                if (reward.gold) parts.push(`+${reward.gold} Ouro`);
                summaryRows.push(`<span>Recompensa<strong>${RebirthText.escape(parts.join(" · "))}</strong></span>`);
            }
            overlay.innerHTML = `
                <div class="vfx-finale-curtain"></div>
                <div class="vfx-finale-text">${headline}</div>
                ${sublineCopy}
                <div class="vfx-finale-panel">
                    <div class="vfx-finale-summary">${summaryRows.join("")}</div>
                    <div class="vfx-finale-actions">
                        <button type="button" class="rb-button-primary rb-cta" data-finale-rematch>Jogar de novo</button>
                        <button type="button" class="rb-button-secondary rb-secondary" data-finale-close>Continuar</button>
                    </div>
                </div>
            `;
            const rematch = overlay.querySelector("[data-finale-rematch]");
            if (rematch) {
                rematch.addEventListener("click", () => {
                    if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                    RebirthFlow.startMatch({ forceNew: true });
                });
            }
            const closeButton = overlay.querySelector("[data-finale-close]");
            if (closeButton) {
                closeButton.addEventListener("click", () => this.reset());
            }
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

            // O texto-impacto assenta e o painel de decisão permanece até o
            // jogador escolher (rematch/continuar ou nova partida externa).
            const settleMs = firstDuel && isVictory ? 4300 : 2800;
            window.setTimeout(() => {
                overlay.classList.add("is-settled");
            }, settleMs);
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
            this.animateCounter("player-hp", state.player.hp);
            this.animateCounter("bot-hp", state.bot.hp);
            RebirthDom.setText("player-energy", state.player.energy);
            RebirthDom.setText("player-max-energy", state.player.max_energy);
            RebirthDom.setText("bot-energy", state.bot.energy);
            RebirthDom.setText("bot-max-energy", state.bot.max_energy);
            RebirthDom.setText("player-deck-count", `Baralho ${state.player.deck_count || 0}`);
            RebirthDom.setText("player-discard-count", `Descarte ${state.player.discard_count || 0}`);
            RebirthDom.setText("bot-deck-count", `Baralho ${state.bot.deck_count || 0}`);
            RebirthDom.setText("bot-discard-count", `Descarte ${state.bot.discard_count || 0}`);
            this.trapZones(state);
            RebirthDom.setText("turn-number", String(state.turn).padStart(2, "0"));
            const bossName = state.campaign && state.campaign.presentation && state.campaign.presentation.name;
            const botName = bossName || (state.bot_profile && state.bot_profile.name) || "Bot";
            RebirthDom.setText("bot-profile-label", botName);
            RebirthDom.setText("bot-hero-name", botName);
            RebirthDom.setText("player-hero-name", (RebirthConfig.player.account && RebirthConfig.player.account.name) || "Sky");
            this.hpBars();
            this.manaCoins("player", state.player.energy, state.player.max_energy);
        },

        // LP counter estilo YGO: o HP rola até o valor novo em vez de teleportar.
        counterTimers: {},
        animateCounter(id, target) {
            const el = RebirthDom.byId(id);
            if (!el) return;
            const goal = Number(target || 0);
            const current = parseInt(el.textContent, 10);
            if (!Number.isFinite(current) || current === goal || RebirthFeel.reducedMotion()) {
                el.textContent = goal;
                return;
            }
            if (this.counterTimers[id]) window.cancelAnimationFrame(this.counterTimers[id]);
            const startedAt = performance.now();
            const from = current;
            const durationMs = 460;
            const tick = (now) => {
                const progress = Math.min(1, (now - startedAt) / durationMs);
                const eased = 1 - Math.pow(1 - progress, 3);
                el.textContent = Math.round(from + (goal - from) * eased);
                if (progress < 1) {
                    this.counterTimers[id] = window.requestAnimationFrame(tick);
                } else {
                    this.counterTimers[id] = null;
                }
            };
            this.counterTimers[id] = window.requestAnimationFrame(tick);
        },

        // Zona de Magia & Trap (YGO): suas armadilhas SET com nome; as do
        // oponente como cartas viradas — você vê o perigo, não o conteúdo.
        trapZones(state) {
            const mine = RebirthDom.byId("player-trap-zone");
            if (mine) {
                const traps = (state.player && state.player.traps) || [];
                mine.innerHTML = traps
                    .map((trap) => `<i class="rb-trap-chip is-mine" title="${RebirthText.escape(trap.name || "Armadilha")} — armada e pronta">${RebirthText.escape(trap.name || "Armadilha")}</i>`)
                    .join("");
                mine.hidden = traps.length === 0;
            }
            const theirs = RebirthDom.byId("bot-trap-zone");
            if (theirs) {
                const traps = (state.bot && state.bot.traps) || [];
                theirs.innerHTML = traps
                    .map(() => '<i class="rb-trap-chip is-set" title="Carta virada para baixo — pode ser uma armadilha">?</i>')
                    .join("");
                theirs.hidden = traps.length === 0;
            }
            this.manaCoins("bot", state.bot.energy, state.bot.max_energy);
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
            RebirthTargeting.sync();
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

        manaCoins(sideName, energy, maxEnergy) {
            const host = RebirthStore.elements[`${sideName}-mana-coins`];
            if (!host) return;
            const total = Math.max(0, Math.min(10, Number(maxEnergy || energy || 0)));
            const available = Math.max(0, Math.min(total, Number(energy || 0)));
            const previousAvailable = host.dataset.available == null ? null : Number(host.dataset.available);
            const gainedMana = previousAvailable != null && available > previousAvailable;
            host.dataset.available = String(available);
            host.dataset.max = String(total);
            host.innerHTML = Array.from({ length: total }).map((_, index) => {
                const spent = index >= available ? " is-spent" : "";
                return `<span class="rb-mana-coin${spent}" style="--coin-index:${index}" aria-hidden="true"></span>`;
            }).join("");
            if (gainedMana) {
                restartClass(host, "is-mana-gaining");
            }
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

        visualFieldSlots(slots) {
            // O display agora espelha a posição LÓGICA dos slots: a fusão exige
            // adjacência real, então remapear visualmente enganava o jogador.
            return (slots || []).slice(0, FIELD_SLOT_COUNT);
        },

        decorateFieldHost(host, sideName, cardCount) {
            if (!host) return;
            host.dataset.side = sideName;
            host.dataset.cardCount = String(cardCount || 0);
            host.classList.toggle("has-active-cards", Number(cardCount || 0) > 0);
        },

        battlefield() {
            const playerHost = RebirthStore.elements["player-battlefield"];
            const botHost = RebirthStore.elements["bot-battlefield"];
            const state = RebirthStore.state;
            if (!playerHost || !botHost || !state) return;
            const playerCards = RebirthStore.fieldCards("player");
            const botCards = RebirthStore.fieldCards("bot");
            const playerSlots = this.visualFieldSlots(RebirthStore.fieldSlots("player"));
            const botSlots = this.visualFieldSlots(RebirthStore.fieldSlots("bot"));
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
            this.decorateFieldHost(playerHost, "player", playerCards.length);
            this.decorateFieldHost(botHost, "bot", botCards.length);
            playerHost.innerHTML = playerSlots.map((card, slotIndex) => {
                if (card) {
                    return RebirthMarkup.fieldCard(card, "player", card.instance_id === RebirthStore.selectedAttackerId, playerStatuses, {
                        fusionSource: fusionMaterialIds.has(card.instance_id),
                        canAct: cardCanActNow(card) && state.phase === "choose" && !state.is_finished && !RebirthStore.pending
                    });
                }
                return RebirthMarkup.emptyFieldSlot(canSummonSelected ? "Invocar" : summonLockCopy, {
                    summonTarget: Boolean(canSummonSelected),
                    locked: !canSummonSelected,
                    slotIndex,
                    reason: canSummonSelected ? `Invocar ${selectedHandCard.name} no slot ${slotIndex + 1}` : summonLockCopy
                });
            }).join("");
            // v92: o slot vazio vira altar visual; a razão fica em aria/title.
            botHost.innerHTML = botSlots.map((card, index) => {
                if (card) {
                    return RebirthMarkup.fieldCard(card, "bot", choosingAttack, botStatuses, {
                        targetable: choosingAttack,
                        risk: choosingAttack ? RebirthTactics.clashRisk(selectedAttacker, card) : null
                    });
                }
                const isLead = !botCards.length ? index === 1 : index === 0;
                if (!isLead) {
                    return RebirthMarkup.emptyFieldSlot("", { reason: "Slot vazio do bot" });
                }
                return RebirthMarkup.emptyFieldSlot(firstTurnDirectLocked ? "Protegido no turno 1" : "", {
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
            // F10: o overlay do bot-card sobrepunha o slot na zona do bot
            // sempre que o bot tinha cartas em campo (o foco repetia a carta
            // que já estava no slot mini). Quando o battlefield tem cards, o
            // overlay vira face-down (placeholder) em vez de duplicar o foco.
            const botField = (RebirthStore.state.bot && RebirthStore.state.bot.battlefield) || [];
            if (botField.length > 0 || !card) {
                // Verso de carta permanente lia-se como "carta oculta" e era
                // o fantasma da auditoria. Com o campo do bot visível e a
                // cena do turno narrando as jogadas, o overlay só existe
                // quando tem informação real (a carta jogada, campo vazio).
                host.className = "rb-bot-card rb-card-back is-empty";
                host.removeAttribute("data-element");
                host.removeAttribute("data-art-key");
                host.removeAttribute("data-statuses");
                host.removeAttribute("style");
                host.innerHTML = "";
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
            const center = (hand.length - 1) / 2;
            host.innerHTML = hand.map((card, index) => {
                const offset = index - center;
                const rotation = hand.length > 1 ? Math.max(-10, Math.min(10, offset * 4.2)) : 0;
                const fanStyle = [
                    `--fan-index:${index}`,
                    `--fan-total:${hand.length}`,
                    `--fan-offset:${offset.toFixed(2)}`,
                    `--fan-rotate:${rotation.toFixed(2)}deg`,
                    `--fan-arc:${(Math.abs(offset) * 13).toFixed(1)}px`,
                    `--fan-z:${100 + index}`,
                    `--draw-delay:${Math.min(360, index * 52)}ms`
                ].join(";");
                return RebirthMarkup.miniCard(card, {
                    selected: card.instance_id === RebirthStore.selectedInstanceId,
                    recommended: recommended && card.instance_id === recommended.instance_id,
                    statuses: card.instance_id === RebirthStore.selectedInstanceId ? RebirthStore.state.player.statuses : null,
                    style: fanStyle,
                    locked: !canChoose || energy < RebirthMarkup.cardCost(card) || (RebirthMarkup.isMonster(card) && !hasOpenSlot),
                    lockedReason: !canChoose
                        ? "Ação indisponível fora da sua fase principal"
                        : energy < RebirthMarkup.cardCost(card)
                            ? `Sem mana suficiente: precisa de ${RebirthMarkup.cardCost(card)}`
                            : RebirthMarkup.isMonster(card) && !hasOpenSlot
                                ? "Sem slot livre"
                                : ""
                });
            }).join("");
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
                panel.classList.remove("is-victory", "is-defeat", "is-clash", "is-first-duel", "is-idle");
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
                    panel.classList.add(`is-${cssToken(result.outcome, "clash")}`);
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
            if (panel) {
                panel.classList.add("is-idle");
            }
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
            // F9: "Prioridade: jogador" virou "Sua vez de jogar" / "Vez do bot".
            const priorityRaw = String(context.priority_label || "");
            const priorityCopy = /jogador/i.test(priorityRaw)
                ? "Sua vez de jogar"
                : /bot/i.test(priorityRaw)
                    ? "Vez do bot"
                    : priorityRaw || "Aguardando";
            RebirthDom.setText("priority-label", priorityCopy);
            const chainEventCount = Number(context.chain_event_count || 0) || 0;
            // audit #9: o id técnico ("EVENT-000001") vazava pra UI. O jogador
            // só precisa saber que há uma cadeia ativa e quantos efeitos ela
            // empilha — não o identificador interno.
            // F9+F15: linguagem de jogador, sem jargão de "cadeia" de motor.
            // Só anuncia sequência quando ≥2 efeitos (1 efeito não é cadeia).
            RebirthDom.setText(
                "chain-label",
                context.chain_id && chainEventCount >= 2
                    ? `${chainEventCount} efeitos em sequência`
                    : "Sem efeitos pendentes"
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
            RebirthDom.setText("interrupt-label", context.interrupt_label || "Sem reação ativa");
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
            const recapMarkup = window.RebirthPostMatchRecap
                && typeof window.RebirthPostMatchRecap.render === "function"
                ? window.RebirthPostMatchRecap.render(reward, RebirthText.escape)
                : "";
            if (!reward.persisted) {
                host.innerHTML = '<span class="rb-reward-muted">' + RebirthText.escape(reward.message) + "</span>" + recapMarkup;
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
                reward.next_goal ? "<span>" + RebirthText.escape(reward.next_goal) + "</span>" : "",
                recapMarkup
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
            const attackerReady = cardCanActNow(selectedAttacker);
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
                    btn.innerHTML = '<i class="rb-action-sword" aria-hidden="true"></i><span>Encerrado</span>';
                    btn.disabled = true;
                    btn.title = "A partida foi encerrada.";
                } else if (state.phase === "result") {
                    actionState = "resolved";
                    btn.innerHTML = '<i class="rb-action-sword" aria-hidden="true"></i><span>Combate resolvido</span>';
                    btn.disabled = true;
                    btn.title = "Combate resolvido. Avance para o próximo turno.";
                } else if (fieldFusion) {
                    actionState = "fusion";
                    btn.innerHTML = '<i class="rb-action-loop" aria-hidden="true"></i><span>Fundir</span>';
                    btn.disabled = !canChoose;
                    btn.title = `Fundir ${fieldFusion.sourceName} x2 em uma forma evoluida.`;
                    actionCopyOverride = `Funda ${fieldFusion.sourceName} x2.`;
                } else if (selectedAttacker) {
                    actionState = attackRisk && attackRisk.tone ? `attack-${attackRisk.tone}` : "attack";
                    btn.innerHTML = '<i class="rb-action-sword" aria-hidden="true"></i><span>Atacar</span>';
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
                    btn.innerHTML = `<i class="rb-action-sword" aria-hidden="true"></i><span>${isMonster ? "Invocar" : "Jogar"}${selected ? ` ${cost}` : ""}</span>`;
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
            const readyAttacker = fieldCards.find((card) => cardCanActNow(card));
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
            const mulliganButton = RebirthStore.elements["mulligan-button"];
            if (mulliganButton) {
                const canMulligan = Boolean(state.mulligan_available) && !state.is_finished;
                mulliganButton.hidden = !canMulligan;
                mulliganButton.disabled = !canMulligan || RebirthStore.pending;
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
                    nextButton.innerHTML = '<i class="rb-action-loop" aria-hidden="true"></i><span>Próximo turno</span>';
                    nextButton.disabled = !canNext;
                    nextButton.title = "Avance para preparar o próximo turno.";
                    RebirthDom.setText("secondary-action-copy", "Prepare seu campo");
                } else if (state.is_finished) {
                    nextButton.innerHTML = '<i class="rb-action-loop" aria-hidden="true"></i><span>Encerrado</span>';
                    nextButton.disabled = true;
                    nextButton.title = "A partida foi encerrada.";
                    RebirthDom.setText("secondary-action-copy", "Inicie uma nova partida");
                } else {
                    nextButton.innerHTML = '<i class="rb-action-loop" aria-hidden="true"></i><span>Encerrar turno</span>';
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

    const RebirthGraveyard = {
        // YGO v104: cemitério é zona pública consultável — clicar no contador
        // de descarte abre as cartas destruídas dos dois lados.
        overlay() {
            return RebirthDom.byId("rebirth-graveyard-overlay");
        },

        cardChip(card) {
            const element = cssToken(card.element || card.family || "vazio");
            const type = String(card.type || card.card_type || "").toUpperCase();
            const stats = type === "MONSTER"
                ? `<span class="rb-grave-stats"><b>${RebirthText.escape(card.attack != null ? card.attack : "?")}</b> ATK · <b>${RebirthText.escape(card.guard != null ? card.guard : "?")}</b> GRD</span>`
                : `<span class="rb-grave-stats">${RebirthText.escape(type === "SPELL" ? "Magia" : type === "TRAP" ? "Armadilha" : type || "Carta")}</span>`;
            return `
                <article class="rb-grave-card is-element-${element}">
                    <strong>${RebirthText.escape(card.name || "?")}</strong>
                    <small>${RebirthText.escape(card.element || "Vazio")} · T${RebirthText.escape(card.tier || 1)}</small>
                    ${stats}
                </article>
            `;
        },

        open(sideName) {
            const overlay = this.overlay();
            const state = RebirthStore.state;
            if (!overlay || !state) return;
            const side = sideName === "bot" ? state.bot : state.player;
            const cards = (side && side.graveyard) || [];
            RebirthDom.setText("graveyard-kicker", sideName === "bot" ? "Cemitério do oponente" : "Seu cemitério");
            RebirthDom.setText("graveyard-title", cards.length ? `${cards.length} carta${cards.length > 1 ? "s" : ""} destruída${cards.length > 1 ? "s" : ""}` : "Nada destruído ainda");
            const host = RebirthDom.byId("graveyard-cards");
            if (host) {
                host.innerHTML = cards.length
                    ? cards.slice().reverse().map((card) => this.cardChip(card)).join("")
                    : '<p class="rb-grave-empty">As cartas destruídas dos dois lados aparecem aqui — informação pública, como manda um TCG.</p>';
            }
            const tabPlayer = RebirthDom.byId("graveyard-tab-player");
            const tabBot = RebirthDom.byId("graveyard-tab-bot");
            if (tabPlayer) tabPlayer.classList.toggle("is-active-tab", sideName !== "bot");
            if (tabBot) tabBot.classList.toggle("is-active-tab", sideName === "bot");
            overlay.hidden = false;
        },

        close() {
            const overlay = this.overlay();
            if (overlay) overlay.hidden = true;
        },

        bind() {
            const gyButton = RebirthDom.byId("graveyard-button");
            if (gyButton) gyButton.addEventListener("click", () => this.open("player"));
            const playerCounter = RebirthDom.byId("player-discard-count");
            const botCounter = RebirthDom.byId("bot-discard-count");
            if (playerCounter) playerCounter.addEventListener("click", () => this.open("player"));
            if (botCounter) botCounter.addEventListener("click", () => this.open("bot"));
            const closeButton = RebirthDom.byId("graveyard-close");
            if (closeButton) closeButton.addEventListener("click", () => this.close());
            const tabPlayer = RebirthDom.byId("graveyard-tab-player");
            const tabBot = RebirthDom.byId("graveyard-tab-bot");
            if (tabPlayer) tabPlayer.addEventListener("click", () => this.open("player"));
            if (tabBot) tabBot.addEventListener("click", () => this.open("bot"));
            const overlay = this.overlay();
            if (overlay) {
                overlay.addEventListener("click", (event) => {
                    if (event.target === overlay) this.close();
                });
            }
            document.addEventListener("keydown", (event) => {
                if (event.key === "Escape") this.close();
            });
        }
    };

    const RebirthMulligan = {
        dismissedFor: null,

        overlay() {
            return RebirthDom.byId("rebirth-mulligan-overlay");
        },

        maybeShow(state) {
            const overlay = this.overlay();
            if (!overlay) return;
            if (!state || !state.mulligan_available || state.is_finished) {
                this.hide();
                return;
            }
            // Primeiro duelo guiado: o tutorial conduz a mão — sem decisão de
            // mulligan em cima (o botão segue disponível para quem procurar).
            if (RebirthStore.guidedFirstMatch) return;
            if (this.dismissedFor === state.match_id) return;
            const host = RebirthDom.byId("mulligan-cards");
            if (host) {
                host.innerHTML = ((state.player && state.player.hand) || [])
                    .map((card) => RebirthMarkup.miniCard(card, {}))
                    .join("");
                RebirthAssets.bindFallbacks(host);
            }
            overlay.hidden = false;
            document.body.classList.add("rb-mulligan-open");
        },

        hide() {
            const overlay = this.overlay();
            if (overlay) overlay.hidden = true;
            document.body.classList.remove("rb-mulligan-open");
        },

        keep() {
            if (RebirthStore.state) this.dismissedFor = RebirthStore.state.match_id;
            this.hide();
        },

        reopen() {
            this.dismissedFor = null;
            this.maybeShow(RebirthStore.state);
        },

        bind() {
            const overlay = this.overlay();
            if (overlay) {
                // Clique no backdrop = manter a mão (nunca prende o jogador).
                overlay.addEventListener("click", (event) => {
                    if (event.target === overlay) this.keep();
                });
            }
            const keepButton = RebirthDom.byId("mulligan-keep");
            const swapButton = RebirthDom.byId("mulligan-swap");
            if (keepButton) {
                keepButton.addEventListener("click", () => {
                    if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                    this.keep();
                });
            }
            if (swapButton) {
                swapButton.addEventListener("click", async () => {
                    if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                    if (RebirthStore.state) this.dismissedFor = RebirthStore.state.match_id;
                    this.hide();
                    await RebirthFlow.mulligan();
                });
            }
        }
    };

    const RebirthTargeting = {
        activeAttackerId: null,
        hoverPreview: null,

        svg() {
            return RebirthDom.byId("rebirth-target-arrow");
        },

        boardPointFromClient(clientX, clientY) {
            const board = RebirthStore.elements["rebirth-board"];
            if (!board) return null;
            const scale = RebirthCombatMotion.boardScale();
            const rect = board.getBoundingClientRect();
            return { x: (clientX - rect.left) / scale, y: (clientY - rect.top) / scale };
        },

        nodeCenter(node) {
            if (!node) return null;
            const rect = node.getBoundingClientRect();
            return this.boardPointFromClient(rect.left + rect.width / 2, rect.top + rect.height / 2);
        },

        estimateStrike(attacker, defender) {
            const attack = Number(attacker && (attacker.attack || attacker.power) || 0);
            if (!defender) {
                return { dmg: Math.max(1, attack), dies: false, shielded: false, direct: true };
            }
            const mitigation = Math.floor(Number(defender.guard || 0) / 2);
            const dmg = Math.max(1, attack - mitigation);
            const guardNow = Number(defender.current_guard != null ? defender.current_guard : defender.guard || 0);
            const shielded = (defender.keywords || []).includes("SHIELD") && !defender.shield_consumed;
            return { dmg, dies: !shielded && dmg >= guardNow, shielded, direct: false };
        },

        sync() {
            const state = RebirthStore.state;
            const attackerId = RebirthStore.selectedAttackerId;
            const attackerCard = attackerId ? RebirthStore.fieldCard(attackerId) : null;
            if (!state || state.is_finished || !attackerId || !attackerCard || !cardCanActNow(attackerCard)) {
                this.deactivate();
                return;
            }
            this.activeAttackerId = attackerId;
            const svg = this.svg();
            const board = RebirthStore.elements["rebirth-board"];
            if (svg && board) {
                const scale = RebirthCombatMotion.boardScale();
                const rect = board.getBoundingClientRect();
                svg.setAttribute("viewBox", `0 0 ${(rect.width / scale).toFixed(0)} ${(rect.height / scale).toFixed(0)}`);
                svg.classList.add("is-active");
            }
            // Alvos válidos pulsam (TAUNT restringe, espelhando a engine).
            const defenders = RebirthStore.fieldCards("bot");
            const taunts = defenders.filter((card) => (card.keywords || []).includes("TAUNT"));
            const validIds = new Set((taunts.length ? taunts : defenders).map((card) => card.instance_id));
            document.querySelectorAll("#bot-battlefield [data-target-instance]").forEach((node) => {
                node.classList.toggle("is-valid-target", validIds.has(node.getAttribute("data-target-instance")));
            });
            const direct = document.querySelector("#bot-battlefield [data-direct-attack]");
            if (direct && !taunts.length) direct.classList.add("is-valid-target");
            this.pointTo(null, null);
        },

        pointTo(clientX, clientY) {
            const svg = this.svg();
            if (!svg || !this.activeAttackerId) return;
            const attackerNode = document.querySelector(
                `#player-battlefield [data-attacker-instance="${escapeSelectorValue(this.activeAttackerId)}"]`
            );
            const from = this.nodeCenter(attackerNode);
            if (!from) return;
            let to = null;
            if (clientX != null) {
                to = this.boardPointFromClient(clientX, clientY);
            } else {
                const fallback = document.querySelector("#bot-battlefield .is-valid-target");
                to = this.nodeCenter(fallback) || { x: from.x, y: from.y - 170 };
            }
            if (!to) return;
            const lift = Math.max(70, Math.abs(from.y - to.y) * 0.35);
            const controlX = (from.x + to.x) / 2;
            const controlY = Math.min(from.y, to.y) - lift;
            const d = `M ${from.x.toFixed(1)} ${from.y.toFixed(1)} Q ${controlX.toFixed(1)} ${controlY.toFixed(1)} ${to.x.toFixed(1)} ${to.y.toFixed(1)}`;
            svg.querySelectorAll("path").forEach((path) => {
                if (!path.closest("marker")) path.setAttribute("d", d);
            });
        },

        previewFor(targetNode) {
            this.clearPreview();
            if (!this.activeAttackerId || !targetNode) return;
            const attacker = RebirthStore.fieldCard(this.activeAttackerId);
            if (!attacker) return;
            const targetId = targetNode.getAttribute("data-target-instance");
            const defender = targetId
                ? RebirthStore.fieldCards("bot").find((card) => card.instance_id === targetId)
                : null;
            if (targetId && !defender) return;
            const estimate = this.estimateStrike(attacker, defender);
            const chip = document.createElement("span");
            chip.className = "rb-strike-preview";
            if (estimate.shielded) {
                chip.textContent = "Escudo absorve";
                chip.dataset.tone = "shield";
            } else {
                chip.textContent = estimate.dies ? `-${estimate.dmg} ☠` : `-${estimate.dmg}`;
                chip.dataset.tone = estimate.dies ? "kill" : "hit";
            }
            targetNode.appendChild(chip);
            this.hoverPreview = chip;
        },

        clearPreview() {
            if (this.hoverPreview) {
                this.hoverPreview.remove();
                this.hoverPreview = null;
            }
        },

        deactivate() {
            this.activeAttackerId = null;
            this.clearPreview();
            const svg = this.svg();
            if (svg) svg.classList.remove("is-active");
            document.querySelectorAll(".is-valid-target").forEach((node) => node.classList.remove("is-valid-target"));
        },

        bind() {
            document.addEventListener("pointermove", (event) => {
                if (!this.activeAttackerId) return;
                this.pointTo(event.clientX, event.clientY);
                const target = event.target && event.target.closest
                    ? event.target.closest("#bot-battlefield .is-valid-target")
                    : null;
                if (target && !target.contains(this.hoverPreview)) {
                    this.previewFor(target);
                } else if (!target) {
                    this.clearPreview();
                }
            }, { passive: true });
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
                if (await this.tryResyncAfterNetworkError(error)) {
                    return;
                }
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

        async tryResyncAfterNetworkError(error) {
            // Resiliência: se a conexão piscou no meio de um comando, o
            // resume (leitura pura) ressincroniza o board com a verdade do
            // servidor — tanto faz se o comando chegou lá ou não, o jogador
            // vê o estado real e segue, em vez de um erro seco.
            if (!error || error.code !== "network_error") return false;
            const matchId = RebirthStore.state && RebirthStore.state.match_id;
            if (!matchId || !RebirthConfig.endpoints.resume || RebirthStore.state.is_finished) return false;
            try {
                const payload = await RebirthApi.post(RebirthConfig.endpoints.resume, { match_id: matchId });
                if (payload && payload.state) {
                    this.applyState(payload.state);
                    RebirthErrors.show("Conexão instável — duelo ressincronizado. Confira o board e siga.");
                    return true;
                }
            } catch (_resyncError) {
                // sem rede de verdade: cai no erro original
            }
            return false;
        },

        persistReconnectHint(state) {
            if (!state || !state.match_id || !window.localStorage) return;
            try {
                window.localStorage.setItem("rebirth.lastMatchId", state.match_id);
                window.localStorage.setItem("rebirth.lastMatchFinished", state.is_finished ? "1" : "0");
            } catch (err) {
                /* storage may be disabled */
            }
        },

        async maybeResumeMatch(options) {
            options = options || {};
            if (options.forceNew || !RebirthConfig.endpoints.resume || RebirthStore.guidedFirstMatch) {
                return null;
            }
            let matchId = "";
            let finished = "1";
            try {
                matchId = window.localStorage ? window.localStorage.getItem("rebirth.lastMatchId") || "" : "";
                finished = window.localStorage ? window.localStorage.getItem("rebirth.lastMatchFinished") || "1" : "1";
            } catch (err) {
                return null;
            }
            if (!matchId || finished === "1") return null;
            try {
                return await RebirthApi.post(RebirthConfig.endpoints.resume, { match_id: matchId });
            } catch (err) {
                try {
                    window.localStorage.removeItem("rebirth.lastMatchId");
                    window.localStorage.removeItem("rebirth.lastMatchFinished");
                } catch (storageErr) {}
                return null;
            }
        },

        applyState(state) {
            // v55 Fase 4 — captura estado anterior ANTES do setState pra
            // os módulos de assinatura compararem HP/finished. Roda em
            // microtask depois pra não bloquear o render.
            const previousState = RebirthStore.state;
            RebirthStore.setState(state);
            this.persistReconnectHint(state);
            RebirthRenderer.render();
            try {
                RebirthMulligan.maybeShow(state);
                RebirthTargeting.sync();
                RebirthFusionMotion.observeStateEvents(previousState, state);
                RebirthHeroDamage.evaluate(previousState, state);
                RebirthGameFeel.evaluate(previousState, state);
                RebirthFinaleOverlay.evaluate(previousState, state);
                if (window.RebirthBossFX) window.RebirthBossFX.observe(previousState, state);
            } catch (err) {
                /* nunca deixa VFX falhar derrubar a UI */
                if (window.console) console.warn("[rebirth] signature VFX failed", err);
            }
            // S1: dispara tutorial in-game se for primeira partida do user autenticado.
            // Tolerante: nunca derruba UI.
            try {
                if (!previousState && window.RebirthTutorial) {
                    setTimeout(() => window.RebirthTutorial.maybeStart(state), 600);
                }
            } catch (err) { /* silencioso */ }
        },

        async startMatch(options) {
            options = options || {};
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
                if (options.forceNew) {
                    try {
                        window.localStorage.removeItem("rebirth.lastMatchId");
                        window.localStorage.removeItem("rebirth.lastMatchFinished");
                    } catch (err) {}
                }
                if (!inCampaign) {
                    const resumed = await this.maybeResumeMatch(options);
                    if (resumed && resumed.state) {
                        RebirthStore.abandonmentSentForMatch = null;
                        RebirthStore.selectedInstanceId = null;
                        RebirthStore.reward = resumed.match_reward || null;
                        RebirthStore.campaignReward = resumed.campaign_reward || null;
                        RebirthStore.lastActionPopupSignature = null;
                        this.applyState(resumed.state);
                        return;
                    }
                }
                const endpoint = inCampaign ? RebirthConfig.endpoints.campaignStart : RebirthConfig.endpoints.start;
                const requestPayload = inCampaign
                    ? { node_id: campaignNode }
                    : { tutorial: RebirthStore.guidedFirstMatch };
                const payload = await RebirthApi.post(endpoint, requestPayload);
                RebirthStore.abandonmentSentForMatch = null;
                RebirthStore.selectedInstanceId = null;
                RebirthStore.reward = null;
                RebirthStore.campaignReward = null;
                RebirthStore.lastActionPopupSignature = null;
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

        async playSelectedCard(options) {
            options = options || {};
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
                if (isMonster && Number.isInteger(options.fieldSlot)) {
                    requestPayload.field_slot = options.fieldSlot;
                }
                if (!isMonster && options.targetInstanceId) {
                    requestPayload.target_instance_id = options.targetInstanceId;
                }
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
            // YGO: o primeiro ataque do turno anuncia a Fase de Batalha.
            if (RebirthGameFeel.lastBattleTurn !== RebirthStore.state.turn) {
                RebirthGameFeel.lastBattleTurn = RebirthStore.state.turn;
                RebirthGameFeel.showTurnBanner("player", "FASE DE BATALHA!");
            }
            const attacker = RebirthStore.fieldCard(RebirthStore.selectedAttackerId);
            if (attacker && !cardCanActNow(attacker)) {
                RebirthErrors.show(
                    attacker.just_summoned && !((attacker.keywords || []).includes("RUSH"))
                        ? "Monstro recém-invocado: ataca no próximo turno (Investida ignora isso)."
                        : "Esse monstro já atacou neste turno."
                );
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
                RebirthFloats.damageFromResult(
                    payload.state,
                    RebirthCombatMotion.attacker(attackerInstanceId),
                    RebirthCombatMotion.target(visualTargetId)
                );
                RebirthTargeting.deactivate();
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
            if (!cardCanActNow(attacker)) {
                RebirthErrors.show("Esse monstro ainda não pode atacar neste turno.");
                RebirthRenderer.buttons();
                return;
            }
            await this.attackTarget(null);
        },

        async mulligan() {
            if (!RebirthStore.state || !RebirthStore.state.mulligan_available) return;
            await this.request(async () => {
                const payload = await RebirthApi.post(RebirthConfig.endpoints.mulligan || "/api/rebirth/mulligan", {
                    match_id: RebirthStore.state.match_id
                });
                RebirthStore.selectedInstanceId = null;
                RebirthStore.selectedAttackerId = null;
                this.applyState(payload.state);
                RebirthGameFeel.showActionPopup(["Mão trocada"], "neutral");
            });
        },

        async nextTurn() {
            if (!RebirthStore.state) return;
            await this.request(async () => {
                RebirthGameFeel.previewBotTurn();
                const payload = await RebirthApi.post(RebirthConfig.endpoints.nextTurn, {
                    match_id: RebirthStore.state.match_id
                });
                RebirthStore.reward = null;
                RebirthStore.campaignReward = payload.campaign_reward || null;
                RebirthStore.selectedAttackerId = null;
                // O turno do bot vira cena: invocações, ataques e dano em
                // sequência sobre o DOM antigo; o estado final entra depois.
                // O estado do servidor SEMPRE entra, mesmo que a cena quebre
                // — board velho pós-turno era o bug nº1 da auditoria.
                try {
                    await BotTurnDirector.stage(payload.bot_phase_events);
                } catch (sceneError) {
                    BotTurnDirector.active = false;
                } finally {
                    RebirthGameFeel.suppressPopupsUntil = Date.now() + 900;
                    this.applyState(payload.state);
                    this.completeTutorialIfNeeded(payload.state);
                }
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
        await this.startMatch({ forceNew: true });
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
                    RebirthFlow.startMatch({ forceNew: true });
                });
            });

            const playButton = RebirthStore.elements["play-button"];
            if (playButton) {
                playButton.addEventListener("click", () => {
                    if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                    // Prioridade: a intenção EXPLÍCITA do jogador (carta ou
                    // atacante selecionado) vem antes de qualquer automação.
                    // A fusão sequestrava este clique quando havia par no
                    // campo — o jogador pedia uma magia e ganhava runa
                    // gigante (auditoria). Fusão tem botão próprio.
                    if (RebirthStore.selectedAttackerId) {
                        RebirthFlow.clashSelectedAttacker();
                        return;
                    }
                    if (RebirthStore.selectedInstanceId) {
                        RebirthFlow.playSelectedCard();
                        return;
                    }
                    if (RebirthStore.firstFieldFusion()) {
                        RebirthFlow.activateEvolutionOrFusion();
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

            const mulliganButton = RebirthStore.elements["mulligan-button"];
            if (mulliganButton) {
                mulliganButton.addEventListener("click", () => {
                    if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                    RebirthMulligan.reopen();
                });
            }
            RebirthMulligan.bind();
            RebirthGraveyard.bind();
            RebirthTargeting.bind();
            BotTurnDirector.bind();

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
                    RebirthGameFeel.selectionPulse();
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
                        const chosenSlot = Number(summonAction.getAttribute("data-summon-slot"));
                        RebirthFlow.playSelectedCard(Number.isInteger(chosenSlot) ? { fieldSlot: chosenSlot } : {});
                        return;
                    }
                    const button = event.target.closest("[data-attacker-instance]");
                    if (!button || !RebirthStore.state || RebirthStore.state.is_finished) return;
                    RebirthStore.selectedInstanceId = null;
                    RebirthStore.selectedAttackerId = button.getAttribute("data-attacker-instance");
                    if (window.RebirthAudioManager) window.RebirthAudioManager.uiClickConfirmed();
                    RebirthErrors.clear();
                    RebirthRenderer.render();
                    RebirthGameFeel.selectionPulse();
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
                    const selectedSpell = RebirthStore.handCard(RebirthStore.selectedInstanceId);
                    if (target && selectedSpell && isDamageSpell(selectedSpell) && !RebirthStore.selectedAttackerId) {
                        // Magia de dano mirando a unidade clicada.
                        RebirthFlow.playSelectedCard({ targetInstanceId: target.getAttribute("data-target-instance") });
                        return;
                    }
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

    // S1: Tutorial in-game. Passos guiados quando o usuário é autenticado
    // E ainda não completou (progression.tutorial_complete === false).
    // Ancorado em elementos do jogo via data-tutorial-spotlight (bounding box).
    const RebirthTutorial = {
        FALLBACK_STEPS: [
            {
                step: 1,
                title: "Bem-vindo à Arena",
                body: "Toque numa carta da sua mão para ver custo, ataque, guarda e habilidade antes de jogar.",
                target: ".rb-hand .rb-mini-card",
            },
            {
                step: 2,
                title: "Invoque com mana",
                body: "O botão principal joga a carta selecionada. Se faltar mana, encerre o turno para recarregar.",
                target: "#play-button",
            },
            {
                step: 3,
                title: "Ataque do campo",
                body: "Depois de invocar, selecione um monstro pronto no seu campo. O botão principal vira Atacar.",
                target: ".rb-field-card[data-attacker-instance], #play-button",
            },
            {
                step: 4,
                title: "Dano direto tem trava",
                body: "No primeiro turno, o jogo bloqueia dano direto para dar tempo do bot responder. Procure o texto no slot inimigo vazio.",
                target: ".rb-field-slot-empty.is-locked, #result-panel",
            },
            {
                step: 5,
                title: "Evolua duplicatas",
                body: "Quando duas cópias aparecem na mão, o painel de evolução cria a forma Rebirth antes da invocação.",
                target: "#evolution-panel, #evolve-button",
            },
            {
                step: 6,
                title: "Funda no campo",
                body: "Duas unidades iguais no campo podem virar uma fusão maior. Use isso antes de atacar quando precisar quebrar guarda.",
                target: "#evolution-panel, #evolve-button, .rb-field-card",
            },
            {
                step: 7,
                title: "Encerre o turno",
                body: "Quando não houver boa jogada, encerre o turno. O bot age, sua mana sobe e você compra novas cartas.",
                target: "#next-turn-button",
            },
            {
                step: 8,
                title: "Leia o recap",
                body: "Ao terminar, o painel mostra por que você venceu ou perdeu e sugere o próximo ajuste do deck.",
                target: "#reward-panel, #result-actions",
            },
        ],
        state: { active: false, currentIdx: 0, dom: null },

        init() {
            const overlay = document.getElementById("rebirth-tutorial");
            if (!overlay) return;
            this.state.dom = {
                overlay,
                spotlight: overlay.querySelector("[data-tutorial-spotlight]"),
                balloon: overlay.querySelector("[data-tutorial-balloon]"),
                stepLabel: overlay.querySelector("[data-tutorial-step-label]"),
                title: overlay.querySelector("[data-tutorial-title]"),
                body: overlay.querySelector("[data-tutorial-body]"),
                skipBtn: overlay.querySelector("[data-tutorial-skip]"),
                nextBtn: overlay.querySelector("[data-tutorial-next]"),
            };
            this.state.dom.nextBtn.addEventListener("click", () => this.advance());
            this.state.dom.skipBtn.addEventListener("click", () => this.finish(true));
            window.addEventListener("resize", () => {
                if (this.state.active) this.repositionSpotlight();
            }, { passive: true });
        },

        // chamado pelo flow do match após state arrivar
        maybeStart(state) {
            if (!state || !state.player) return;
            const progression = (window.REBIRTH_PLAYER_CONTEXT && window.REBIRTH_PLAYER_CONTEXT.progression) || {};
            const account = (window.REBIRTH_PLAYER_CONTEXT && window.REBIRTH_PLAYER_CONTEXT.account) || {};
            // Mostra tutorial pra: autenticado + progression.tutorial_complete=false +
            // clashes=0 (primeira partida real, não restart)
            const shouldShow = (
                account.authenticated &&
                progression && !progression.tutorial_complete &&
                Number(progression.clashes || 0) === 0
            );
            if (!shouldShow || this.state.active) return;
            this.start();
        },

        start() {
            if (!this.state.dom) return;
            this.state.active = true;
            this.state.currentIdx = 0;
            this.state.dom.overlay.hidden = false;
            this.renderStep();
        },

        renderStep() {
            const dom = this.state.dom;
            const step = this.steps()[this.state.currentIdx];
            if (!step) return this.finish(false);
            dom.stepLabel.textContent = `Passo ${step.step} de ${this.steps().length}`;
            dom.title.textContent = step.title;
            dom.body.textContent = step.body;
            dom.nextBtn.textContent = step.step >= this.steps().length ? "Concluir" : "Entendi";
            this.repositionSpotlight();
        },

        repositionSpotlight() {
            const dom = this.state.dom;
            const step = this.steps()[this.state.currentIdx];
            if (!dom || !step) return;
            const targets = step.target.split(",").map((s) => s.trim()).filter(Boolean);
            let el = null;
            for (const sel of targets) {
                el = document.querySelector(sel);
                if (el && el.getBoundingClientRect().width > 0) break;
            }
            if (!el) {
                dom.spotlight.style.display = "none";
                return;
            }
            const rect = el.getBoundingClientRect();
            const pad = 8;
            dom.spotlight.style.display = "block";
            dom.spotlight.style.top = `${Math.max(0, rect.top - pad)}px`;
            dom.spotlight.style.left = `${Math.max(0, rect.left - pad)}px`;
            dom.spotlight.style.width = `${rect.width + pad * 2}px`;
            dom.spotlight.style.height = `${rect.height + pad * 2}px`;
        },

        advance() {
            // Reporta passo ao backend (best-effort, não bloqueia UX)
            const step = this.steps()[this.state.currentIdx];
            if (step) {
                this.reportStep(step.step).catch(() => {});
            }
            this.state.currentIdx += 1;
            if (this.state.currentIdx >= this.steps().length) {
                this.finish(false);
                return;
            }
            this.renderStep();
        },

        async reportStep(step) {
            try {
                await fetch(RebirthConfig.endpoints.telemetry || "/api/rebirth/telemetry", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Rebirth-CSRF": window.REBIRTH_CSRF || "",
                    },
                    body: JSON.stringify({
                        event_type: "tutorial_step_viewed",
                        step,
                        match_id: RebirthStore.state && RebirthStore.state.match_id,
                        surface: "arena_tutorial"
                    }),
                });
            } catch (e) { /* silencioso */ }
        },

        steps() {
            const configured = window.REBIRTH_FIRST_SESSION && window.REBIRTH_FIRST_SESSION.arena_tutorial_steps;
            return Array.isArray(configured) && configured.length ? configured : this.FALLBACK_STEPS;
        },

        finish(skipped) {
            this.state.active = false;
            if (this.state.dom) {
                this.state.dom.overlay.hidden = true;
            }
            if (!skipped && RebirthConfig.endpoints.completeTutorial && RebirthCoach.account().authenticated) {
                RebirthApi.post(RebirthConfig.endpoints.completeTutorial, { step: 4 }).catch(() => {});
            }
        },
    };

    // F22-F: tilt 3D nos mini-cards da mão. Hover define --tilt-x/--tilt-y
    // em graus baseado na posição do mouse dentro do card. A regra CSS
    // .rb-hand .rb-mini-card já consome esses vars via rotateX/rotateY.
    const RebirthHandTilt = {
        init() {
            // Delegation via document para pegar cards re-renderizados também.
            document.addEventListener("mousemove", (event) => {
                const card = event.target && event.target.closest
                    ? event.target.closest(".rb-hand .rb-mini-card")
                    : null;
                if (!card) return;
                const rect = card.getBoundingClientRect();
                const dx = (event.clientX - (rect.left + rect.width / 2)) / (rect.width / 2);
                const dy = (event.clientY - (rect.top + rect.height / 2)) / (rect.height / 2);
                card.style.setProperty("--tilt-y", `${(dx * 8).toFixed(2)}deg`);
                card.style.setProperty("--tilt-x", `${(-dy * 6).toFixed(2)}deg`);
            }, { passive: true });
            document.addEventListener("mouseout", (event) => {
                const card = event.target && event.target.closest
                    ? event.target.closest(".rb-hand .rb-mini-card")
                    : null;
                if (!card) return;
                card.style.removeProperty("--tilt-x");
                card.style.removeProperty("--tilt-y");
            }, { passive: true });
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
        RebirthHandTilt.init();
        RebirthTutorial.init();
        RebirthFlow.startMatch();
    }

    // S1: expor pra integração com flow — chamado após state inicial chegar
    window.RebirthTutorial = RebirthTutorial;

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
