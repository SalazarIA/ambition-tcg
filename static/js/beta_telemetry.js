/* Ambitionz public beta telemetry. Defensive, local, no external service. */
(function () {
    if (window.__ambitionzBetaTelemetryV1) return;
    window.__ambitionzBetaTelemetryV1 = true;

    var endpoint = "/api/beta/telemetry";
    var sentOnce = {};
    var knownEvents = [
        "visit_home",
        "start_training",
        "finish_match",
        "claim_daily",
        "open_shop",
        "buy_booster",
        "open_booster",
        "save_deck",
        "view_collection",
        "view_roadmap",
        "dismiss_first_session_quest"
    ];
    var pathEvents = {
        "/": "visit_home",
        "/collection": "view_collection",
        "/roadmap": "view_roadmap",
        "/shop": "open_shop"
    };

    function safeMeta(metadata) {
        var result = {};
        if (!metadata || typeof metadata !== "object") return result;
        Object.keys(metadata).slice(0, 20).forEach(function (key) {
            var value = metadata[key];
            result[String(key).slice(0, 80)] = String(value == null ? "" : value).slice(0, 220);
        });
        return result;
    }

    function send(eventName, metadata, onceKey) {
        try {
            if (!eventName) return;
            if (onceKey && sentOnce[onceKey]) return;
            if (onceKey) sentOnce[onceKey] = true;

            var payload = {
                event: eventName,
                page: window.location.pathname || "/",
                source: "browser",
                metadata: safeMeta(metadata || {})
            };
            var body = JSON.stringify(payload);

            if (navigator.sendBeacon) {
                navigator.sendBeacon(endpoint, new Blob([body], { type: "application/json" }));
                return;
            }

            if (window.fetch) {
                fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    credentials: "same-origin",
                    body: body,
                    keepalive: true
                }).catch(function () {});
            }
        } catch (error) {}
    }

    function textOf(element) {
        return ((element && (element.innerText || element.textContent)) || "").trim().slice(0, 90);
    }

    function bindActions() {
        document.querySelectorAll("[data-beta-telemetry]").forEach(function (element) {
            element.addEventListener("click", function () {
                send(element.getAttribute("data-beta-telemetry"), {
                    label: textOf(element),
                    href: element.getAttribute("href") || ""
                });
            }, { passive: true });
        });

        document.querySelectorAll("[data-retention-event='training_start_click'], #az48-floating-start, #az48-start").forEach(function (element) {
            element.addEventListener("click", function () {
                send("start_training", { label: textOf(element) });
            }, { passive: true });
        });

        document.querySelectorAll("[data-shop-purchase-form]").forEach(function (form) {
            form.addEventListener("submit", function () {
                send("buy_booster", { action: form.getAttribute("action") || "/shop" });
            });
        });

        document.querySelectorAll("#az-deck-builder-form, form[data-retention-event='deck_save_attempt']").forEach(function (form) {
            form.addEventListener("submit", function () {
                send("save_deck", { action: form.getAttribute("action") || "/deck-builder" });
            });
        });

        document.querySelectorAll("form[action$='/daily/claim'], [data-retention-event='daily_claim']").forEach(function (element) {
            element.addEventListener("submit", function () {
                send("claim_daily", { source: "daily_form" }, "claim_daily_submit");
            });
            element.addEventListener("click", function () {
                send("claim_daily", { source: "daily_click" }, "claim_daily_click");
            }, { passive: true });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        var path = window.location.pathname || "/";
        var pageEvent = pathEvents[path];
        if (pageEvent) send(pageEvent, { auto: "page_view" }, "page:" + pageEvent);

        if (document.querySelector(".booster-result-v124, .is-booster-result-card")) {
            send("open_booster", { source: "booster_result" }, "open_booster_result");
        }

        bindActions();
    });

    window.AmbitionzBetaTelemetry = {
        track: send,
        knownEvents: knownEvents.slice()
    };
})();
