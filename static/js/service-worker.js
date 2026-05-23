const CACHE_NAME = "ambitionz-rebirth-season0-v57";

const CORE_ASSETS = [
    "/",
    "/rebirth",
    "/rebirth/account",
    "/rebirth/collection",
    "/rebirth/shop",
    "/rebirth/progression",
    "/rebirth/profile",
    "/rebirth/lab",
    "/manifest.webmanifest",
    "/static/manifest.webmanifest",
    "/static/css/rebirth.css",
    "/static/js/rebirth.js",
    "/static/js/rebirth_global.js",
    "/static/js/rebirth_product.js",
    "/static/js/pwa.js",
    "/static/assets/rebirth/manifest.json",
    "/static/assets/rebirth/cards/dreadclaw-art.png",
    "/static/assets/rebirth/cards/dreadmaw-art.png",
    "/static/assets/rebirth/cards/stoneshell-art.png",
    "/static/assets/rebirth/cards/stonewarden-art.png",
    "/static/assets/rebirth/cards/shadewisp-art.png",
    "/static/assets/rebirth/cards/skywarden-art.png",
    "/static/assets/rebirth/cards/stormwarden-art.png",
    "/static/assets/rebirth/cards/ironbastion-art.png",
    "/static/assets/rebirth/cards/ironbulwark-art.png",
    "/static/assets/rebirth/cards/embermaw-art.png",
    "/static/assets/rebirth/cards/embermaw-alpha-art.png",
    "/static/assets/rebirth/cards/voidstalker-art.png",
    "/static/assets/rebirth/cards/nightfang-art.png",
    "/static/assets/rebirth/ui/bot-card-back.png",
    "/static/assets/rebirth/ui/bot-emblem.png",
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

self.addEventListener("message", function (event) {
    if (event.data && event.data.type === "SKIP_WAITING") {
        self.skipWaiting();
    }
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
