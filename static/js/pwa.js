(function () {
    let deferredPrompt = null;

    const banner = document.getElementById("network-status-banner");

    function setNetworkStatus() {
        if (!banner) {
            return;
        }

        if (navigator.onLine) {
            banner.textContent = "Online";
            banner.classList.remove("offline");
            banner.classList.add("online");
        } else {
            banner.textContent = "Offline";
            banner.classList.remove("online");
            banner.classList.add("offline");
        }
    }

    window.addEventListener("online", setNetworkStatus);
    window.addEventListener("offline", setNetworkStatus);
    setNetworkStatus();

    window.addEventListener("beforeinstallprompt", function (event) {
        event.preventDefault();
        deferredPrompt = event;

        const installButton = document.getElementById("install-app-btn");

        if (installButton) {
            installButton.style.display = "inline-flex";
        }
    });

    window.installAmbitionPWA = async function () {
        if (!deferredPrompt) {
            alert("On iPhone, install through Safari: Share > Add to Home Screen.");
            return;
        }

        deferredPrompt.prompt();

        try {
            await deferredPrompt.userChoice;
        } finally {
            deferredPrompt = null;
        }
    };

    document.addEventListener("DOMContentLoaded", function () {
        const installButton = document.getElementById("install-app-btn");

        if (installButton) {
            installButton.addEventListener("click", window.installAmbitionPWA);
        }

        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (
            navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1
        );

        const isStandalone =
            window.navigator.standalone === true ||
            window.matchMedia("(display-mode: standalone)").matches;

        const iosTip = document.getElementById("ios-install-tip");

        if (iosTip && isIOS && !isStandalone) {
            iosTip.style.display = "block";
        }
    });

    if ("serviceWorker" in navigator) {
        window.addEventListener("load", function () {
            navigator.serviceWorker.register("/static/js/service-worker.js").catch(function () {
                // Silent fail during local or restricted environments.
            });
        });
    }
})();


// ==========================================================================
// AMBITIONZ V1.40B — MOBILE TAP / LOADING FEEDBACK
// ==========================================================================

(function () {
    if (window.__ambitionzMobileTapV140B) {
        return;
    }

    window.__ambitionzMobileTapV140B = true;

    function createLoadingPill(label) {
        try {
            var existing = document.querySelector(".az-page-loading-pill-v140b");
            if (existing) {
                existing.remove();
            }

            var pill = document.createElement("div");
            pill.className = "az-page-loading-pill-v140b";
            pill.textContent = label || "Loading...";
            document.body.appendChild(pill);

            window.setTimeout(function () {
                if (pill && pill.parentNode) {
                    pill.parentNode.removeChild(pill);
                }
            }, 1600);
        } catch (error) {}
    }

    function markBusy(element) {
        try {
            if (!element) {
                return;
            }

            element.classList.add("az-loading-tap-v140b");
            element.setAttribute("aria-busy", "true");

            window.setTimeout(function () {
                element.classList.remove("az-loading-tap-v140b");
                element.removeAttribute("aria-busy");
            }, 1800);
        } catch (error) {}
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("a[href]").forEach(function (link) {
            link.addEventListener("click", function () {
                var href = link.getAttribute("href") || "";

                if (
                    href &&
                    href.indexOf("#") !== 0 &&
                    href.indexOf("javascript:") !== 0 &&
                    !link.target
                ) {
                    markBusy(link);
                    createLoadingPill("Opening...");
                }
            }, { passive: true });
        });

        document.querySelectorAll("form").forEach(function (form) {
            form.addEventListener("submit", function () {
                var submit = form.querySelector("button[type=submit], button:not([type]), .btn");

                if (submit) {
                    markBusy(submit);
                }

                createLoadingPill("Sending...");
            });
        });
    });
})();
