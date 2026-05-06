/* =========================================================
   Ambitionz Arena Rework V3
   Forces cleaner action UX without changing backend/game rules.
   ========================================================= */

(function () {
    function isBattlePage() {
        return window.location.pathname === "/training" || window.location.pathname === "/arena";
    }

    function allButtons() {
        return Array.prototype.slice.call(document.querySelectorAll("button, a.btn, [role='button']"));
    }

    function findClickableByText(terms) {
        terms = Array.isArray(terms) ? terms : [terms];

        return allButtons().find(function (el) {
            var text = (el.textContent || "").trim().toLowerCase();
            return terms.some(function (term) {
                return text.indexOf(term.toLowerCase()) !== -1;
            });
        });
    }

    function clickFirst(terms) {
        var el = findClickableByText(terms);
        if (el) {
            el.click();
            return true;
        }
        return false;
    }

    function createNextActionBanner() {
        if (document.querySelector(".az-v3-next-action")) return;

        var main = document.querySelector(".page-shell") || document.querySelector("main") || document.body;

        var banner = document.createElement("section");
        banner.className = "az-v3-next-action";
        banner.innerHTML = [
            '<div>',
            '  <small id="az-v3-mode">Battle Flow</small>',
            '  <strong id="az-v3-title">Start the duel</strong>',
            '  <span id="az-v3-subtitle">Draw your hand, choose one intent, then commit the round.</span>',
            '</div>',
            '<div class="az-v3-state-pill" id="az-v3-state">Waiting</div>'
        ].join("");

        var anchor =
            document.querySelector(".arena-shell") ||
            document.querySelector(".arena-layout") ||
            main.firstElementChild;

        if (anchor && anchor.parentNode) {
            anchor.parentNode.insertBefore(banner, anchor);
        } else {
            main.prepend(banner);
        }
    }

    function createDock() {
        if (document.querySelector(".az-v3-dock")) return;

        var dock = document.createElement("nav");
        dock.className = "az-v3-dock";
        dock.innerHTML = [
            '<button type="button" class="az-v3-button" data-az-action="strike">Strike<small>Attack</small></button>',
            '<button type="button" class="az-v3-button" data-az-action="guard">Guard<small>Defend</small></button>',
            '<button type="button" class="az-v3-button" data-az-action="focus">Focus<small>Build</small></button>',
            '<button type="button" class="az-v3-button az-v3-button-ready" data-az-action="ready">Ready<small>Commit</small></button>'
        ].join("");

        document.body.appendChild(dock);

        dock.addEventListener("click", function (event) {
            var button = event.target.closest("button");
            if (!button) return;

            var action = button.getAttribute("data-az-action");

            if (action === "strike") clickFirst(["strike"]);
            if (action === "guard") clickFirst(["guard"]);
            if (action === "focus") clickFirst(["focus"]);

            if (action === "ready") {
                clickFirst(["ready", "declare ready", "start training", "find match", "start duel"]);
            }

            Array.prototype.slice.call(dock.querySelectorAll(".az-v3-button")).forEach(function (btn) {
                btn.classList.remove("is-selected");
            });

            button.classList.add("is-selected");
            setBannerForAction(action);
        });
    }

    function setBannerForAction(action) {
        var title = document.getElementById("az-v3-title");
        var subtitle = document.getElementById("az-v3-subtitle");
        var state = document.getElementById("az-v3-state");

        if (!title || !subtitle || !state) return;

        if (action === "strike") {
            title.textContent = "Strike selected";
            subtitle.textContent = "Pressure the opponent. Play a card if possible, then press Ready.";
            state.textContent = "Attack";
        } else if (action === "guard") {
            title.textContent = "Guard selected";
            subtitle.textContent = "Reduce risk. Good when behind or waiting for a better turn.";
            state.textContent = "Defend";
        } else if (action === "focus") {
            title.textContent = "Focus selected";
            subtitle.textContent = "Build Ambition for a stronger future swing.";
            state.textContent = "Build";
        } else if (action === "ready") {
            title.textContent = "Round committed";
            subtitle.textContent = "Waiting for the duel result.";
            state.textContent = "Ready";
        }
    }

    function inferState() {
        var title = document.getElementById("az-v3-title");
        var subtitle = document.getElementById("az-v3-subtitle");
        var state = document.getElementById("az-v3-state");
        if (!title || !subtitle || !state) return;

        var bodyText = document.body.textContent.toLowerCase();

        if (bodyText.indexOf("start a duel") !== -1 || bodyText.indexOf("start training") !== -1) {
            title.textContent = "Start the duel";
            subtitle.textContent = "Press Ready or Start Training to draw your hand.";
            state.textContent = "Start";
            return;
        }

        if (bodyText.indexOf("choose intent") !== -1) {
            title.textContent = "Choose your intent";
            subtitle.textContent = "Pick Strike, Guard or Focus. Then commit with Ready.";
            state.textContent = "Intent";
            return;
        }

        if (bodyText.indexOf("waiting") !== -1) {
            title.textContent = "Waiting";
            subtitle.textContent = "The match is processing the next move.";
            state.textContent = "Waiting";
            return;
        }
    }

    function collapseSideNoise() {
        var candidates = Array.prototype.slice.call(document.querySelectorAll("section, aside, article, div"));

        candidates.forEach(function (el) {
            var text = (el.textContent || "").trim().toLowerCase();

            if (text === "quick tips" || text.indexOf("quick tips") === 0) {
                el.classList.add("az-v3-collapsed-tips");
            }

            if (text === "battle log" || text.indexOf("battle log") === 0) {
                el.classList.add("az-v3-collapsed-log");
            }
        });
    }

    function boot() {
        if (!isBattlePage()) return;

        document.body.classList.add("az-v3-ready");

        createNextActionBanner();
        createDock();
        collapseSideNoise();
        inferState();

        setInterval(inferState, 1400);
    }

    document.addEventListener("DOMContentLoaded", boot);
})();
