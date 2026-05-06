/* =========================================================
   Ambitionz Arena App V1
   Renders canonical `match_state` without DOM-reading overlays.
   Legacy engine remains loaded until replacement is stable.
   ========================================================= */

(function () {
    const isArenaRoute = () => window.location.pathname === "/training" || window.location.pathname === "/arena";

    if (!isArenaRoute()) return;

    const state = {
        socket: null,
        match: null,
        selectedIntent: null,
        selectedCardId: null,
        booted: false,
        seenEventKeys: new Set(),
        lastHp: { me: null, enemy: null },
        pendingPlayedCards: new Map(),
        lastPlayedCardId: null,
        endSoundPlayed: false,
    };

    const $ = (selector) => document.querySelector(selector);

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function createAppShell() {
        if ($(".az-arena-app")) return;

        document.body.classList.add("az-arena-app-enabled");

        const app = document.createElement("main");
        app.className = "az-arena-app";
        app.innerHTML = [
            '<header class="az-arena-app-top az-arena-app-shell">',
            '  <div class="az-arena-app-title">',
            '    <span class="az-arena-app-kicker" id="az-mode">Arena</span>',
            '    <h1 id="az-title">Ambitionz</h1>',
            '  </div>',
            '  <div class="az-arena-app-phase" id="az-phase">Connecting</div>',
            '  <a class="az-arena-app-back" href="/">Back</a>',
            '</header>',

            '<section class="az-arena-app-message az-arena-app-shell" id="az-message">Waiting for match state...</section>',

            '<section class="az-arena-app-score">',
            '  <article class="az-arena-player az-arena-app-shell">',
            '    <div class="az-arena-player-head"><span>You</span><strong id="az-me-name">Player</strong></div>',
            '    <div class="az-arena-stat-row">',
            '      <div class="az-arena-stat">HP <strong id="az-me-hp">3600</strong></div>',
            '      <div class="az-arena-stat">EN <strong id="az-me-energy">0/0</strong></div>',
            '      <div class="az-arena-stat">AMB <strong id="az-me-ambition">0</strong></div>',
            '      <div class="az-arena-stat">Intent <strong id="az-me-intent">None</strong></div>',
            '    </div>',
            '  </article>',
            '  <article class="az-arena-round az-arena-app-shell">',
            '    <div><strong id="az-round">1</strong><span>Round</span></div>',
            '  </article>',
            '  <article class="az-arena-player az-arena-app-shell">',
            '    <div class="az-arena-player-head"><span>Enemy</span><strong id="az-enemy-name">Opponent</strong></div>',
            '    <div class="az-arena-stat-row">',
            '      <div class="az-arena-stat">HP <strong id="az-enemy-hp">3600</strong></div>',
            '      <div class="az-arena-stat">EN <strong id="az-enemy-energy">0/0</strong></div>',
            '      <div class="az-arena-stat">AMB <strong id="az-enemy-ambition">0</strong></div>',
            '      <div class="az-arena-stat">Hand <strong id="az-enemy-hand">0</strong></div>',
            '    </div>',
            '  </article>',
            '</section>',

            '<section class="az-arena-board az-arena-app-shell">',
            '  <div class="az-arena-field" id="az-enemy-field"></div>',
            '  <div class="az-arena-divider">Battlefield</div>',
            '  <div class="az-arena-field" id="az-me-field"></div>',
            '</section>',

            '<div class="az-arena-perspective-glow" id="az-perspective-glow"></div>',
            '<div class="az-event-layer" id="az-event-layer"></div>',
            '<section class="az-arena-hand az-arena-app-shell">',
            '  <div class="az-arena-hand-head">',
            '    <h2>Your Hand</h2>',
            '    <span id="az-hand-count">0 cards</span>',
            '  </div>',
            '  <div class="az-arena-hand-row" id="az-hand"></div>',
            '</section>',

            '<nav class="az-arena-actions">',
            '  <button type="button" data-action="Strike">Strike</button>',
            '  <button type="button" data-action="Guard">Guard</button>',
            '  <button type="button" data-action="Focus">Focus</button>',
            '  <button type="button" class="primary" data-action="Ready">Ready</button>',
            '</nav>'
        ].join("");

        document.body.prepend(app);
    }

    function setText(selector, value) {
        const el = $(selector);
        if (el) el.textContent = String(value ?? "");
    }

    function renderCard(card, options = {}) {
        if (!card) {
            return '<div class="az-arena-slot az-arena-empty">' + escapeHtml(options.emptyLabel || "Empty") + '</div>';
        }

        const playable = options.playableCardIds && options.playableCardIds.includes(card.id);
        const playableClass = options.inHand
            ? playable ? "is-playable" : "is-unplayable"
            : "";

        const type = card.type || "Monster";
        const rarity = card.rarity || "Common";
        const element = card.element || "Neutral";
        const isMonster = type === "Monster";
        const combatLabel = card.combat_label || (isMonster ? "ATK" : "VALUE");
        const attack = Number(card.attack ?? card.power ?? card.value ?? 0);
        const defense = Number(card.defense ?? card.value ?? 0);
        const mainStat = isMonster ? attack : Number(card.value ?? card.power ?? 0);
        const subStat = isMonster ? defense : Number(card.cost ?? 0);

        const typeCss = "type-" + String(type).toLowerCase().replace(/\s+/g, "-");
        const rarityCss = "rarity-" + String(rarity).toLowerCase().replace(/\s+/g, "-");
        const elementCss = elementClass(element);

        return [
            '<button type="button" class="az-arena-card ' + playableClass + ' ' + typeCss + ' ' + rarityCss + ' ' + elementCss + '" data-card-id="' + escapeHtml(card.id) + '" data-element="' + escapeHtml(element) + '" ' + (options.inHand ? "" : "disabled") + '>',
            '  <div class="az-card-frame-glow"></div>',
            '  <div class="az-card-rarity-line"></div>',
            '  <div class="az-arena-card-cost">' + escapeHtml(card.cost ?? 0) + '</div>',
            '  <div class="az-arena-card-art">',
            '    <div class="az-card-art-orb"></div>',
            '    <div class="az-card-art-mark">' + escapeHtml(String(element).slice(0, 1).toUpperCase()) + '</div>',
            '  </div>',
            '  <div class="az-arena-card-body">',
            '    <strong title="' + escapeHtml(card.name || "Card") + '">' + escapeHtml(card.name || "Card") + '</strong>',
            '    <span>' + escapeHtml(type) + ' · ' + escapeHtml(element) + '</span>',
            '  </div>',
            '  <div class="az-arena-card-tags">',
            '    <small>' + escapeHtml(card.sigil || "None") + '</small>',
            '    <small>' + escapeHtml(rarity) + '</small>',
            '  </div>',
            '  <div class="az-arena-card-stats">',
            '    <div><b>' + escapeHtml(mainStat) + '</b><small>' + escapeHtml(combatLabel) + '</small></div>',
            '    <div><b>' + escapeHtml(subStat) + '</b><small>' + (isMonster ? "DEF" : "COST") + '</small></div>',
            '  </div>',
            '</button>'
        ].join("");
    }

    function renderField(selector, field, enemy = false) {
        const el = $(selector);
        if (!el) return;

        field = field || {};

        el.innerHTML = [
            renderCard(field.monster, { emptyLabel: enemy ? "Enemy Monster" : "Monster Slot" }),
            renderCard(field.spell, { emptyLabel: enemy ? "Enemy Spell" : "Spell Slot" }),
            renderCard(field.trap, { emptyLabel: enemy ? "Enemy Trap" : "Trap Slot" }),
        ].join("");
    }

    function renderHand(match) {
        const handEl = $("#az-hand");
        const countEl = $("#az-hand-count");

        if (!handEl) return;

        const hand = (match.me && match.me.hand) || [];
        const playable = (match.legal_actions && match.legal_actions.playable_card_ids) || [];

        if (countEl) {
            countEl.textContent = hand.length + " cards";
        }

        if (!hand.length) {
            handEl.innerHTML = '<div class="az-arena-slot az-arena-empty">No cards in hand. Start the match or wait for sync.</div>';
            return;
        }

        handEl.innerHTML = hand.map((card) => renderCard(card, {
            inHand: true,
            playableCardIds: playable,
        })).join("");
    }


    function eventKey(event, index) {
        return [
            event.type || "event",
            event.player || "",
            event.card_id || event.card_name || "",
            event.p1_damage ?? "",
            event.p2_damage ?? "",
            event.p1_hp ?? "",
            event.p2_hp ?? "",
            index,
        ].join(":");
    }

    function showRoundBanner(title, copy) {
        let layer = document.querySelector("#az-event-layer");

        if (!layer) return;

        const banner = document.createElement("div");
        banner.className = "az-round-event-banner";
        banner.innerHTML = '<strong>' + escapeHtml(title) + '</strong><span>' + escapeHtml(copy || "") + '</span>';

        layer.appendChild(banner);

        setTimeout(() => {
            banner.remove();
        }, 1800);
    }

    function floatingDamage(target, amount) {
        if (!amount || amount <= 0) return;

        let layer = document.querySelector("#az-event-layer");

        if (!layer) return;

        const el = document.createElement("div");
        el.className = "az-floating-damage " + target;
        el.textContent = "-" + amount;

        layer.appendChild(el);

        setTimeout(() => {
            el.remove();
        }, 1200);
    }

    function pulseSelector(selector, className) {
        const el = document.querySelector(selector);

        if (!el) return;

        el.classList.remove(className);
        void el.offsetWidth;
        el.classList.add(className);

        setTimeout(() => {
            el.classList.remove(className);
        }, 900);
    }


    function showRewardModal(match) {
        if (!match || match.phase !== "finished") return;

        const reward = match.reward_preview || {};
        if (!reward.available) return;

        let modal = document.querySelector("#az-reward-modal");

        if (!modal) {
            modal = document.createElement("div");
            modal.id = "az-reward-modal";
            modal.className = "az-reward-modal";
            modal.innerHTML = [
                '<article class="az-reward-card">',
                '  <span class="az-arena-app-kicker">Match Rewards</span>',
                '  <h2 id="az-reward-title">Victory</h2>',
                '  <p id="az-reward-copy">Your progress moved forward.</p>',
                '  <div class="az-reward-grid">',
                '    <div><strong id="az-reward-xp">0</strong><span>XP</span></div>',
                '    <div><strong id="az-reward-coins">0</strong><span>Coins</span></div>',
                '    <div><strong id="az-reward-round">1</strong><span>Round</span></div>',
                '  </div>',
                '  <div class="az-reward-progress">',
                '    <div class="az-reward-progress-label"><span>Next Booster</span><strong id="az-reward-booster-progress">+0%</strong></div>',
                '    <div class="az-reward-progress-bar"><i id="az-reward-booster-fill"></i></div>',
                '  </div>',
                '  <div class="az-reward-actions">',
                '    <button type="button" id="az-reward-rematch">Train Again</button>',
                '    <a href="/deck-builder">Improve Deck</a>',
                '    <a href="/shop">Open Booster</a>',
                '  </div>',
                '</article>'
            ].join("");

            document.body.appendChild(modal);

            const rematch = document.querySelector("#az-reward-rematch");

            if (rematch) {
                rematch.addEventListener("click", () => {
                    modal.classList.remove("is-visible");
                    state.endSoundPlayed = false;
                    state.seenEventKeys = new Set();
                    emit("start_training", {});
                    setTimeout(() => emit("request_match_state", {}), 250);
                });
            }
        }

        const title = document.querySelector("#az-reward-title");
        const copy = document.querySelector("#az-reward-copy");
        const xp = document.querySelector("#az-reward-xp");
        const coins = document.querySelector("#az-reward-coins");
        const round = document.querySelector("#az-reward-round");
        const boosterProgress = document.querySelector("#az-reward-booster-progress");
        const boosterFill = document.querySelector("#az-reward-booster-fill");

        if (title) title.textContent = reward.title || "Match Complete";
        if (copy) {
            if (reward.result === "win") copy.textContent = "Clean win. Your account gained stronger progress.";
            else if (reward.result === "draw") copy.textContent = "Close match. You still earned useful progress.";
            else copy.textContent = "Defeat still teaches. Claim progress and improve the deck.";
        }

        if (xp) xp.textContent = "+" + (reward.xp || 0);
        if (coins) coins.textContent = "+" + (reward.coins || 0);
        if (round) round.textContent = match.round || 1;

        const boosterPct = Math.max(8, Math.min(100, Math.round((Number(reward.coins || 0) / 300) * 100)));

        if (boosterProgress) boosterProgress.textContent = "+" + boosterPct + "%";
        if (boosterFill) boosterFill.style.width = boosterPct + "%";

        modal.classList.add("is-visible");

        if (!reward.persisted && !reward.already_claimed) {
            emit("claim_match_rewards_v1", {});
        }
    }

    function showEndOverlay(match) {
        if (!match || match.phase !== "finished") return;

        let overlay = document.querySelector("#az-match-end-overlay");

        if (!overlay) {
            overlay = document.createElement("div");
            overlay.id = "az-match-end-overlay";
            overlay.className = "az-match-end-overlay";
            overlay.innerHTML = [
                '<article>',
                '  <span class="az-arena-app-kicker">Match Result</span>',
                '  <h2 id="az-end-title">Victory</h2>',
                '  <p id="az-end-copy">The battle is complete.</p>',
                '  <div class="az-end-actions">',
                '    <button type="button" id="az-end-continue">Continue</button>',
                '    <button type="button" id="az-end-rematch">Train Again</button>',
                '  </div>',
                '</article>'
            ].join("");

            document.body.appendChild(overlay);

            const close = document.querySelector("#az-end-continue");
            const rematch = document.querySelector("#az-end-rematch");

            if (close) {
                close.addEventListener("click", () => overlay.classList.remove("is-visible"));
            }

            if (rematch) {
                rematch.addEventListener("click", () => {
                    overlay.classList.remove("is-visible");
                    emit("start_training", {});
                    setTimeout(() => emit("request_match_state", {}), 250);
                });
            }
        }

        const title = document.querySelector("#az-end-title");
        const copy = document.querySelector("#az-end-copy");

        const winner = match.winner;

        if (winner === "p1" || winner === match.viewer_key) {
            title.textContent = "Victory";
            copy.textContent = "You won the training duel.";
            if (!state.endSoundPlayed) {
                playSound("victory");
                state.endSoundPlayed = true;
            }
        } else if (winner === "draw") {
            title.textContent = "Draw";
            copy.textContent = "The duel ended in a draw.";
            if (!state.endSoundPlayed) {
                playSound("roundResolve");
                state.endSoundPlayed = true;
            }
        } else {
            title.textContent = "Defeat";
            copy.textContent = "You lost the duel. Adjust your strategy and try again.";
            if (!state.endSoundPlayed) {
                playSound("defeat");
                state.endSoundPlayed = true;
            }
        }

        overlay.classList.add("is-visible");
    }



    function playSound(name, payload) {
        try {
            if (window.AmbitionzSound && window.AmbitionzSound.play) {
                window.AmbitionzSound.play(name, payload || {});
            }
        } catch (err) {}
    }

    function elementClass(element) {
        return "element-" + String(element || "neutral").toLowerCase().replace(/\s+/g, "-");
    }


    function visualHaptic(kind) {
        const app = document.querySelector(".az-arena-app");

        if (!app) return;

        app.classList.remove("az-haptic-light", "az-haptic-medium", "az-haptic-heavy");
        void app.offsetWidth;

        const className = kind === "heavy"
            ? "az-haptic-heavy"
            : kind === "medium"
            ? "az-haptic-medium"
            : "az-haptic-light";

        app.classList.add(className);

        setTimeout(() => {
            app.classList.remove(className);
        }, 420);

        // Mobile haptics only, no sound.
        try {
            if (navigator.vibrate) {
                if (kind === "heavy") navigator.vibrate([20, 30, 20]);
                else if (kind === "medium") navigator.vibrate(18);
                else navigator.vibrate(10);
            }
        } catch (err) {}
    }


    function createElementBurst(element, x, y) {
        const layer = document.querySelector("#az-event-layer");

        if (!layer) return;

        const burst = document.createElement("div");
        burst.className = "az-element-burst " + elementClass(element);
        burst.style.left = x + "px";
        burst.style.top = y + "px";

        for (let i = 0; i < 10; i += 1) {
            const particle = document.createElement("span");
            particle.style.setProperty("--angle", (i * 36) + "deg");
            particle.style.setProperty("--dist", (28 + Math.random() * 34) + "px");
            burst.appendChild(particle);
        }

        layer.appendChild(burst);

        setTimeout(() => {
            burst.remove();
        }, 900);
    }


    function findCardElementById(cardId) {
        if (!cardId) return null;

        return document.querySelector('#az-hand .az-arena-card[data-card-id="' + CSS.escape(String(cardId)) + '"]');
    }

    function findFieldTargetForZone(zone) {
        const normalized = String(zone || "monster").toLowerCase();

        if (normalized === "spell") {
            return document.querySelector("#az-me-field .az-arena-slot:nth-child(2), #az-me-field .az-arena-card:nth-child(2)");
        }

        if (normalized === "trap") {
            return document.querySelector("#az-me-field .az-arena-slot:nth-child(3), #az-me-field .az-arena-card:nth-child(3)");
        }

        return document.querySelector("#az-me-field .az-arena-slot:nth-child(1), #az-me-field .az-arena-card:nth-child(1)");
    }

    function flyCardToField(cardId, zone, label, element) {
        const source = findCardElementById(cardId);
        const target = findFieldTargetForZone(zone);
        const layer = document.querySelector("#az-event-layer");

        if (!source || !target || !layer) {
            pulseSelector("#az-me-field", "az-field-impact");
            visualHaptic("medium");
            return;
        }

        const sourceRect = source.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();

        const clone = source.cloneNode(true);
        clone.classList.add("az-flying-card");
        clone.style.left = sourceRect.left + "px";
        clone.style.top = sourceRect.top + "px";
        clone.style.width = sourceRect.width + "px";
        clone.style.height = sourceRect.height + "px";

        layer.appendChild(clone);

        const dx = targetRect.left + targetRect.width / 2 - (sourceRect.left + sourceRect.width / 2);
        const dy = targetRect.top + targetRect.height / 2 - (sourceRect.top + sourceRect.height / 2);

        clone.style.setProperty("--fly-x", dx + "px");
        clone.style.setProperty("--fly-y", dy + "px");

        requestAnimationFrame(() => {
            clone.classList.add("is-flying");
        });

        playSound("cardFly", { element });

        setTimeout(() => {
            clone.remove();
            pulseSelector("#az-me-field", "az-field-impact");
            showRoundBanner("Card Played", label || "Card entered the field.");
            createElementBurst(element || "Global", targetRect.left + targetRect.width / 2, targetRect.top + targetRect.height / 2);
            playSound("cardImpact", { element });
            visualHaptic("medium");
        }, 620);
    }

    function markPendingCard(cardId) {
        if (!cardId) return;

        const cardEl = findCardElementById(cardId);

        if (cardEl) {
            cardEl.classList.add("az-card-pending-play");
        }

        state.lastPlayedCardId = cardId;
        state.pendingPlayedCards.set(String(cardId), {
            createdAt: Date.now(),
        });

        setTimeout(() => {
            const el = findCardElementById(cardId);
            if (el) el.classList.remove("az-card-pending-play");
        }, 900);
    }

    function buttonImpact(action) {
        const btn = document.querySelector('.az-arena-actions button[data-action="' + action + '"]');

        if (!btn) return;

        btn.classList.remove("az-action-impact");
        void btn.offsetWidth;
        btn.classList.add("az-action-impact");

        setTimeout(() => {
            btn.classList.remove("az-action-impact");
        }, 420);
    }


    function processBattleEvents(match) {
        const events = Array.isArray(match.events) ? match.events : [];

        events.forEach((event, index) => {
            const key = eventKey(event, index);

            if (state.seenEventKeys.has(key)) return;

            state.seenEventKeys.add(key);

            if (event.type === "play_card") {
                flyCardToField(event.card_id, event.zone, event.card_name || "A card entered the field.", event.element || "Global");
                pulseSelector("#az-me-field", "az-field-pulse");
            }

            if (event.type === "bot_play_card") {
                showRoundBanner("Enemy Played", event.card_name || "Enemy card entered the field.");
                pulseSelector("#az-enemy-field", "az-field-impact");
                playSound("cardImpact", { element: event.element || "Global" });
                visualHaptic("light");
            }

            if (event.type === "set_intent") {
                showRoundBanner("Intent", (event.intent || "Intent") + " selected.");
                buttonImpact(event.intent || "");
                playSound("intent", { element: event.intent || "Global" });
                visualHaptic("light");
            }

            if (event.type === "declare_ready") {
                showRoundBanner("Ready", "Round committed.");
                buttonImpact("Ready");
                playSound("ready");
                visualHaptic("medium");
            }

            if (event.type === "resolve_round") {
                showRoundBanner("Round Resolved", "Damage exchanged.");
                floatingDamage("enemy", Number(event.p1_damage || 0));
                floatingDamage("me", Number(event.p2_damage || 0));
                pulseSelector("#az-enemy-hp", "az-hp-hit");
                pulseSelector("#az-me-hp", "az-hp-hit");
                pulseSelector(".az-arena-board", "az-board-impact");
                playSound("roundResolve");
                if (Number(event.p1_damage || 0) > 0 || Number(event.p2_damage || 0) > 0) {
                    playSound("damage");
                }
                visualHaptic("heavy");
            }
        });

        if (state.seenEventKeys.size > 80) {
            state.seenEventKeys = new Set(Array.from(state.seenEventKeys).slice(-40));
        }
    }

    function processHpChanges(match) {
        const meHp = Number(match?.me?.hp ?? 0);
        const enemyHp = Number(match?.enemy?.hp ?? 0);

        if (state.lastHp.me !== null && meHp < state.lastHp.me) {
            floatingDamage("me", state.lastHp.me - meHp);
            pulseSelector("#az-me-hp", "az-hp-hit");
        }

        if (state.lastHp.enemy !== null && enemyHp < state.lastHp.enemy) {
            floatingDamage("enemy", state.lastHp.enemy - enemyHp);
            pulseSelector("#az-enemy-hp", "az-hp-hit");
        }

        state.lastHp.me = meHp;
        state.lastHp.enemy = enemyHp;
    }


    function render(match) {
        if (!match || match.schema !== "ambitionz_match_v1") return;

        state.match = match;

        const me = match.me || {};
        const enemy = match.enemy || {};

        setText("#az-mode", match.mode || "Arena");
        setText("#az-title", window.location.pathname === "/training" ? "Training" : "Arena");
        setText("#az-phase", match.phase || "Battle");
        const azPhaseEl = document.querySelector("#az-phase");
        if (azPhaseEl) {
            azPhaseEl.className = "az-arena-app-phase " + String(match.phase || "battle").toLowerCase();
        }
        setText("#az-message", match.message || "Choose your move.");
        setText("#az-round", match.round || 1);

        setText("#az-me-name", me.name || "Player");
        setText("#az-me-hp", me.hp ?? 3600);
        setText("#az-me-energy", (me.energy ?? 0) + "/" + (me.max_energy ?? 0));
        setText("#az-me-ambition", me.ambition ?? 0);
        setText("#az-me-intent", me.intent || state.selectedIntent || "None");

        setText("#az-enemy-name", enemy.name || "Opponent");
        setText("#az-enemy-hp", enemy.hp ?? 3600);
        setText("#az-enemy-energy", (enemy.energy ?? 0) + "/" + (enemy.max_energy ?? 0));
        setText("#az-enemy-ambition", enemy.ambition ?? 0);
        setText("#az-enemy-hand", enemy.hand_count ?? 0);

        renderField("#az-enemy-field", enemy.field || {}, true);
        renderField("#az-me-field", me.field || {}, false);
        renderHand(match);

        processHpChanges(match);
        processBattleEvents(match);
        showEndOverlay(match);
        showRewardModal(match);

        updateActions();
    }

    function updateActions() {
        document.querySelectorAll(".az-arena-actions button").forEach((btn) => {
            btn.classList.remove("active");

            if (btn.dataset.action === state.selectedIntent) {
                btn.classList.add("active");
            }
        });
    }

    function emit(event, payload) {
        const socket = state.socket || window.socket;

        if (!socket || !socket.emit) {
            console.warn("[ArenaApp] socket unavailable", event, payload);
            setText("#az-message", "Socket not connected yet.");
            return;
        }

        socket.emit(event, payload || {});
    }

    function bindActions() {
        document.addEventListener("click", (event) => {
            const actionBtn = event.target.closest(".az-arena-actions button");

            if (actionBtn) {
                const action = actionBtn.dataset.action;

                if (["Strike", "Guard", "Focus"].includes(action)) {
                    state.selectedIntent = action;
                    updateActions();
                    buttonImpact(action);
                    playSound("intent", { element: action });
                    visualHaptic("light");
                    emit("set_intent", { intent: action });
                    return;
                }

                if (action === "Ready") {
                    buttonImpact("Ready");
                    playSound("ready");
                    visualHaptic("medium");
                    emit("declare_ready", {});
                    return;
                }
            }

            const cardBtn = event.target.closest("#az-hand .az-arena-card");

            if (cardBtn) {
                const cardId = cardBtn.dataset.cardId;

                if (cardBtn.classList.contains("is-unplayable")) {
                    setText("#az-message", "Not enough energy for this card.");
                    return;
                }

                state.selectedCardId = cardId;
                markPendingCard(cardId);
                playSound("cardSelect");
                visualHaptic("light");
                emit("play_card", { card_id: cardId });
            }
        });
    }

    function connectSocket() {
        const start = () => {
            const socket = window.socket;

            if (!socket || !socket.on || !socket.emit) {
                return false;
            }

            state.socket = socket;

            socket.on("match_state", (payload) => {
                console.debug("[ArenaApp] match_state", payload);
                render(payload);
            });

            socket.on("action_error", (payload) => {
                console.warn("[ArenaApp] action_error", payload);
                setText("#az-message", payload && payload.message ? payload.message : "Action failed.");
            });

            socket.on("reward_result", (payload) => {
                console.debug("[ArenaApp] reward_result", payload);
                state.lastRewardResult = payload;
                if (payload && payload.available) {
                    setText("#az-message", payload.already_claimed ? "Rewards already claimed." : "Rewards saved to your account.");
                }
            });

            if (window.location.pathname === "/training") {
                socket.emit("start_training", {});
            }

            socket.emit("request_match_state", {});

            return true;
        };

        let tries = 0;
        const timer = setInterval(() => {
            tries += 1;

            if (start() || tries > 24) {
                clearInterval(timer);
            }
        }, 250);
    }


    function recalibrateArenaViewport() {
        const app = document.querySelector(".az-arena-app");
        if (!app) return;

        const vh = window.innerHeight || document.documentElement.clientHeight || 720;
        app.style.setProperty("--az-vh", vh + "px");

        if (vh < 680) {
            app.classList.add("az-compact-height");
        } else {
            app.classList.remove("az-compact-height");
        }
    }


    function boot() {
        if (state.booted) return;

        state.booted = true;

        createAppShell();
        recalibrateArenaViewport();
        window.addEventListener("resize", recalibrateArenaViewport);
        bindActions();
        connectSocket();

        setText("#az-message", "Connecting to match state...");
    }

    document.addEventListener("DOMContentLoaded", boot);

    window.AmbitionzArenaApp = {
        render,
        state,
        requestState: () => emit("request_match_state", {}),
    };
})();
