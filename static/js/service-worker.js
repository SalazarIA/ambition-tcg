const CACHE_NAME = "v66_EVENT_AUDIO";
const REBIRTH_CACHE_RE = /^(?:ambitionz-rebirth(?:[-_].*)?|rebirth(?:[-_].*)?|v\d+_(?:COMBAT_REWORK|EVENT_AUDIO)(?:$|-))/i;

function stableAsset(path) {
    return `${path}?v=${CACHE_NAME}`;
}

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
    stableAsset("/static/css/rebirth.css"),
    stableAsset("/static/js/rebirth.js"),
    stableAsset("/static/js/rebirth_audio.js"),
    stableAsset("/static/js/rebirth_global.js"),
    stableAsset("/static/js/rebirth_product.js"),
    stableAsset("/static/js/pwa.js"),
    "/static/assets/rebirth/manifest.json",
    "/static/assets/rebirth/audio/impact_heavy.wav",
    "/static/assets/rebirth/audio/shield_shatter.wav",
    "/static/assets/rebirth/audio/evolution_burst.wav",
    "/static/assets/rebirth/audio/click_metallic.wav",
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
    return CORE_ASSET_SET.has(`${url.pathname}${url.search}`) || FALLBACK_WEBP_ART_RE.test(url.pathname);
}

function pruneActiveCache() {
    return caches.open(CACHE_NAME).then(function (cache) {
        return cache.keys().then(function (requests) {
            return Promise.all(
                requests
                    .filter(function (request) {
                        return !isCacheableAppShellRequest(new URL(request.url));
                    })
                    .map(function (request) {
                        return cache.delete(request);
                    })
            );
        });
    });
}

self.addEventListener("install", function (event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function (cache) {
            return cache.addAll(CORE_ASSETS);
        }).then(function () {
            return self.skipWaiting();
        })
    );
});

self.addEventListener("activate", function (event) {
    event.waitUntil(
        Promise.all([
            self.skipWaiting(),
            caches.keys().then(function (keys) {
                return Promise.all(
                    keys
                        .filter(function (key) {
                            return key !== CACHE_NAME && REBIRTH_CACHE_RE.test(key);
                        })
                        .map(function (key) {
                            return caches.delete(key);
                        })
                );
            }),
            pruneActiveCache()
        ]).then(function () {
            return self.clients.claim();
        })
    );
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
