/* =========================================================
   Ambitionz Deck Builder Premium Layer
   Non-invasive helper UI. Does not alter save behavior.
   ========================================================= */

(function () {
    function qs(selector) {
        return document.querySelector(selector);
    }

    function qsa(selector) {
        return Array.prototype.slice.call(document.querySelectorAll(selector));
    }

    function parseNumber(text) {
        var match = String(text || "").match(/\d+/);
        return match ? Number(match[0]) : 0;
    }

    function countSelectedCards() {
        var candidates = [
            "#deck-count",
            "[data-deck-count]",
            ".deck-count",
            "#selected-count"
        ];

        for (var i = 0; i < candidates.length; i++) {
            var el = qs(candidates[i]);
            if (el) {
                var value = parseNumber(el.textContent || el.value);
                if (value) return value;
            }
        }

        var hiddenInputs = qsa('input[name="cards"], input[name="card_ids"], input[name="deck_cards"]');
        if (hiddenInputs.length) return hiddenInputs.length;

        var selectedRows = qsa(".selected-card, .deck-card, [data-selected-card]");
        return selectedRows.length || 0;
    }

    function createDeckPanel() {
        if (qs(".deck-premium-panel")) return;

        var shell = qs(".page-shell") || qs("main") || document.body;
        if (!shell) return;

        var panel = document.createElement("section");
        panel.className = "deck-premium-panel";
        panel.innerHTML = [
            '<div class="deck-premium-head">',
            '  <div>',
            '    <span class="progression-kicker">Deck Coach</span>',
            '    <h2>30-card beta discipline</h2>',
            '    <p>Build a readable deck: enough low-cost cards, clear intent synergy and no random pile.</p>',
            '  </div>',
            '  <span class="premium-status-pill" id="deck-premium-status">Analyzing</span>',
            '</div>',
            '<div class="deck-premium-grid">',
            '  <article class="deck-premium-stat"><strong id="deck-premium-count">0/30</strong><span>Selected cards</span><div class="deck-premium-bar"><span id="deck-premium-fill"></span></div></article>',
            '  <article class="deck-premium-stat"><strong>Early Game</strong><span>Prioritize playable cards for the first turns.</span></article>',
            '  <article class="deck-premium-stat"><strong>Win Plan</strong><span>Pick a strategy: Strike pressure, Guard control or Focus ramp.</span></article>',
            '</div>'
        ].join("");

        var anchor = qs(".hero-card") || shell.firstElementChild;
        if (anchor && anchor.parentNode) {
            anchor.parentNode.insertBefore(panel, anchor.nextSibling);
        } else {
            shell.prepend(panel);
        }
    }

    function updateDeckPanel() {
        var countEl = qs("#deck-premium-count");
        var fill = qs("#deck-premium-fill");
        var status = qs("#deck-premium-status");
        if (!countEl || !fill || !status) return;

        var count = countSelectedCards();
        var pct = Math.max(0, Math.min(100, (count / 30) * 100));

        countEl.textContent = count + "/30";
        fill.style.width = pct + "%";

        status.classList.remove("deck-premium-good", "deck-premium-warning", "deck-premium-bad");

        if (count === 30) {
            status.textContent = "Deck valid";
            status.classList.add("deck-premium-good");
        } else if (count > 30) {
            status.textContent = "Too many cards";
            status.classList.add("deck-premium-bad");
        } else if (count >= 24) {
            status.textContent = "Almost ready";
            status.classList.add("deck-premium-warning");
        } else {
            status.textContent = "Needs cards";
            status.classList.add("deck-premium-warning");
        }
    }

    function bindUpdates() {
        document.addEventListener("click", function () {
            setTimeout(updateDeckPanel, 120);
        });

        document.addEventListener("change", function () {
            setTimeout(updateDeckPanel, 120);
        });

        setInterval(updateDeckPanel, 1600);
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (window.location.pathname.indexOf("/deck-builder") === -1) return;

        createDeckPanel();
        updateDeckPanel();
        bindUpdates();
    });
})();
