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
            "/match-history",
            "/roadmap",
            "/feedback",
            "/shop",
            "/booster-history",
            "/"
        ].indexOf(window.location.pathname) !== -1;
    }

    function injectRewardToast() {
        if (!isProgressionPage()) return;
        if (document.querySelector(".az-reward-toast")) return;

        var toast = document.createElement("div");
        toast.className = "az-reward-toast";
        toast.innerHTML = "<strong>Reward Ready</strong><span>Complete missions, claim Gold and open boosters.</span>";
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

    function todayKey() {
        var now = new Date();
        return now.getFullYear() + "-" + String(now.getMonth() + 1).padStart(2, "0") + "-" + String(now.getDate()).padStart(2, "0");
    }

    function updateDailyRewardCards() {
        var cards = document.querySelectorAll("[data-daily-reward-card]");
        if (!cards.length) return;

        var key = "ambitionz_daily_reward_claimed_v1";
        var today = todayKey();
        var localClaimed = false;

        try {
            localClaimed = window.localStorage.getItem(key) === today;
        } catch (error) {
            localClaimed = false;
        }

        cards.forEach(function (card) {
            var serverState = card.dataset.dailyState || "preview";
            var claimed = serverState === "claimed" || localClaimed;
            var title = card.querySelector("[data-daily-reward-title]");
            var copy = card.querySelector("[data-daily-reward-copy]");

            card.classList.toggle("is-claimed", claimed);
            card.classList.toggle("is-available", !claimed && serverState !== "preview");

            if (claimed && title) title.textContent = "Collected Today";
            if (claimed && copy) copy.textContent = "Next Gold reward tomorrow. Play Training to progress missions now.";
        });
    }

    function bindLocalDailyReward() {
        document.querySelectorAll("[data-local-daily-claim]").forEach(function (button) {
            button.addEventListener("click", function () {
                try {
                    window.localStorage.setItem("ambitionz_daily_reward_claimed_v1", todayKey());
                } catch (error) {}

                button.disabled = true;
                button.textContent = "Preview Claimed";
                updateDailyRewardCards();
            });
        });
    }

    function bindPublicOnboarding() {
        var panel = document.querySelector("[data-public-onboarding]");
        if (!panel) return;

        var key = "ambitionz_public_onboarding_seen_v1";
        var dismissed = false;

        try {
            dismissed = window.localStorage.getItem(key) === "true";
        } catch (error) {
            dismissed = false;
        }

        if (dismissed) {
            panel.classList.add("is-collapsed");
            panel.setAttribute("aria-label", "Public beta onboarding completed");
        }

        document.querySelectorAll("[data-public-onboarding-dismiss]").forEach(function (button) {
            button.addEventListener("click", function () {
                try {
                    window.localStorage.setItem(key, "true");
                } catch (error) {}

                panel.classList.add("is-collapsed");
                button.textContent = "Onboarding salvo";
            });
        });
    }

    function bindFirstSessionQuestline() {
        var panels = document.querySelectorAll("[data-first-session-questline]");
        if (!panels.length) return;

        panels.forEach(function (panel) {
            var key = panel.getAttribute("data-dismiss-key") || "ambitionz_first_session_questline_dismissed_v1";
            var dismissed = false;

            try {
                dismissed = window.localStorage.getItem(key) === "true";
            } catch (error) {
                dismissed = false;
            }

            if (dismissed) {
                panel.classList.add("is-dismissed");
            }

            panel.querySelectorAll("[data-first-session-dismiss]").forEach(function (button) {
                button.addEventListener("click", function () {
                    try {
                        window.localStorage.setItem(key, "true");
                    } catch (error) {}

                    panel.classList.add("is-dismissed");
                    button.textContent = "Questline hidden";
                });
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!isProgressionPage()) return;

        document.body.classList.add("az-progression-page");

        markMissionCards();
        markTables();
        addLoopStrip();
        bindLocalDailyReward();
        updateDailyRewardCards();
        bindPublicOnboarding();
        bindFirstSessionQuestline();
        injectRewardToast();
    });
})();
