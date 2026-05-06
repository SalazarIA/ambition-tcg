/* =========================================================
   Ambitionz Card System JS
   Adds progressive interaction to card grids.
   ========================================================= */

(function () {
    function isArenaPage() {
        return window.location.pathname === "/training" || window.location.pathname === "/arena";
    }

    function enhanceCards() {
        if (isArenaPage()) return;

        document.querySelectorAll(".collection-card, .image-card").forEach(function (card, index) {
            card.dataset.azCard = "1";
            card.style.setProperty("--az-card-index", index);

            if (!card.getAttribute("tabindex")) {
                card.setAttribute("tabindex", "0");
            }

            card.addEventListener("keydown", function (event) {
                if (event.key === "Enter" || event.key === " ") {
                    var button = card.querySelector("button, a, input");
                    if (button) {
                        event.preventDefault();
                        button.click();
                    }
                }
            });
        });

        document.querySelectorAll(".card-grid, .deck-builder-grid, .mobile-card-grid").forEach(function (grid) {
            grid.classList.add("az-card-grid");
        });
    }

    document.addEventListener("DOMContentLoaded", enhanceCards);
})();
