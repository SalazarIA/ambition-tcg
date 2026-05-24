const CACHE_NAME = "v59_COMBAT_REWORK";

// Keep authentication, wallet, profile and loadout HTML network-owned. Only
// immutable presentation resources belong in the install cache. v59: added
// `auth` and `loadout` to the player-state deny list explicitly. They used
// to pass via the catch-all `/api/` branch in the fetch handler, but making
// them PLAYER_STATE_API_DENY_RE matches keeps intent obvious for future
// refactors that might broaden the cacheable surface. `tutorial` added to
// the dynamic deny list because tutorial reward grants are economy-grade
// transactions and must never be served from cache.
const PLAYER_STATE_API_DENY_RE = /^\/api\/(?:rebirth\/)?(?:wallet|profile|market|auth|loadout)(?:\/|$)/;
const DYNAMIC_REBIRTH_API_DENY_RE = /^\/api\/rebirth\/(?:session|progression|collection|match-history|economy-ledger|onboarding|tutorial)(?:\/|$)/;
const FALLBACK_WEBP_ART_RE = /^\/static\/assets\/rebirth\/cards\/dreadclaw-art\.webp$/;
const CORE_ASSETS = [
    "/manifest.webmanifest",
    "/static/manifest.webmanifest",
    "/static/css/rebirth.css",
    "/static/js/rebirth.js",
    "/static/js/rebirth_global.js",
    "/static/js/rebirth_product.js",
    "/static/js/pwa.js",
    "/static/assets/rebirth/manifest.json",
    "/static/assets/rebirth/cards/dreadclaw-art.webp",
    "/static/assets/rebirth/ui/bot-card-back.png",
    "/static/assets/rebirth/ui/bot-emblem.png",
    "/static/icons/icon.svg",
    "/static/icons/icon-192.png",
    "/static/icons/icon-512.png"
];
const CORE_ASSET_SET = new Set(CORE_ASSETS);

function isPlayerStateRequest(url) {
    return PLAYER_STATE_API_DENY_RE.test(url.pathname) || DYNAMIC_REBIRTH_API_DENY_RE.test(url.pathname);
}

function isCacheableAppShellRequest(url) {
    if (url.origin !== self.location.origin) {
        return false;
    }
    return CORE_ASSET_SET.has(url.pathname) || FALLBACK_WEBP_ART_RE.test(url.pathname);
}

self.addEventListener("install", function (event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function (cache) {
            return cache.addAll(CORE_ASSETS);
        })
    );
    self.skipWaiting();
});

self.addEventListener("activate", function (event) {
    self.skipWaiting();
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(
                keys
                    .filter(function (key) {
                        return key.startsWith("ambitionz-rebirth-") && key !== CACHE_NAME;
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
    if (isPlayerStateRequest(url) || url.pathname.startsWith("/api/") || event.request.mode === "navigate") {
        event.respondWith(fetch(event.request));
        return;
    }

    if (!isCacheableAppShellRequest(url)) {
        return;
    }

    event.respondWith(
        caches.open(CACHE_NAME).then(function (cache) {
            return cache.match(event.request).then(function (cached) {
                const network = fetch(event.request).then(function (response) {
                    if (response && response.ok) {
                        cache.put(event.request, response.clone());
                    }
                    return response;
                });
                return cached || network;
            });
        })
    );
});
