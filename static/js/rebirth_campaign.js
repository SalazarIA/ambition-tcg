(function () {
    "use strict";

    function initializeCampaignCards() {
        Array.from(document.querySelectorAll("[data-campaign-node]")).forEach(function (card) {
            const action = card.querySelector("a[href]");
            if (!action) return;
            function navigate() {
                window.location.href = action.href;
            }
            card.addEventListener("click", function (event) {
                if (!event.target.closest("a, button")) navigate();
            });
            card.addEventListener("keydown", function (event) {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    navigate();
                }
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeCampaignCards);
    } else {
        initializeCampaignCards();
    }
}());
