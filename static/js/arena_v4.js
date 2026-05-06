/* =========================================================
   Ambitionz Arena V4 Bridge
   Keeps new UI synced and bridges bottom dock to native buttons.
   ========================================================= */

(function () {
    function qs(selector) {
        return document.querySelector(selector);
    }

    function qsa(selector) {
        return Array.prototype.slice.call(document.querySelectorAll(selector));
    }

    function setText(selector, value) {
        var el = qs(selector);
        if (el && value !== undefined && value !== null) {
            el.textContent = value;
        }
    }

    function clickIntent(intent) {
        var button = qs('[data-intent="' + intent + '"]');
        if (button) {
            button.click();
            markSelected(intent);
            updateNextMove(intent);
        }
    }

    function clickReady() {
        var btn = qs("#ready-btn");
        if (btn) {
            btn.click();
            updateNextMove("Ready");
        }
    }

    function markSelected(intent) {
        qsa(".az-v4-action-btn, .az-v4-dock-btn").forEach(function (el) {
            el.classList.remove("is-selected");
        });

        qsa('[data-intent="' + intent + '"], [data-v4-click="' + intent + '"]').forEach(function (el) {
            el.classList.add("is-selected");
        });
    }

    function updateNextMove(action) {
        var title = qs("#next-move-title");
        var copy = qs("#next-move-copy");
        var state = qs("#battle-state-label");

        if (!title || !copy) return;

        if (action === "Strike") {
            title.textContent = "Strike selected";
            copy.textContent = "Pressure the opponent. Play a card if possible, then press Ready.";
            if (state) state.textContent = "Attack";
        }

        if (action === "Guard") {
            title.textContent = "Guard selected";
            copy.textContent = "Defend this round and reduce risk.";
            if (state) state.textContent = "Defend";
        }

        if (action === "Focus") {
            title.textContent = "Focus selected";
            copy.textContent = "Build Ambition and prepare a stronger future turn.";
            if (state) state.textContent = "Build";
        }

        if (action === "Ready") {
            title.textContent = "Round committed";
            copy.textContent = "Waiting for the round result.";
            if (state) state.textContent = "Ready";
        }
    }

    function bindDock() {
        qsa("[data-v4-click]").forEach(function (button) {
            button.addEventListener("click", function () {
                var action = button.getAttribute("data-v4-click");

                if (action === "Strike" || action === "Guard" || action === "Focus") {
                    clickIntent(action);
                }

                if (action === "Ready") {
                    clickReady();
                }
            });
        });
    }

    function bindActionButtons() {
        qsa("[data-intent]").forEach(function (button) {
            button.addEventListener("click", function () {
                var intent = button.getAttribute("data-intent");
                markSelected(intent);
                updateNextMove(intent);
            });
        });

        var ready = qs("#ready-btn");
        if (ready) {
            ready.addEventListener("click", function () {
                updateNextMove("Ready");
            });
        }
    }

    function inferFromText() {
        var body = document.body ? document.body.textContent.toLowerCase() : "";
        var title = qs("#next-move-title");
        var copy = qs("#next-move-copy");
        var state = qs("#battle-state-label");

        if (!title || !copy) return;

        if (body.indexOf("start a duel") !== -1 || body.indexOf("start training") !== -1) {
            title.textContent = window.AMBITIONZ_TRAINING_MODE ? "Start the training duel" : "Start the arena duel";
            copy.textContent = "Draw your hand, choose one intent, then press Ready.";
            if (state) state.textContent = "Start";
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        bindDock();
        bindActionButtons();
        inferFromText();
    });
})();
