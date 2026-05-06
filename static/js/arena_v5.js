/* =========================================================
   Ambitionz Arena V5 Clean Overlay
   Old arena remains hidden as engine. This is the visible UX.
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

    function text(selector, fallback) {
        var el = qs(selector);
        return el ? (el.textContent || "").trim() : fallback;
    }

    function findButton(terms) {
        terms = Array.isArray(terms) ? terms : [terms];

        return qsa("button, a.btn, [role='button']").find(function (el) {
            if (el.closest(".az-v5-root")) return false;

            var t = (el.textContent || "").trim().toLowerCase();

            return terms.some(function (term) {
                return t.indexOf(term.toLowerCase()) !== -1;
            });
        });
    }

    function clickOld(terms) {
        var btn = findButton(terms);
        if (btn) {
            btn.click();
            return true;
        }
        return false;
    }

    function createRoot() {
        if (qs(".az-v5-root")) return;

        document.body.classList.add("az-v5-active");

        var mode = window.location.pathname === "/training" ? "Training" : "Arena";

        var root = document.createElement("main");
        root.className = "az-v5-root";

        root.innerHTML = [
            '<header class="az-v5-top">',
            '  <div class="az-v5-title">',
            '    <span class="az-v5-kicker">' + (mode === "Training" ? "Training Mode" : "Competitive Mode") + '</span>',
            '    <h1>' + mode + '</h1>',
            '  </div>',
            '  <div class="az-v5-online">Online</div>',
            '  <a class="az-v5-back" href="/">Back</a>',
            '</header>',

            '<section class="az-v5-hero">',
            '  <div>',
            '    <span class="az-v5-kicker">Battle Flow</span>',
            '    <h2 id="az-v5-title">Start the duel</h2>',
            '    <p id="az-v5-copy">Press Start to draw your hand. Then choose one intent and commit.</p>',
            '  </div>',
            '  <button class="az-v5-start" data-v5-action="start">Start</button>',
            '</section>',

            '<section class="az-v5-score">',
            '  <article class="az-v5-player">',
            '    <div class="az-v5-player-head"><span>You</span><strong id="az-v5-my-name">Player</strong></div>',
            '    <div class="az-v5-stats">',
            '      <span>HP <strong id="az-v5-my-hp">3600</strong></span>',
            '      <span>EN <strong id="az-v5-my-energy">0/0</strong></span>',
            '      <span>AMB <strong id="az-v5-my-ambition">0</strong></span>',
            '      <span>Intent <strong id="az-v5-my-intent">Strike</strong></span>',
            '    </div>',
            '  </article>',

            '  <article class="az-v5-round">',
            '    <div><span id="az-v5-phase">Set Phase</span><strong id="az-v5-round">Round 1</strong></div>',
            '  </article>',

            '  <article class="az-v5-player">',
            '    <div class="az-v5-player-head"><span>Opponent</span><strong id="az-v5-enemy-name">Opponent</strong></div>',
            '    <div class="az-v5-stats">',
            '      <span>HP <strong id="az-v5-enemy-hp">3600</strong></span>',
            '      <span>EN <strong id="az-v5-enemy-energy">0/0</strong></span>',
            '      <span>AMB <strong id="az-v5-enemy-ambition">0</strong></span>',
            '      <span>Intent <strong id="az-v5-enemy-intent">Hidden</strong></span>',
            '    </div>',
            '  </article>',
            '</section>',

            '<section class="az-v5-board">',
            '  <article class="az-v5-field">',
            '    <div class="az-v5-field-head"><h3>Enemy Field</h3><span id="az-v5-enemy-ready">Waiting</span></div>',
            '    <div class="az-v5-zones">',
            '      <div class="az-v5-zone"><span class="az-v5-zone-label">Monster</span><div id="az-v5-enemy-monster" class="az-v5-slot">Hidden</div></div>',
            '      <div class="az-v5-zone"><span class="az-v5-zone-label">Spell / Trap</span><div id="az-v5-enemy-spell" class="az-v5-slot">Set Zone</div></div>',
            '    </div>',
            '  </article>',

            '  <div class="az-v5-divider"><span id="az-v5-state">Waiting</span></div>',

            '  <article class="az-v5-field">',
            '    <div class="az-v5-field-head"><h3>Your Field</h3><span id="az-v5-field-hint">Choose intent</span></div>',
            '    <div class="az-v5-zones">',
            '      <div class="az-v5-zone"><span class="az-v5-zone-label">Monster</span><div id="az-v5-my-monster" class="az-v5-slot">Empty Monster Zone</div></div>',
            '      <div class="az-v5-zone"><span class="az-v5-zone-label">Spell / Trap</span><div id="az-v5-my-spell" class="az-v5-slot">Empty Spell/Trap Zone</div></div>',
            '    </div>',
            '  </article>',
            '</section>',

            '<section class="az-v5-hand">',
            '  <div class="az-v5-field-head"><h3>Your Hand</h3><span>Tap a card in the original engine or use actions below</span></div>',
            '  <div id="az-v5-hand-row" class="az-v5-hand-row"><div class="az-v5-empty">Start the duel to draw your hand.</div></div>',
            '</section>',

            '<section class="az-v5-tools">',
            '  <details class="az-v5-details"><summary>Battle Log</summary><div id="az-v5-log">No battle events yet.</div></details>',
            '  <details class="az-v5-details"><summary>Quick Tips</summary><div><p><strong>Strike:</strong> pressure HP.</p><p><strong>Guard:</strong> survive pressure.</p><p><strong>Focus:</strong> build Ambition.</p></div></details>',
            '</section>',

            '<nav class="az-v5-dock">',
            '  <button data-v5-action="strike">Strike<small>Attack</small></button>',
            '  <button data-v5-action="guard">Guard<small>Defend</small></button>',
            '  <button data-v5-action="focus">Focus<small>Build</small></button>',
            '  <button data-v5-action="ready">Ready<small>Commit</small></button>',
            '</nav>'
        ].join("");

        document.body.prepend(root);
    }

    function bindActions() {
        document.addEventListener("click", function (event) {
            var btn = event.target.closest("[data-v5-action]");
            if (!btn) return;

            var action = btn.getAttribute("data-v5-action");

            qsa(".az-v5-dock button").forEach(function (b) {
                b.classList.remove("is-selected");
            });

            if (btn.closest(".az-v5-dock")) {
                btn.classList.add("is-selected");
            }

            if (action === "start") {
                clickOld(["start training", "find match", "start", "ready"]);
                setHero("Duel started", "Choose your intent, play your best card, then press Ready.", "Choosing");
            }

            if (action === "strike") {
                clickOld(["strike"]);
                setHero("Strike selected", "Attack pressure. Play a card if possible, then press Ready.", "Attack");
            }

            if (action === "guard") {
                clickOld(["guard"]);
                setHero("Guard selected", "Defend this turn and reduce risk.", "Defend");
            }

            if (action === "focus") {
                clickOld(["focus"]);
                setHero("Focus selected", "Build Ambition for a stronger future turn.", "Build");
            }

            if (action === "ready") {
                clickOld(["ready", "declare ready", "start training"]);
                setHero("Round committed", "Waiting for the result.", "Ready");
            }
        });
    }

    function setHero(title, copy, state) {
        var t = qs("#az-v5-title");
        var c = qs("#az-v5-copy");
        var s = qs("#az-v5-state");

        if (t) t.textContent = title;
        if (c) c.textContent = copy;
        if (s) s.textContent = state;
    }

    function syncStats() {
        var pairs = [
            ["#az-v5-my-name", "#my-name"],
            ["#az-v5-enemy-name", "#enemy-name"],
            ["#az-v5-my-hp", "#my-hp"],
            ["#az-v5-enemy-hp", "#enemy-hp"],
            ["#az-v5-my-energy", "#my-energy"],
            ["#az-v5-enemy-energy", "#enemy-energy"],
            ["#az-v5-my-ambition", "#my-ambition"],
            ["#az-v5-enemy-ambition", "#enemy-ambition"],
            ["#az-v5-my-intent", "#my-intent"],
            ["#az-v5-enemy-intent", "#enemy-intent"],
            ["#az-v5-phase", "#phase-label"],
            ["#az-v5-round", "#round-number"],
            ["#az-v5-enemy-ready", "#enemy-ready"],
            ["#az-v5-field-hint", "#field-hint"]
        ];

        pairs.forEach(function (pair) {
            var target = qs(pair[0]);
            var source = qs(pair[1]);

            if (target && source) {
                var value = (source.textContent || "").trim();
                if (value) target.textContent = value;
            }
        });

        syncHand();
        syncLog();
    }

    function syncHand() {
        var row = qs("#az-v5-hand-row");
        var oldHand = qs("#my-hand");

        if (!row || !oldHand) return;

        var rawText = (oldHand.textContent || "").trim();

        if (!rawText || rawText.toLowerCase().indexOf("start") !== -1) {
            row.innerHTML = '<div class="az-v5-empty">Start the duel to draw your hand.</div>';
            return;
        }

        var cardEls = qsa("#my-hand button, #my-hand .card, #my-hand [data-card-id], #my-hand article");

        if (!cardEls.length) {
            row.innerHTML = '<div class="az-v5-card-mini"><strong>Hand ready</strong><span>Use original card area if needed.</span></div>';
            return;
        }

        row.innerHTML = "";

        cardEls.slice(0, 8).forEach(function (card, index) {
            var name = (card.textContent || "Card").trim().replace(/\s+/g, " ").slice(0, 36);

            var mini = document.createElement("button");
            mini.type = "button";
            mini.className = "az-v5-card-mini";
            mini.innerHTML = "<strong>" + name + "</strong><span>Tap to play</span>";

            mini.addEventListener("click", function () {
                card.click();
            });

            row.appendChild(mini);
        });
    }

    function syncLog() {
        var target = qs("#az-v5-log");
        var oldLog = qs("#battle-log");

        if (!target || !oldLog) return;

        var txt = (oldLog.textContent || "").trim();

        if (txt) {
            target.textContent = txt.slice(-900);
        }
    }

    function boot() {
        if (!isBattlePage()) return;

        createRoot();
        bindActions();
        syncStats();

        setInterval(syncStats, 700);
    }

    document.addEventListener("DOMContentLoaded", boot);
})();
