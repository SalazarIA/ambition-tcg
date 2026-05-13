/* =========================================================
   Ambitionz Progression UI
   Enhances progression pages without changing backend logic.
   ========================================================= */

(function () {
    function isProgressionPage() {
        return [
            "/profile",
            "/campaign",
            "/daily",
            "/missions",
            "/progression",
            "/leaderboard",
            "/ranking",
            "/match-history"
        ].indexOf(window.location.pathname) !== -1;
    }

    function injectRewardToast() {
        if (!isProgressionPage()) return;
        if (document.querySelector(".az-reward-toast")) return;

        var toast = document.createElement("div");
        toast.className = "az-reward-toast";
        toast.innerHTML = "<strong>Reward Ready</strong><span>Complete missions and claim your progress.</span>";
        document.body.appendChild(toast);

        document.querySelectorAll("button, .btn").forEach(function (button) {
            var text = (button.textContent || "").toLowerCase();

            if (text.indexOf("claim") !== -1) {
                button.addEventListener("click", function () {
                    toast.classList.add("is-visible");
                    setTimeout(function () {
                        toast.classList.remove("is-visible");
                    }, 1800);
                });
            }
        });
    }

    function markMissionCards() {
        document.querySelectorAll(".progression-mission-card, .mission-card-v113, .mission-card, .progression-card").forEach(function (card) {
            card.classList.add("az-mission-card");
        });
    }

    function markTables() {
        document.querySelectorAll(".leaderboard-table, .ranking-table-v116").forEach(function (table) {
            table.classList.add("az-rank-board");
        });
    }

    function addLoopStrip() {
        if (!["/progression", "/daily", "/missions", "/campaign"].includes(window.location.pathname)) return;
        if (document.querySelector(".az-loop-strip")) return;

        var anchor = document.querySelector(".progression-hub-hero, .progression-hero, .hero-card, .deck-status");
        if (!anchor || !anchor.parentNode) return;

        var strip = document.createElement("section");
        strip.className = "az-loop-strip";
        strip.innerHTML = [
            '<article class="az-loop-step"><b>1</b><strong>Learn</strong><span>Open tutorial.</span></article>',
            '<article class="az-loop-step"><b>2</b><strong>Train</strong><span>Play BE2 bot duel.</span></article>',
            '<article class="az-loop-step"><b>3</b><strong>Review</strong><span>Read result and XP.</span></article>',
            '<article class="az-loop-step"><b>4</b><strong>Collect</strong><span>Inspect cards.</span></article>',
            '<article class="az-loop-step"><b>5</b><strong>Tune</strong><span>Validate 30 cards.</span></article>',
            '<article class="az-loop-step"><b>6</b><strong>Return</strong><span>Play again.</span></article>'
        ].join("");

        anchor.parentNode.insertBefore(strip, anchor.nextSibling);
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!isProgressionPage()) return;

        document.body.classList.add("az-progression-page");

        markMissionCards();
        markTables();
        addLoopStrip();
        injectRewardToast();
    });
})();
