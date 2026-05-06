/* =========================================================
   Ambitionz Progression UI
   Enhances progression pages without changing backend logic.
   ========================================================= */

(function () {
    function isProgressionPage() {
        return [
            "/profile",
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
        if (!["/progression", "/daily", "/missions"].includes(window.location.pathname)) return;
        if (document.querySelector(".az-loop-strip")) return;

        var anchor = document.querySelector(".progression-hub-hero, .progression-hero, .hero-card, .deck-status");
        if (!anchor || !anchor.parentNode) return;

        var strip = document.createElement("section");
        strip.className = "az-loop-strip";
        strip.innerHTML = [
            '<article class="az-loop-step"><b>1</b><strong>Play</strong><span>Enter a duel.</span></article>',
            '<article class="az-loop-step"><b>2</b><strong>Earn</strong><span>Gain XP and coins.</span></article>',
            '<article class="az-loop-step"><b>3</b><strong>Claim</strong><span>Complete missions.</span></article>',
            '<article class="az-loop-step"><b>4</b><strong>Open</strong><span>Use boosters.</span></article>',
            '<article class="az-loop-step"><b>5</b><strong>Improve</strong><span>Upgrade deck identity.</span></article>',
            '<article class="az-loop-step"><b>6</b><strong>Climb</strong><span>Rise in ranking.</span></article>'
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
