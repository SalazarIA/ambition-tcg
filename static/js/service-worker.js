const CACHE_NAME = "ambition-tcg-beta-v1";

const STATIC_ASSETS = [
    "/",
    "/offline",
    "/static/css/style.css",
    "/static/js/pwa.js",
    "/static/js/game.js",
    "/static/manifest.webmanifest",
    "/static/icons/icon.svg",
    "/static/img/cards/placeholders/card_placeholder.svg"
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );

    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((cacheName) => cacheName !== CACHE_NAME)
                    .map((cacheName) => caches.delete(cacheName))
            );
        })
    );

    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    const request = event.request;

    if (request.method !== "GET") {
        return;
    }

    const url = new URL(request.url);

    if (url.pathname.includes("/socket.io/")) {
        return;
    }

    event.respondWith(
        fetch(request)
            .then((response) => {
                const responseClone = response.clone();

                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(request, responseClone);
                });

                return response;
            })
            .catch(async () => {
                const cachedResponse = await caches.match(request);

                if (cachedResponse) {
                    return cachedResponse;
                }

                if (request.headers.get("accept")?.includes("text/html")) {
                    return caches.match("/offline");
                }

                return new Response("Offline", {
                    status: 503,
                    statusText: "Offline"
                });
            })
    );
});