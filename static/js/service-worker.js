const CACHE_NAME = "ambitionz-rebirth-clash-ui-v2";

const CORE_ASSETS = [
    "/",
    "/rebirth",
    "/manifest.webmanifest",
    "/static/manifest.webmanifest",
    "/static/css/rebirth.css",
    "/static/js/rebirth.js",
    "/static/js/pwa.js",
    "/static/assets/rebirth/cards/dreadclaw.svg",
    "/static/assets/rebirth/cards/stoneshell.svg",
    "/static/assets/rebirth/cards/shadewisp.svg",
    "/static/assets/rebirth/cards/skywarden.svg",
    "/static/assets/rebirth/cards/ironbastion.svg",
    "/static/assets/rebirth/cards/embermaw.svg",
    "/static/assets/rebirth/cards/voidstalker.svg",
    "/static/assets/rebirth/cards/nightfang.svg",
    "/static/icons/icon.svg",
    "/static/icons/icon-192.png",
    "/static/icons/icon-512.png"
];

self.addEventListener("install", function (event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function (cache) {
            return cache.addAll(CORE_ASSETS).catch(function () {
                return Promise.resolve();
            });
        })
    );
    self.skipWaiting();
});

self.addEventListener("activate", function (event) {
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(
                keys
                    .filter(function (key) {
                        return key !== CACHE_NAME;
                    })
                    .map(function (key) {
                        return caches.delete(key);
                    })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener("fetch", function (event) {
    if (event.request.method !== "GET") {
        return;
    }

    const url = new URL(event.request.url);
    if (url.pathname.startsWith("/api/")) {
        return;
    }

    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request).catch(function () {
                return caches.match("/rebirth");
            })
        );
        return;
    }

    event.respondWith(
        caches.match(event.request).then(function (cached) {
            return cached || fetch(event.request).then(function (response) {
                if (response && response.ok && url.origin === self.location.origin) {
                    const copy = response.clone();
                    caches.open(CACHE_NAME).then(function (cache) {
                        cache.put(event.request, copy);
                    });
                }
                return response;
            });
        })
    );
});
