/* =========================================================
   Ambitionz Arena Rework V2
   Adds clear action dock and turn banner without changing rules.
   ========================================================= */

(function () {
    function isBattlePage() {
        return window.location.pathname === "/training" || window.location.pathname === "/arena";
    }

    function textOf(selector, fallback) {
        var el = document.querySelector(selector);
        return el ? (el.textContent || "").trim() : fallback;
    }

    function findButtonByText(text) {
        text = text.toLowerCase();

        var buttons = Array.prototype.slice.call(document.querySelectorAll("button, a.btn"));
        return buttons.find(function (button) {
            return (button.textContent || "").trim().toLowerCase().indexOf(text) !== -1;
        });
    }

    function clickExisting(label) {
        var btn = findButtonByText(label);
        if (btn) {
            btn.click();
            return true;
        }
        return false;
    }

    function createTurnBanner() {
        if (document.querySelector(".ambitionz-turn-banner")) return;

        var main = document.querySelector(".page-shell") || document.querySelector("main") || document.body;
        var banner = document.createElement("section");
        banner.className = "ambitionz-turn-banner";
        banner.innerHTML = [
            '<div>',
            '  <strong id="az-banner-player">You</strong><br>',
            '  <span id="az-banner-player-state">HP / Energy / Ambition</span>',
            '</div>',
            '<div class="ambitionz-turn-center">',
            '  <strong id="az-banner-round">Round</strong><br>',
            '  <span id="az-banner-phase">Choose your move</span>',
            '</div>',
            '<div class="ambitionz-turn-right">',
            '  <strong id="az-banner-enemy">Opponent</strong><br>',
            '  <span id="az-banner-enemy-state">HP / Energy / Ambition</span>',
            '</div>'
        ].join("");

        var firstUseful =
            document.querySelector(".arena-shell") ||
            document.querySelector(".arena-layout") ||
            main.firstElementChild;

        if (firstUseful && firstUseful.parentNode) {
            firstUseful.parentNode.insertBefore(banner, firstUseful);
        } else {
            main.prepend(banner);
        }
    }

    function updateTurnBanner() {
        var playerState = document.getElementById("az-banner-player-state");
        var enemyState = document.getElementById("az-banner-enemy-state");
        var round = document.getElementById("az-banner-round");
        var phase = document.getElementById("az-banner-phase");

        if (!playerState || !enemyState || !round || !phase) return;

        var myHp = textOf("#my-hp", textOf("[data-my-hp]", "?"));
        var myEnergy = textOf("#my-energy", textOf("[data-my-energy]", "?"));
        var myAmbition = textOf("#my-ambition", textOf("[data-my-ambition]", "?"));

        var enemyHp = textOf("#enemy-hp", textOf("[data-enemy-hp]", "?"));
        var enemyEnergy = textOf("#enemy-energy", textOf("[data-enemy-energy]", "?"));
        var enemyAmbition = textOf("#enemy-ambition", textOf("[data-enemy-ambition]", "?"));

        var roundText = textOf("#round-number", textOf("[data-round]", "Round 1"));
        var phaseText = textOf("#phase-label", textOf("[data-phase]", "Choose your move"));

        playerState.textContent = "HP " + myHp + " · EN " + myEnergy + " · AMB " + myAmbition;
        enemyState.textContent = "HP " + enemyHp + " · EN " + enemyEnergy + " · AMB " + enemyAmbition;
        round.textContent = roundText;
        phase.textContent = phaseText;
    }

    function createActionDock() {
        if (document.querySelector(".ambitionz-action-dock")) return;

        var dock = document.createElement("nav");
        dock.className = "ambitionz-action-dock";
        dock.innerHTML = [
            '<button type="button" data-action="strike">Strike<small>Attack</small></button>',
            '<button type="button" data-action="guard">Guard<small>Defend</small></button>',
            '<button type="button" data-action="focus">Focus<small>Build</small></button>',
            '<button type="button" data-action="ready">Ready<small>Commit</small></button>'
        ].join("");

        document.body.appendChild(dock);

        dock.addEventListener("click", function (event) {
            var button = event.target.closest("button");
            if (!button) return;

            var action = button.getAttribute("data-action");

            if (action === "strike") clickExisting("strike");
            if (action === "guard") clickExisting("guard");
            if (action === "focus") clickExisting("focus");
            if (action === "ready") {
                clickExisting("ready") ||
                clickExisting("declare ready") ||
                clickExisting("start training") ||
                clickExisting("find match");
            }

            Array.prototype.slice.call(dock.querySelectorAll("button")).forEach(function (btn) {
                btn.classList.remove("is-selected");
            });

            button.classList.add("is-selected");
        });
    }

    function collapseNoise() {
        var tips = document.querySelector(".quick-tips, .tips-panel");
        if (tips && !tips.dataset.azCollapsed) {
            tips.dataset.azCollapsed = "1";
        }

        var log = document.querySelector(".battle-log, #battle-log");
        if (log && !log.dataset.azCollapsed) {
            log.dataset.azCollapsed = "1";
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!isBattlePage()) return;

        createTurnBanner();
        createActionDock();
        collapseNoise();
        updateTurnBanner();

        setInterval(updateTurnBanner, 1000);
    });
})();
