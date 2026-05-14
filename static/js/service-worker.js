const CACHE_NAME = "ambitionz-web-app-v185";

const CORE_ASSETS = [
    "/",
    "/offline",
    "/static/manifest.webmanifest",
    "/static/css/style.css",
    "/static/css/arena_clean_v48.css",
    "/static/css/arena3d.css",
    "/static/js/pwa.js",
    "/static/js/arena_renderer_adapter.js",
    "/static/js/arena_clean_v48.js",
    "/static/js/arena_sound.js",
    "/static/dist/arena3d/arena3d.js",
    "/static/assets/arena3d/manifest.json",
    "/static/icons/icon.svg",
    "/static/icons/icon-192.png",
    "/static/icons/icon-512.png",
    "/static/icons/maskable-icon-192.png",
    "/static/icons/maskable-icon-512.png",
    "/static/icons/apple-touch-icon.png"
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

    const requestUrl = new URL(event.request.url);

    if (
        requestUrl.pathname.startsWith("/socket.io/") ||
        requestUrl.pathname.startsWith("/api/")
    ) {
        return;
    }

    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request).catch(function () {
                return caches.match("/offline");
            })
        );
        return;
    }

    event.respondWith(
        caches.match(event.request).then(function (cachedResponse) {
            const networkFetch = fetch(event.request).then(function (networkResponse) {
                if (networkResponse && networkResponse.ok && requestUrl.origin === self.location.origin) {
                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then(function (cache) {
                        cache.put(event.request, responseClone);
                    });
                }

                return networkResponse;
            }).catch(function () {
                return cachedResponse || caches.match("/offline");
            });

            return cachedResponse || networkFetch;
        })
    );
});
