/* =========================================================
   Ambitionz Training Coach
   Compact helper UI for /training only.
   Does not alter battle rules or SocketIO.
   ========================================================= */

(function () {
    function qs(selector) {
        return document.querySelector(selector);
    }

    function isTrainingPage() {
        return window.location.pathname === "/training";
    }

    function createTrainingCoach() {
        if (!isTrainingPage()) return;
        if (document.querySelector(".training-coach-compact")) return;

        var shell = qs(".page-shell") || qs("main") || document.body;
        if (!shell) return;

        var coach = document.createElement("section");
        coach.className = "training-coach-compact";
        coach.innerHTML = [
            '<div class="training-coach-top">',
            '  <div>',
            '    <span class="training-chip">Training Guide</span>',
            '    <h2>Win the round, not the screen.</h2>',
            '    <p>Pick one intent, play cards you can afford, then press Ready.</p>',
            '  </div>',
            '  <button type="button" class="training-coach-hide" aria-label="Hide training guide">×</button>',
            '</div>',
            '<div class="training-steps-compact">',
            '  <span><strong>1</strong> Intent</span>',
            '  <span><strong>2</strong> Card</span>',
            '  <span><strong>3</strong> Ready</span>',
            '</div>',
            '<div class="training-intent-help">',
            '  <article><strong>Strike</strong><small>Attack pressure.</small></article>',
            '  <article><strong>Guard</strong><small>Defend tempo.</small></article>',
            '  <article><strong>Focus</strong><small>Build Ambition.</small></article>',
            '</div>'
        ].join("");

        var anchor =
            qs(".arena-status-row") ||
            qs(".arena-top-grid") ||
            qs(".arena-shell") ||
            qs(".hero-card") ||
            shell.firstElementChild;

        if (anchor && anchor.parentNode) {
            anchor.parentNode.insertBefore(coach, anchor.nextSibling);
        } else {
            shell.prepend(coach);
        }

        var hideBtn = coach.querySelector(".training-coach-hide");
        if (hideBtn) {
            hideBtn.addEventListener("click", function () {
                coach.classList.add("is-hidden");
                try {
                    localStorage.setItem("ambitionz_training_coach_hidden", "1");
                } catch (err) {}
            });
        }

        try {
            if (localStorage.getItem("ambitionz_training_coach_hidden") === "1") {
                coach.classList.add("is-hidden");
            }
        } catch (err) {}
    }

    function markTrainingActions() {
        if (!isTrainingPage()) return;

        document.querySelectorAll("button, a.btn").forEach(function (el) {
            var text = (el.textContent || "").trim().toLowerCase();

            if (
                text.indexOf("start training") !== -1 ||
                text === "ready" ||
                text.indexOf("declare ready") !== -1
            ) {
                el.classList.add("training-primary-action");
            }
        });
    }

    function bindIntentSelectionFeedback() {
        if (!isTrainingPage()) return;

        document.querySelectorAll("button, .btn").forEach(function (el) {
            var text = (el.textContent || "").toLowerCase();

            if (
                text.indexOf("strike") !== -1 ||
                text.indexOf("guard") !== -1 ||
                text.indexOf("focus") !== -1
            ) {
                el.addEventListener("click", function () {
                    document.querySelectorAll(".training-intent-selected").forEach(function (x) {
                        x.classList.remove("training-intent-selected");
                    });
                    el.classList.add("training-intent-selected");
                });
            }
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!isTrainingPage()) return;

        createTrainingCoach();
        markTrainingActions();
        bindIntentSelectionFeedback();
    });
})();
