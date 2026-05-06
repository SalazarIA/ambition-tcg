/* =========================================================
   Ambitionz Booster Opening Animation
   Visual only, works with existing POST flow.
   ========================================================= */

(function () {
    function qs(selector) {
        return document.querySelector(selector);
    }

    function playSound(name, payload) {
        try {
            if (window.AmbitionzSound && window.AmbitionzSound.play) {
                window.AmbitionzSound.play(name, payload || {});
            }
        } catch (err) {}
    }

    function bindBoosterForms() {
        document.querySelectorAll("[data-booster-open-form]").forEach((form) => {
            if (form.dataset.bound === "1") return;

            form.dataset.bound = "1";

            form.addEventListener("submit", (event) => {
                const stage = qs("#az-booster-stage");

                if (!stage) return;

                event.preventDefault();

                stage.classList.add("is-opening");
                playSound("cardFly", { element: "Global" });

                const button = form.querySelector("button[type='submit']");
                if (button) {
                    button.disabled = true;
                    button.textContent = "Opening...";
                }

                setTimeout(() => {
                    form.submit();
                }, 720);
            });
        });
    }

    document.addEventListener("DOMContentLoaded", bindBoosterForms);
})();
