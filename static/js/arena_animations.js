/* =========================================================
   Ambitionz Arena Animations
   Animation bridge for Arena V7.
   Does not change battle rules.
   ========================================================= */

(function () {
    function isBattlePage() {
        return window.location.pathname === "/training" || window.location.pathname === "/arena";
    }

    function qs(selector) {
        return document.querySelector(selector);
    }

    function qsa(selector) {
        return Array.prototype.slice.call(document.querySelectorAll(selector));
    }

    var previous = {
        myHp: null,
        enemyHp: null,
        myEnergy: null,
        enemyEnergy: null,
        round: null,
        state: null,
        handText: ""
    };

    function createRoundBanner() {
        if (qs(".az-round-banner")) return;

        var banner = document.createElement("div");
        banner.className = "az-round-banner";
        banner.innerHTML = "<strong>Round Ready</strong><span>Choose your move.</span>";
        document.body.appendChild(banner);
    }

    function showRoundBanner(title, copy) {
        var banner = qs(".az-round-banner");
        if (!banner) return;

        banner.innerHTML = "<strong>" + title + "</strong><span>" + copy + "</span>";
        banner.classList.remove("is-visible");
        void banner.offsetWidth;
        banner.classList.add("is-visible");
    }

    function createEndOverlay() {
        if (qs(".az-end-overlay")) return;

        var overlay = document.createElement("div");
        overlay.className = "az-end-overlay";
        overlay.innerHTML = [
            '<article class="az-end-card">',
            '  <small>Match Result</small>',
            '  <h2 id="az-end-title">Victory</h2>',
            '  <p id="az-end-copy">Your ambition grows stronger.</p>',
            '  <div class="az-end-rewards">',
            '    <div class="az-end-reward"><div><strong id="az-end-xp">+0</strong><span>XP</span></div></div>',
            '    <div class="az-end-reward"><div><strong id="az-end-coins">+0</strong><span>Coins</span></div></div>',
            '  </div>',
            '  <div class="az-end-actions">',
            '    <button type="button" class="primary" id="az-end-close">Continue</button>',
            '    <a href="/daily">Daily Quests</a>',
            '    <a href="/deck-builder">Deck</a>',
            '  </div>',
            '</article>'
        ].join("");

        document.body.appendChild(overlay);

        var close = qs("#az-end-close");
        if (close) {
            close.addEventListener("click", function () {
                overlay.classList.remove("is-visible");
            });
        }
    }

    function showEndOverlay(result, xp, coins) {
        createEndOverlay();

        var overlay = qs(".az-end-overlay");
        var title = qs("#az-end-title");
        var copy = qs("#az-end-copy");
        var xpEl = qs("#az-end-xp");
        var coinsEl = qs("#az-end-coins");

        if (!overlay) return;

        var cleanResult = String(result || "Victory").toLowerCase();

        if (cleanResult.indexOf("lose") !== -1 || cleanResult.indexOf("defeat") !== -1) {
            title.textContent = "Defeat";
            copy.textContent = "You still earned progress. Improve your deck and run it back.";
        } else if (cleanResult.indexOf("draw") !== -1) {
            title.textContent = "Draw";
            copy.textContent = "A close duel. Claim progress and try again.";
        } else {
            title.textContent = "Victory";
            copy.textContent = "Good duel. Claim your momentum and keep climbing.";
        }

        if (xpEl) xpEl.textContent = "+" + (xp || 0);
        if (coinsEl) coinsEl.textContent = "+" + (coins || 0);

        overlay.classList.add("is-visible");
    }

    function floatingText(text, kind) {
        var el = document.createElement("div");
        el.className = "az-floating-text " + (kind || "");
        el.textContent = text;
        document.body.appendChild(el);

        setTimeout(function () {
            el.remove();
        }, 980);
    }

    function flash(el, className) {
        if (!el) return;
        el.classList.remove(className);
        void el.offsetWidth;
        el.classList.add(className);

        setTimeout(function () {
            el.classList.remove(className);
        }, 780);
    }

    function normalizeNumber(text) {
        var n = parseInt(String(text || "").replace(/\D/g, ""), 10);
        return Number.isFinite(n) ? n : null;
    }

    function watchStats() {
        var myHpEl = qs("#az-v7-my-hp");
        var enemyHpEl = qs("#az-v7-enemy-hp");
        var myEnergyEl = qs("#az-v7-my-energy");
        var enemyEnergyEl = qs("#az-v7-enemy-energy");
        var roundEl = qs("#az-v7-round");

        var myHp = normalizeNumber(myHpEl ? myHpEl.textContent : "");
        var enemyHp = normalizeNumber(enemyHpEl ? enemyHpEl.textContent : "");
        var myEnergy = myEnergyEl ? myEnergyEl.textContent.trim() : "";
        var enemyEnergy = enemyEnergyEl ? enemyEnergyEl.textContent.trim() : "";
        var round = roundEl ? roundEl.textContent.trim() : "";

        if (previous.myHp !== null && myHp !== null && myHp < previous.myHp) {
            flash(myHpEl, "az-hp-damage");
            flash(myHpEl, "az-hit-shake");
            floatingText("-" + (previous.myHp - myHp), "damage");
        }

        if (previous.enemyHp !== null && enemyHp !== null && enemyHp < previous.enemyHp) {
            flash(enemyHpEl, "az-hp-damage");
            flash(enemyHpEl, "az-hit-shake");
            floatingText("-" + (previous.enemyHp - enemyHp), "damage");
        }

        if (previous.myEnergy !== null && previous.myEnergy !== myEnergy) {
            flash(myEnergyEl, "az-energy-pulse");
        }

        if (previous.enemyEnergy !== null && previous.enemyEnergy !== enemyEnergy) {
            flash(enemyEnergyEl, "az-energy-pulse");
        }

        if (previous.round !== null && previous.round !== round) {
            showRoundBanner(round || "New Round", "Plan your next move.");
        }

        previous.myHp = myHp;
        previous.enemyHp = enemyHp;
        previous.myEnergy = myEnergy;
        previous.enemyEnergy = enemyEnergy;
        previous.round = round;
    }

    function bindIntentGlow() {
        document.addEventListener("click", function (event) {
            var btn = event.target.closest("[data-v7-action]");
            if (!btn) return;

            var action = btn.getAttribute("data-v7-action");
            if (!["strike", "guard", "focus"].includes(action)) return;

            qsa('[data-v7-action="strike"], [data-v7-action="guard"], [data-v7-action="focus"]').forEach(function (el) {
                el.classList.remove("az-intent-glow");
            });

            btn.classList.add("az-intent-glow");

            var label = action.charAt(0).toUpperCase() + action.slice(1);
            showRoundBanner(label + " selected", "Press Ready when your move is set.");
        });
    }

    function bindReadyFeedback() {
        document.addEventListener("click", function (event) {
            var btn = event.target.closest('[data-v7-action="ready"]');
            if (!btn) return;

            showRoundBanner("Ready", "Round committed.");
            floatingText("READY", "reward");
        });
    }

    function watchHandChanges() {
        var hand = qs("#az-v7-hand");
        if (!hand) return;

        var text = hand.textContent.trim();

        if (previous.handText && previous.handText !== text) {
            qsa(".az-v7-hand-card").forEach(function (card, index) {
                card.classList.remove("az-card-draw");
                card.style.animationDelay = (index * 45) + "ms";
                void card.offsetWidth;
                card.classList.add("az-card-draw");
            });
        }

        previous.handText = text;
    }

    function hookSocketIfAvailable() {
        // game.js may use a global socket variable depending on implementation.
        // This hook is defensive and harmless if socket is unavailable.
        setTimeout(function () {
            try {
                if (!window.socket || !window.socket.on) return;

                window.socket.on("post_match_summary", function (payload) {
                    var result = payload && (payload.result || payload.outcome || payload.status);
                    var rewards = payload && (payload.rewards || {});
                    showEndOverlay(result || "Victory", rewards.xp || payload.xp || 0, rewards.coins || payload.coins || 0);
                });

                window.socket.on("battle_log", function (payload) {
                    var text = "";

                    if (typeof payload === "string") {
                        text = payload;
                    } else if (payload && payload.message) {
                        text = payload.message;
                    } else if (payload && payload.line) {
                        text = payload.line;
                    }

                    var lower = text.toLowerCase();

                    if (lower.indexOf("victory") !== -1 || lower.indexOf("win") !== -1) {
                        showEndOverlay("Victory", 0, 0);
                    }

                    if (lower.indexOf("defeat") !== -1 || lower.indexOf("lose") !== -1) {
                        showEndOverlay("Defeat", 0, 0);
                    }
                });
            } catch (err) {}
        }, 1200);
    }

    function boot() {
        if (!isBattlePage()) return;

        createRoundBanner();
        createEndOverlay();
        bindIntentGlow();
        bindReadyFeedback();
        hookSocketIfAvailable();

        setInterval(watchStats, 650);
        setInterval(watchHandChanges, 750);
    }

    document.addEventListener("DOMContentLoaded", boot);

    window.AmbitionzArenaFeedback = {
        showEndOverlay: showEndOverlay,
        showRoundBanner: showRoundBanner,
        floatingText: floatingText
    };
})();
