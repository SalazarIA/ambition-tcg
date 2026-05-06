/* =========================================================
   Ambitionz Guided Tutorial
   Training-only guided overlay.
   ========================================================= */

(function () {
    function isTraining() {
        return window.location.pathname === "/training";
    }

    function qs(selector) {
        return document.querySelector(selector);
    }

    function qsa(selector) {
        return Array.prototype.slice.call(document.querySelectorAll(selector));
    }

    var state = {
        step: 0,
        completed: {
            start: false,
            intent: false,
            ready: false,
            reward: false
        }
    };

    var steps = [
        {
            key: "start",
            title: "Start the duel",
            copy: "Tap Start or Ready to draw your first hand. The goal is simple: make one clean round.",
            target: '[data-v7-action="ready"], .az-v7-main-action',
            actionLabel: "Start"
        },
        {
            key: "intent",
            title: "Choose your intent",
            copy: "Pick Strike, Guard or Focus. Strike attacks, Guard defends, Focus builds Ambition.",
            target: '[data-v7-action="strike"]',
            actionLabel: "Choose Strike"
        },
        {
            key: "ready",
            title: "Commit the round",
            copy: "Once your intent is selected, tap Ready. This locks your move and resolves the duel round.",
            target: '[data-v7-action="ready"], .az-v7-main-action',
            actionLabel: "Ready"
        },
        {
            key: "reward",
            title: "Progress after every match",
            copy: "Training gives XP, coins and mission progress. After the duel, open Daily Quests or improve your deck.",
            target: '.az-v7-hand, .az-v7-root',
            actionLabel: "Got it"
        }
    ];

    function createOverlay() {
        if (qs(".az-tutorial-overlay")) return;

        var overlay = document.createElement("section");
        overlay.className = "az-tutorial-overlay";
        overlay.innerHTML = [
            '<div class="az-tutorial-head">',
            '  <span class="az-tutorial-kicker" id="az-tutorial-kicker">Tutorial</span>',
            '  <button class="az-tutorial-close" type="button" aria-label="Close tutorial">×</button>',
            '</div>',
            '<h2 id="az-tutorial-title">Start the duel</h2>',
            '<p id="az-tutorial-copy">Tap Start to begin.</p>',
            '<div class="az-tutorial-progress" id="az-tutorial-progress"></div>',
            '<div class="az-tutorial-actions">',
            '  <button class="az-tutorial-btn primary" type="button" id="az-tutorial-primary">Start</button>',
            '  <button class="az-tutorial-btn" type="button" id="az-tutorial-next">Next</button>',
            '  <button class="az-tutorial-btn" type="button" id="az-tutorial-skip">Skip</button>',
            '</div>'
        ].join("");

        document.body.appendChild(overlay);

        qs(".az-tutorial-close").addEventListener("click", hideTutorial);
        qs("#az-tutorial-skip").addEventListener("click", completeTutorial);
        qs("#az-tutorial-next").addEventListener("click", nextStep);
        qs("#az-tutorial-primary").addEventListener("click", performStepAction);
    }

    function createPlayabilityPanel() {
        if (qs(".az-playability-panel")) return;

        var panel = document.createElement("aside");
        panel.className = "az-playability-panel";
        panel.innerHTML = [
            '<strong>Training Checklist</strong>',
            '<div class="az-playability-list">',
            '  <div class="az-playability-item" data-check="start"><span class="az-playability-check"></span>Start duel</div>',
            '  <div class="az-playability-item" data-check="intent"><span class="az-playability-check"></span>Choose intent</div>',
            '  <div class="az-playability-item" data-check="ready"><span class="az-playability-check"></span>Press Ready</div>',
            '  <div class="az-playability-item" data-check="reward"><span class="az-playability-check"></span>Earn progress</div>',
            '</div>'
        ].join("");

        document.body.appendChild(panel);
    }

    function renderProgress() {
        var progress = qs("#az-tutorial-progress");
        if (!progress) return;

        progress.innerHTML = "";

        steps.forEach(function (_, index) {
            var dot = document.createElement("div");
            dot.className = "az-tutorial-dot" + (index <= state.step ? " is-active" : "");
            progress.appendChild(dot);
        });
    }

    function renderStep() {
        var step = steps[state.step];
        if (!step) return;

        var overlay = qs(".az-tutorial-overlay");
        var panel = qs(".az-playability-panel");

        if (overlay) overlay.classList.add("is-visible");
        if (panel) panel.classList.add("is-visible");

        qs("#az-tutorial-kicker").textContent = "Step " + (state.step + 1) + " / " + steps.length;
        qs("#az-tutorial-title").textContent = step.title;
        qs("#az-tutorial-copy").textContent = step.copy;
        qs("#az-tutorial-primary").textContent = step.actionLabel;

        renderProgress();
        highlightTarget(step.target);
        updateChecklist();
    }

    function highlightTarget(selector) {
        qsa(".az-tutorial-highlight").forEach(function (el) {
            el.classList.remove("az-tutorial-highlight");
        });

        var target = qs(selector);
        if (target) {
            target.classList.add("az-tutorial-highlight");
        }
    }

    function updateChecklist() {
        Object.keys(state.completed).forEach(function (key) {
            var item = qs('[data-check="' + key + '"]');
            if (!item) return;

            if (state.completed[key]) {
                item.classList.add("done");
                var check = item.querySelector(".az-playability-check");
                if (check) check.textContent = "✓";
            }
        });
    }

    function nextStep() {
        markCurrentDone();

        if (state.step < steps.length - 1) {
            state.step += 1;
            renderStep();
        } else {
            completeTutorial();
        }
    }

    function markCurrentDone() {
        var step = steps[state.step];
        if (step) {
            state.completed[step.key] = true;
            updateChecklist();
        }
    }

    function performStepAction() {
        var step = steps[state.step];

        if (!step) return;

        if (step.key === "start") {
            clickFirst(['[data-v7-action="ready"]', ".az-v7-main-action"]);
            state.completed.start = true;
            setTimeout(function () {
                state.step = 1;
                renderStep();
            }, 450);
            return;
        }

        if (step.key === "intent") {
            clickFirst(['[data-v7-action="strike"]']);
            state.completed.intent = true;
            setTimeout(function () {
                state.step = 2;
                renderStep();
            }, 450);
            return;
        }

        if (step.key === "ready") {
            clickFirst(['[data-v7-action="ready"]', ".az-v7-main-action"]);
            state.completed.ready = true;
            setTimeout(function () {
                state.step = 3;
                renderStep();
            }, 650);
            return;
        }

        if (step.key === "reward") {
            state.completed.reward = true;
            completeTutorial();
        }
    }

    function clickFirst(selectors) {
        for (var i = 0; i < selectors.length; i++) {
            var el = qs(selectors[i]);
            if (el) {
                el.click();
                return true;
            }
        }

        return false;
    }

    function hideTutorial() {
        var overlay = qs(".az-tutorial-overlay");
        if (overlay) overlay.classList.remove("is-visible");

        qsa(".az-tutorial-highlight").forEach(function (el) {
            el.classList.remove("az-tutorial-highlight");
        });

        try {
            localStorage.setItem("ambitionz_tutorial_hidden", "1");
        } catch (err) {}
    }

    function completeTutorial() {
        state.completed.start = true;
        state.completed.intent = true;
        state.completed.ready = true;
        state.completed.reward = true;

        updateChecklist();

        var overlay = qs(".az-tutorial-overlay");
        if (overlay) {
            qs("#az-tutorial-title").textContent = "Tutorial complete";
            qs("#az-tutorial-copy").textContent = "Good. Now play a full training match, claim rewards and improve your deck.";
            setTimeout(function () {
                overlay.classList.remove("is-visible");
            }, 1600);
        }

        qsa(".az-tutorial-highlight").forEach(function (el) {
            el.classList.remove("az-tutorial-highlight");
        });

        try {
            localStorage.setItem("ambitionz_tutorial_complete", "1");
        } catch (err) {}
    }

    function listenForManualActions() {
        document.addEventListener("click", function (event) {
            var target = event.target.closest("[data-v7-action], .az-v7-main-action");
            if (!target) return;

            var action = target.getAttribute("data-v7-action");

            if (action === "ready") {
                if (!state.completed.start) {
                    state.completed.start = true;
                    state.step = Math.max(state.step, 1);
                } else {
                    state.completed.ready = true;
                }
            }

            if (["strike", "guard", "focus"].includes(action)) {
                state.completed.intent = true;
                state.step = Math.max(state.step, 2);
            }

            updateChecklist();
        });
    }

    function boot() {
        if (!isTraining()) return;

        createOverlay();
        createPlayabilityPanel();
        listenForManualActions();

        var completed = false;

        try {
            completed = localStorage.getItem("ambitionz_tutorial_complete") === "1";
        } catch (err) {}

        if (!completed) {
            setTimeout(renderStep, 800);
        } else {
            var panel = qs(".az-playability-panel");
            if (panel) panel.classList.add("is-visible");
        }
    }

    document.addEventListener("DOMContentLoaded", boot);

    window.AmbitionzTutorial = {
        start: function () {
            state.step = 0;
            renderStep();
        },
        complete: completeTutorial
    };
})();
