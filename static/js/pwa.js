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
