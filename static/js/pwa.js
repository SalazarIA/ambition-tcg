(function () {
    let deferredPrompt = null;

    const INSTALL_SNOOZE_KEY = "ambitionzInstallPromptHiddenUntil";
    const INSTALL_ACCEPTED_KEY = "ambitionzInstallAccepted";

    function isStandaloneMode() {
        return window.navigator.standalone === true ||
            window.matchMedia("(display-mode: standalone)").matches;
    }

    function isIOSDevice() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) || (
            navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1
        );
    }

    function isMobileDevice() {
        return window.matchMedia("(max-width: 820px)").matches ||
            /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    }

    function promptIsSnoozed() {
        const hiddenUntil = Number(localStorage.getItem(INSTALL_SNOOZE_KEY) || 0);
        return hiddenUntil > Date.now() || localStorage.getItem(INSTALL_ACCEPTED_KEY) === "true";
    }

    function createNetworkBanner() {
        let banner = document.getElementById("network-status-banner");

        if (!banner) {
            banner = document.createElement("div");
            banner.id = "network-status-banner";
            banner.className = "network-banner";
            banner.setAttribute("aria-live", "polite");
            document.body.appendChild(banner);
        }

        return banner;
    }

    function setNetworkStatus() {
        const banner = createNetworkBanner();

        if (navigator.onLine) {
            banner.textContent = "Online";
            banner.classList.remove("offline");
            banner.classList.add("online");
        } else {
            banner.textContent = "Offline mode";
            banner.classList.remove("online");
            banner.classList.add("offline");
        }
    }

    function createInstallPanel() {
        let panel = document.getElementById("pwa-install-panel");

        if (panel) {
            return panel;
        }

        panel = document.createElement("aside");
        panel.id = "pwa-install-panel";
        panel.className = "pwa-install-panel-v155";
        panel.setAttribute("aria-live", "polite");
        panel.innerHTML = [
            '<img src="/static/icons/icon-192.png" alt="" class="pwa-install-icon-v155">',
            '<div class="pwa-install-copy-v155">',
            "<strong>Install Ambitionz</strong>",
            "<span>Play from your home screen, fullscreen and faster to open.</span>",
            '<small class="pwa-ios-copy-v155">iPhone: use Safari, Share, then Add to Home Screen.</small>',
            "</div>",
            '<div class="pwa-install-actions-v155">',
            '<button type="button" id="install-app-btn" class="btn small-btn">Install</button>',
            '<button type="button" id="dismiss-install-app-btn" class="btn btn-secondary small-btn">Later</button>',
            "</div>"
        ].join("");

        document.body.appendChild(panel);

        panel.querySelector("#install-app-btn").addEventListener("click", window.installAmbitionPWA);
        panel.querySelector("#dismiss-install-app-btn").addEventListener("click", function () {
            localStorage.setItem(INSTALL_SNOOZE_KEY, String(Date.now() + 7 * 24 * 60 * 60 * 1000));
            hideInstallPanel();
        });

        return panel;
    }

    function showInstallPanel() {
        if (isStandaloneMode() || promptIsSnoozed()) {
            return;
        }

        if (document.body && document.body.classList.contains("arena-page-v154")) {
            return;
        }

        if (!deferredPrompt && !isIOSDevice()) {
            return;
        }

        const panel = createInstallPanel();
        panel.classList.add("is-visible-v155");
        panel.classList.toggle("is-ios-v155", isIOSDevice());
    }

    function hideInstallPanel() {
        const panel = document.getElementById("pwa-install-panel");

        if (panel) {
            panel.classList.remove("is-visible-v155");
        }
    }

    window.addEventListener("online", setNetworkStatus);
    window.addEventListener("offline", setNetworkStatus);

    window.addEventListener("beforeinstallprompt", function (event) {
        event.preventDefault();
        deferredPrompt = event;

        if (isMobileDevice()) {
            showInstallPanel();
        }
    });

    window.addEventListener("appinstalled", function () {
        localStorage.setItem(INSTALL_ACCEPTED_KEY, "true");
        deferredPrompt = null;
        hideInstallPanel();
    });

    window.installAmbitionPWA = async function () {
        if (!deferredPrompt) {
            const message = "iPhone install: open Safari, tap Share, then Add to Home Screen.";
            const status = document.getElementById("queue-status");

            if (status) {
                status.textContent = message;
            } else {
                console.info(message);
            }

            return;
        }

        deferredPrompt.prompt();

        try {
            const result = await deferredPrompt.userChoice;

            if (result && result.outcome === "accepted") {
                localStorage.setItem(INSTALL_ACCEPTED_KEY, "true");
                hideInstallPanel();
            }
        } finally {
            deferredPrompt = null;
        }
    };

    document.addEventListener("DOMContentLoaded", function () {
        setNetworkStatus();

        if (isMobileDevice() && isIOSDevice() && !isStandaloneMode()) {
            window.setTimeout(showInstallPanel, 900);
        }
    });

    if ("serviceWorker" in navigator) {
        window.addEventListener("load", function () {
            navigator.serviceWorker.register("/service-worker.js", { scope: "/" }).catch(function () {
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


// ==========================================================================
// AMBITIONZ V1.41B — FRONTEND BETA EVENT ANALYTICS
// ==========================================================================

(function () {
    if (window.__ambitionzBetaAnalyticsV141B) {
        return;
    }

    window.__ambitionzBetaAnalyticsV141B = true;

    function sendBetaEvent(eventName, extra) {
        try {
            var payload = {
                event: eventName || "unknown_event",
                path: window.location.pathname || "/",
                source: "android_webview_or_browser",
                title: document.title || "",
                width: String(window.innerWidth || ""),
                height: String(window.innerHeight || ""),
                ts: new Date().toISOString()
            };

            if (extra && typeof extra === "object") {
                Object.keys(extra).forEach(function (key) {
                    payload[key] = String(extra[key]).slice(0, 180);
                });
            }

            var body = JSON.stringify(payload);

            if (navigator.sendBeacon) {
                var blob = new Blob([body], { type: "application/json" });
                navigator.sendBeacon("/api/beta-event", blob);
                return;
            }

            fetch("/api/beta-event", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: body,
                keepalive: true
            }).catch(function () {});
        } catch (error) {}
    }

    document.addEventListener("DOMContentLoaded", function () {
        sendBetaEvent("page_view");

        document.querySelectorAll("a[href]").forEach(function (link) {
            link.addEventListener("click", function () {
                var href = link.getAttribute("href") || "";
                var label = (link.innerText || link.textContent || "").trim().slice(0, 80);

                sendBetaEvent("action_link_click", {
                    href: href,
                    label: label
                });
            }, { passive: true });
        });

        document.querySelectorAll("form").forEach(function (form) {
            form.addEventListener("submit", function () {
                sendBetaEvent("form_submit", {
                    action: form.getAttribute("action") || window.location.pathname || "",
                    method: form.getAttribute("method") || "GET"
                });
            });
        });

        window.addEventListener("pagehide", function () {
            sendBetaEvent("page_hide");
        });
    });
})();


(function () {
    var pageEventMap = {
        "/campaign": "campaign_view",
        "/collection": "collection_view",
        "/daily": "daily_view",
        "/deck-builder": "deck_builder_view"
    };

    function trackRetentionEvent(eventKey, metadata) {
        try {
            if (!window.fetch) return;

            fetch("/api/retention/event", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    event_key: eventKey,
                    page: window.location.pathname,
                    metadata: metadata || {}
                })
            }).catch(function () {});
        } catch (err) {}
    }

    window.AmbitionzRetention = {
        track: trackRetentionEvent
    };

    document.addEventListener("DOMContentLoaded", function () {
        var page = document.body ? document.body.getAttribute("data-retention-page") : null;
        var path = window.location.pathname || "";
        var pageEvent = pageEventMap[path];

        trackRetentionEvent("page_view", {
            page: page || path,
            standalone: window.matchMedia && window.matchMedia("(display-mode: standalone)").matches
        });

        if (pageEvent) {
            trackRetentionEvent(pageEvent, {
                page: page || path,
                source: "auto_page_view"
            });
        }

        document.querySelectorAll("a[href], button").forEach(function (el) {
            el.addEventListener("click", function () {
                var label = (el.textContent || "").trim().slice(0, 80);
                var href = el.getAttribute("href") || "";
                var eventTarget = el.closest("[data-retention-event]");

                if (eventTarget) {
                    trackRetentionEvent(eventTarget.getAttribute("data-retention-event"), {
                        label: label,
                        href: href
                    });
                }

                trackRetentionEvent("ui_click", {
                    label: label,
                    href: href
                });
            });
        });

        document.querySelectorAll("form[data-retention-event]").forEach(function (form) {
            form.addEventListener("submit", function () {
                trackRetentionEvent(form.getAttribute("data-retention-event"), {
                    action: form.getAttribute("action") || path,
                    method: form.getAttribute("method") || "POST"
                });
            });
        });
    });
})();



// PWA_FORCE_UPDATE_V1
if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.getRegistration().then(function (registration) {
      if (registration) {
        registration.update();
      }
    }).catch(function () {});
  });
}
