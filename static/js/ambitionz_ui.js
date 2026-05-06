/* =========================================================
   Ambitionz Global UI
   Small progressive enhancements for non-arena pages.
   ========================================================= */

(function () {
    function isArenaPage() {
        return window.location.pathname === "/training" || window.location.pathname === "/arena";
    }

    function enhancePage() {
        if (isArenaPage()) return;

        document.body.classList.add("az-themed-page");

        document.querySelectorAll(".btn, button").forEach(function (el) {
            if (!el.dataset.azEnhanced) {
                el.dataset.azEnhanced = "1";
            }
        });

        document.querySelectorAll(".collection-card, .menu-card, .progression-card, .deck-status, .panel-card").forEach(function (el, index) {
            el.style.setProperty("--az-card-delay", Math.min(index * 22, 240) + "ms");
        });
    }

    document.addEventListener("DOMContentLoaded", enhancePage);
})();
