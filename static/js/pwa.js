let deferredInstallPrompt = null;

function isStandaloneMode() {
    return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
}

function setupInstallPrompt() {
    const installButton = document.getElementById("install-app-btn");

    if (!installButton) {
        return;
    }

    if (isStandaloneMode()) {
        installButton.style.display = "none";
        return;
    }

    window.addEventListener("beforeinstallprompt", (event) => {
        event.preventDefault();
        deferredInstallPrompt = event;
        installButton.style.display = "inline-flex";
    });

    installButton.addEventListener("click", async () => {
        if (!deferredInstallPrompt) {
            alert("No Android, use o menu do navegador e toque em 'Adicionar à tela inicial'. No iPhone, use Compartilhar > Adicionar à Tela de Início.");
            return;
        }

        deferredInstallPrompt.prompt();

        const result = await deferredInstallPrompt.userChoice;

        if (result.outcome === "accepted") {
            installButton.style.display = "none";
        }

        deferredInstallPrompt = null;
    });
}

function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) {
        return;
    }

    window.addEventListener("load", async () => {
        try {
            await navigator.serviceWorker.register("/static/js/service-worker.js");
            console.log("Ambition service worker registered.");
        } catch (error) {
            console.warn("Service worker registration failed:", error);
        }
    });
}

function setupMobileViewportClass() {
    const setMode = () => {
        if (window.innerWidth <= 820) {
            document.body.classList.add("mobile-mode");
        } else {
            document.body.classList.remove("mobile-mode");
        }
    };

    setMode();
    window.addEventListener("resize", setMode);
}

function setupNetworkStatus() {
    const banner = document.getElementById("network-status-banner");

    if (!banner) {
        return;
    }

    const update = () => {
        if (navigator.onLine) {
            banner.textContent = "Online";
            banner.className = "network-banner online";
        } else {
            banner.textContent = "Offline mode";
            banner.className = "network-banner offline";
        }
    };

    window.addEventListener("online", update);
    window.addEventListener("offline", update);

    update();
}

document.addEventListener("DOMContentLoaded", () => {
    setupInstallPrompt();
    setupMobileViewportClass();
    setupNetworkStatus();
    registerServiceWorker();
});