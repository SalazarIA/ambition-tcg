/* =========================================================
   Ambitionz Battle Premium Layer
   Non-invasive helper UI. Does not alter game rules.
   ========================================================= */

(function () {
    function qs(selector) {
        return document.querySelector(selector);
    }

    function createBattleCoach() {
        if (document.querySelector(".premium-battle-coach")) return;

        var shell = qs(".page-shell") || qs("main") || document.body;
        if (!shell) return;

        var coach = document.createElement("section");
        coach.className = "premium-battle-coach";
        coach.innerHTML = [
            '<div class="premium-coach-head">',
            '  <div>',
            '    <span class="progression-kicker">Battle Coach</span>',
            '    <h2>Choose with intent</h2>',
            '    <p>Strike pressures HP, Guard reduces risk, Focus builds Ambition. Commit only when your round plan is clear.</p>',
            '  </div>',
            '  <span class="premium-status-pill" id="premium-battle-status">Ready</span>',
            '</div>',
            '<div class="premium-round-strip">',
            '  <span>1. Pick Intent</span>',
            '  <span>2. Spend Energy</span>',
            '  <span>3. Build Ambition</span>',
            '  <span>4. Declare Ready</span>',
            '</div>',
            '<div class="premium-intent-grid">',
            '  <article class="premium-intent-card"><strong>Strike</strong><span>Best when you can convert board pressure into damage.</span></article>',
            '  <article class="premium-intent-card"><strong>Guard</strong><span>Best when behind, low HP, or waiting for a better hand.</span></article>',
            '  <article class="premium-intent-card"><strong>Focus</strong><span>Best when preparing Ambition swing turns or Unleash pressure.</span></article>',
            '</div>'
        ].join("");

        var anchor = qs(".arena-shell") || qs(".hero-card") || shell.firstElementChild;
        if (anchor && anchor.parentNode) {
            anchor.parentNode.insertBefore(coach, anchor.nextSibling);
        } else {
            shell.prepend(coach);
        }
    }

    function inferBattleStatus() {
        var status = qs("#premium-battle-status");
        if (!status) return;

        var myHp = qs("#my-hp");
        var enemyHp = qs("#enemy-hp");
        var myEnergy = qs("#my-energy");
        var myAmbition = qs("#my-ambition");

        var hpText = myHp ? myHp.textContent.trim() : "";
        var enemyText = enemyHp ? enemyHp.textContent.trim() : "";
        var energyText = myEnergy ? myEnergy.textContent.trim() : "";
        var ambitionText = myAmbition ? myAmbition.textContent.trim() : "";

        var parts = [];
        if (hpText) parts.push("HP " + hpText);
        if (enemyText) parts.push("Enemy " + enemyText);
        if (energyText) parts.push("Energy " + energyText);
        if (ambitionText) parts.push("Ambition " + ambitionText);

        status.textContent = parts.length ? parts.join(" · ") : "Ready";
    }

    function highlightPrimaryActions() {
        var labels = ["Start Training", "Find Match", "Declare Ready", "Ready", "Start"];
        document.querySelectorAll("button, a.btn").forEach(function (el) {
            var text = (el.textContent || "").trim();
            if (labels.some(function (label) { return text.indexOf(label) !== -1; })) {
                el.classList.add("premium-action-glow");
            }
        });
    }

    function bindIntentFocus() {
        document.querySelectorAll("button, .btn").forEach(function (el) {
            var text = (el.textContent || "").toLowerCase();
            if (text.indexOf("strike") !== -1 || text.indexOf("guard") !== -1 || text.indexOf("focus") !== -1) {
                el.addEventListener("click", function () {
                    document.querySelectorAll(".premium-battle-focus").forEach(function (x) {
                        x.classList.remove("premium-battle-focus");
                    });
                    el.classList.add("premium-battle-focus");
                    var status = qs("#premium-battle-status");
                    if (status) status.textContent = "Intent selected: " + (el.textContent || "").trim();
                });
            }
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!/\/arena|\/training/.test(window.location.pathname)) return;

        createBattleCoach();
        inferBattleStatus();
        highlightPrimaryActions();
        bindIntentFocus();

        setInterval(inferBattleStatus, 1500);
    });
})();
