/* =========================================================
   Ambitionz Arena V7 — Board Game Style
   Visible game board overlay. Old engine remains hidden.
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

    function oldText(selector, fallback) {
        var el = qs(selector);
        return el ? (el.textContent || "").trim() : fallback;
    }

    function findOldButton(terms) {
        terms = Array.isArray(terms) ? terms : [terms];

        return qsa("button, a.btn, [role='button']").find(function (el) {
            if (el.closest(".az-v7-root")) return false;
            if (el.closest(".az-v5-root")) return false;

            var text = (el.textContent || "").trim().toLowerCase();

            return terms.some(function (term) {
                return text.indexOf(term.toLowerCase()) !== -1;
            });
        });
    }

    function clickOld(terms) {
        var btn = findOldButton(terms);

        if (btn) {
            btn.click();
            return true;
        }

        return false;
    }

    function createCard(name, index, kind) {
        var card = document.createElement("button");
        card.type = "button";
        card.className = kind === "hand" ? "az-v7-hand-card" : "az-v7-board-card";
        card.style.setProperty("--rot", ((index - 2) * 3) + "deg");
        card.style.setProperty("--lift", Math.abs(index - 2) * 3 + "px");
        card.innerHTML = [
            '<div class="cost">' + ((index % 4) + 1) + '</div>',
            '<strong>' + name + '</strong>',
            '<span>Ambitionz</span>',
            kind === "board" ? '<div class="atk">' + (index + 1) + '</div><div class="hp">' + (index + 2) + '</div>' : ''
        ].join("");

        return card;
    }

    function createRoot() {
        if (qs(".az-v7-root")) return;

        document.body.classList.add("az-v5-active");
        document.body.classList.add("az-v7-active");

        var mode = window.location.pathname === "/training" ? "Training" : "Arena";

        var root = document.createElement("main");
        root.className = "az-v7-root";
        root.innerHTML = [
            '<div class="az-v7-board-line"></div>',

            '<div class="az-v7-top">',
            '  <div></div>',
            '  <div class="az-v7-mode">Online</div>',
            '  <a href="/" class="az-v7-back">Back</a>',
            '</div>',

            '<div class="az-v7-log"><button type="button" id="az-v7-log-btn">•••</button></div>',

            '<div class="az-v7-avatar enemy"></div>',
            '<div class="az-v7-side-name enemy"><span>Enemy</span><strong id="az-v7-enemy-name">Opponent</strong></div>',
            '<div class="az-v7-hp-orb enemy" id="az-v7-enemy-hp">36</div>',
            '<div class="az-v7-resource-orb enemy" id="az-v7-enemy-energy">0/0</div>',

            '<div class="az-v7-round"><div><span id="az-v7-phase">Set Phase</span><strong id="az-v7-round">Round 1</strong></div></div>',

            '<div class="az-v7-lane enemy" id="az-v7-enemy-lane">',
            '  <div class="az-v7-board-card" style="--rot:-4deg"><div class="cost">1</div><strong>Hidden</strong><div class="atk">?</div><div class="hp">?</div></div>',
            '  <div class="az-v7-board-card" style="--rot:2deg"><div class="cost">2</div><strong>Set Zone</strong><div class="atk">?</div><div class="hp">?</div></div>',
            '</div>',

            '<button class="az-v7-main-action" data-v7-action="ready">Ready<small>Commit</small></button>',

            '<div class="az-v7-lane you" id="az-v7-your-lane">',
            '  <div class="az-v7-board-card" style="--rot:-2deg"><div class="cost">1</div><strong>Monster Zone</strong><div class="atk">0</div><div class="hp">0</div></div>',
            '  <div class="az-v7-board-card" style="--rot:3deg"><div class="cost">2</div><strong>Spell Zone</strong><div class="atk">0</div><div class="hp">0</div></div>',
            '</div>',

            '<div class="az-v7-deck-pile enemy"></div>',
            '<div class="az-v7-deck-pile you"></div>',

            '<div class="az-v7-avatar you"></div>',
            '<div class="az-v7-side-name you"><span>You</span><strong id="az-v7-my-name">Player</strong></div>',
            '<div class="az-v7-hp-orb you" id="az-v7-my-hp">36</div>',
            '<div class="az-v7-resource-orb you" id="az-v7-my-energy">0/0</div>',

            '<div class="az-v7-hand" id="az-v7-hand">',
            '  <div class="az-v7-hand-card"><div class="cost">0</div><strong>Start Duel</strong><span>Draw your hand</span></div>',
            '</div>',

            '<div class="az-v7-intents">',
            '  <button data-v7-action="strike">Strike</button>',
            '  <button data-v7-action="guard">Guard</button>',
            '  <button data-v7-action="focus">Focus</button>',
            '  <button data-v7-action="ready">Ready</button>',
            '</div>'
        ].join("");

        document.body.appendChild(root);
    }

    function bindActions() {
        document.addEventListener("click", function (event) {
            var btn = event.target.closest("[data-v7-action]");
            if (!btn) return;

            var action = btn.getAttribute("data-v7-action");

            qsa(".az-v7-intents button").forEach(function (b) {
                b.classList.remove("is-selected");
            });

            if (btn.closest(".az-v7-intents")) {
                btn.classList.add("is-selected");
            }

            if (action === "strike") clickOld(["strike"]);
            if (action === "guard") clickOld(["guard"]);
            if (action === "focus") clickOld(["focus"]);
            if (action === "ready") clickOld(["ready", "start training", "find match", "start"]);
        });
    }

    function normalizeHp(value) {
        var n = parseInt(String(value || "").replace(/\D/g, ""), 10);
        if (!n && n !== 0) return value || "36";

        if (n >= 100) {
            return String(Math.round(n / 100));
        }

        return String(n);
    }

    function syncStats() {
        var myName = oldText("#my-name", "Player");
        var enemyName = oldText("#enemy-name", "Opponent");

        var myHp = normalizeHp(oldText("#my-hp", "3600"));
        var enemyHp = normalizeHp(oldText("#enemy-hp", "3600"));

        var myEnergy = oldText("#my-energy", "0/0");
        var enemyEnergy = oldText("#enemy-energy", "0/0");

        var phase = oldText("#phase-label", "Set Phase");
        var round = oldText("#round-number", "Round 1");

        set("#az-v7-my-name", myName);
        set("#az-v7-enemy-name", enemyName);
        set("#az-v7-my-hp", myHp);
        set("#az-v7-enemy-hp", enemyHp);
        set("#az-v7-my-energy", myEnergy);
        set("#az-v7-enemy-energy", enemyEnergy);
        set("#az-v7-phase", phase);
        set("#az-v7-round", round);

        syncHand();
    }

    function set(selector, value) {
        var el = qs(selector);
        if (el && value) el.textContent = value;
    }

    function syncHand() {
        var hand = qs("#az-v7-hand");
        var oldHand = qs("#my-hand");

        if (!hand || !oldHand) return;

        var oldTextValue = (oldHand.textContent || "").trim();

        if (!oldTextValue || oldTextValue.toLowerCase().indexOf("start") !== -1) {
            if (!hand.dataset.empty) {
                hand.innerHTML = '<div class="az-v7-hand-card"><div class="cost">0</div><strong>Start Duel</strong><span>Draw your hand</span></div>';
                hand.dataset.empty = "1";
            }
            return;
        }

        var oldCards = qsa("#my-hand button, #my-hand [data-card-id], #my-hand article, #my-hand .card");

        if (!oldCards.length) {
            if (hand.dataset.fallback !== "1") {
                hand.innerHTML = "";
                ["Card", "Card", "Card", "Card", "Card"].forEach(function (name, index) {
                    hand.appendChild(createCard(name, index, "hand"));
                });
                hand.dataset.fallback = "1";
                hand.dataset.empty = "";
            }
            return;
        }

        hand.innerHTML = "";
        oldCards.slice(0, 6).forEach(function (oldCard, index) {
            var label = (oldCard.textContent || "Card").trim().replace(/\s+/g, " ").slice(0, 24);
            var card = createCard(label, index, "hand");

            card.addEventListener("click", function () {
                oldCard.click();
            });

            hand.appendChild(card);
        });

        hand.dataset.empty = "";
        hand.dataset.fallback = "";
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



/* Arena animation integration */
(function () {
    function isBattlePage() {
        return window.location.pathname === "/training" || window.location.pathname === "/arena";
    }

    if (!isBattlePage()) return;

    document.addEventListener("click", function (event) {
        var card = event.target.closest(".az-v7-hand-card");
        if (!card) return;

        card.classList.remove("az-card-played");
        void card.offsetWidth;
        card.classList.add("az-card-played");
    });
})();

