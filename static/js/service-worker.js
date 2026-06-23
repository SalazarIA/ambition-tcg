const ASSET_VERSION = "v113_MECHANICS_GUIDE";
const CACHE_NAME = `ambitionz-rebirth-shell-${ASSET_VERSION}`;
const REBIRTH_CACHE_RE = /^(?:ambitionz-rebirth(?:[-_].*)?|rebirth(?:[-_].*)?|v\d+_(?:COMBAT_REWORK|EVENT_AUDIO|PRODUCT_FLOW|PRODUCT_READINESS|FIRST_DUEL|CAMPAIGN(?:_V\d+|_ERA)?|RELEASE_POLISH|EMAIL_VERIFY|ART_FOUNDATION|ART_PERSONALITY|FULLSCREEN|DOC_REBIRTH|DOC_LAYOUT|DOC_POLISH|LAUNCH|KEYWORDS|DECK_BUILDER|BATTLEFIELD|ARENA_ZEN|FATES_REBORN|FATES_FIX|NO_TABLE|GAME_FEEL_PASS|CORE_LOOP_STABILIZATION|MOBILE_WEB_FIX|AAA_RULES_PASS|ARENA_FEEL|VISUAL_UNITY|PLAYER_FIRST|PERF_STUDY|YGO_POLISH|ARENA_ACTIONS)(?:$|-))/i;

function stableAsset(path) {
    return `${path}?v=${ASSET_VERSION}`;
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
const CORE_ASSETS = [
    "/manifest.webmanifest",
    "/static/manifest.webmanifest",
    stableAsset("/static/css/rebirth.css"),
    stableAsset("/static/css/rebirth_beta.css"),
    stableAsset("/static/js/rebirth.js"),
    stableAsset("/static/js/rebirth_recap.js"),
    stableAsset("/static/js/rebirth_audio.js"),
    stableAsset("/static/js/rebirth_ui.js"),
    stableAsset("/static/js/rebirth_fx.js"),
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
const MAX_RUNTIME_CACHE_ENTRIES = CORE_ASSETS.length;

function isPlayerStateRequest(url) {
    return PLAYER_STATE_API_DENY_RE.test(url.pathname) || DYNAMIC_REBIRTH_API_DENY_RE.test(url.pathname);
}

function isCacheableAppShellRequest(url) {
    if (url.origin !== self.location.origin) {
        return false;
    }
    return CORE_ASSET_SET.has(`${url.pathname}${url.search}`);
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

function trimRuntimeCache(cache) {
    return cache.keys().then(function (requests) {
        const overflow = Math.max(0, requests.length - MAX_RUNTIME_CACHE_ENTRIES);
        if (!overflow) {
            return Promise.resolve();
        }
        return Promise.all(
            requests.slice(0, overflow).map(function (request) {
                return cache.delete(request);
            })
        );
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

    const cachePromise = caches.open(CACHE_NAME);
    const networkUpdate = cachePromise.then(function (cache) {
        return fetch(event.request).then(function (response) {
            if (!response || !response.ok || response.type !== "basic") {
                return response;
            }
            return cache.put(event.request, response.clone()).then(function () {
                return trimRuntimeCache(cache);
            }).then(function () {
                return response;
            });
        });
    });

    // A resposta em cache pode voltar imediatamente, mas a atualização precisa
    // manter o worker vivo para não deixar assets antigos após uma nova versão.
    event.waitUntil(networkUpdate.catch(function () {
        return undefined;
    }));
    event.respondWith(
        cachePromise.then(function (cache) {
            return cache.match(event.request);
        }).then(function (cached) {
            return cached || networkUpdate;
        })
    );
});
