const CACHE_NAME = "ambition-tcg-pwa-v1";

const CORE_ASSETS = [
    "/",
    "/offline",
    "/static/css/style.css",
    "/static/icons/icon.svg",
    "/static/img/cards/placeholders/card_placeholder.svg"
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

    event.respondWith(
        fetch(event.request).catch(function () {
            return caches.match(event.request).then(function (cachedResponse) {
                return cachedResponse || caches.match("/offline");
            });
        })
    );
});
