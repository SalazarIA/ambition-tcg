(function () {
    "use strict";

    if (!("serviceWorker" in navigator)) {
        return;
    }

    function showUpdatePrompt(registration) {
        if (!registration || !registration.waiting || document.querySelector("[data-rebirth-update]")) {
            return;
        }
        const prompt = document.createElement("button");
        prompt.type = "button";
        prompt.className = "rb-update-prompt";
        prompt.setAttribute("data-rebirth-update", "");
        prompt.textContent = "Update Rebirth";
        prompt.addEventListener("click", function () {
            prompt.disabled = true;
            registration.waiting.postMessage({ type: "SKIP_WAITING" });
        });
        document.body.appendChild(prompt);
    }

    window.addEventListener("load", function () {
        navigator.serviceWorker.register("/service-worker.js", { scope: "/" })
            .then(function (registration) {
                showUpdatePrompt(registration);
                registration.addEventListener("updatefound", function () {
                    const installing = registration.installing;
                    if (!installing) {
                        return;
                    }
                    installing.addEventListener("statechange", function () {
                        if (installing.state === "installed" && navigator.serviceWorker.controller) {
                            showUpdatePrompt(registration);
                        }
                    });
                });
            })
            .catch(function () {
                return undefined;
            });
    });

    navigator.serviceWorker.addEventListener("controllerchange", function () {
        window.location.reload();
    });
})();
