const fs = require("fs");
const path = require("path");
const vm = require("vm");

const SCRIPT = fs.readFileSync(
    path.join(__dirname, "..", "..", "static", "js", "service-worker.js"),
    "utf-8"
);
const VERSION_MATCH = SCRIPT.match(/const ASSET_VERSION = "([^"]+)"/);

function assert(condition, message) {
    if (!condition) {
        throw new Error("ASSERTION FAILED: " + message);
    }
}

assert(VERSION_MATCH, "ASSET_VERSION deve estar declarado");
const ASSET_VERSION = VERSION_MATCH[1];
const CACHE_NAME = `ambitionz-rebirth-shell-${ASSET_VERSION}`;
const ORIGIN = "https://ambition.test";

function createHarness({ cacheRequests = [], cachedResponse = null } = {}) {
    const listeners = new Map();
    const deletedCaches = [];
    const deletedRequests = [];
    const openedCaches = [];
    const addAllCalls = [];
    const putCalls = [];
    const matchCalls = [];
    const fetchCalls = [];
    let claimCalls = 0;
    let skipWaitingCalls = 0;

    const cache = {
        addAll(assets) {
            addAllCalls.push(assets.slice());
            return Promise.resolve();
        },
        keys() {
            return Promise.resolve(cacheRequests.slice());
        },
        delete(request) {
            deletedRequests.push(request.url);
            return Promise.resolve(true);
        },
        match(request) {
            matchCalls.push(request.url);
            return Promise.resolve(cachedResponse);
        },
        put(request, response) {
            putCalls.push({ request, response });
            return Promise.resolve();
        },
    };
    const caches = {
        storedNames: [CACHE_NAME],
        open(name) {
            openedCaches.push(name);
            return Promise.resolve(cache);
        },
        keys() {
            return Promise.resolve(this.storedNames.slice());
        },
        delete(name) {
            deletedCaches.push(name);
            return Promise.resolve(true);
        },
    };
    const self = {
        location: { origin: ORIGIN },
        clients: {
            claim() {
                claimCalls += 1;
                return Promise.resolve();
            },
        },
        skipWaiting() {
            skipWaitingCalls += 1;
            return Promise.resolve();
        },
        addEventListener(type, listener) {
            listeners.set(type, listener);
        },
    };
    const networkResponse = {
        ok: true,
        type: "basic",
        clone() {
            return { cloned: true };
        },
    };
    const fetch = (request) => {
        fetchCalls.push(request.url);
        return Promise.resolve(networkResponse);
    };

    vm.runInNewContext(SCRIPT, { URL, caches, fetch, self });

    function dispatchExtendable(type, extra = {}) {
        let lifetime = Promise.resolve();
        const event = Object.assign({
            waitUntil(promise) {
                lifetime = Promise.resolve(promise);
            },
        }, extra);
        listeners.get(type)(event);
        return lifetime;
    }

    function dispatchFetch(request) {
        let responsePromise = null;
        let lifetime = Promise.resolve();
        const event = {
            request,
            respondWith(promise) {
                responsePromise = Promise.resolve(promise);
            },
            waitUntil(promise) {
                lifetime = Promise.resolve(promise);
            },
        };
        listeners.get("fetch")(event);
        return { responsePromise, lifetime };
    }

    return {
        addAllCalls,
        caches,
        deletedCaches,
        deletedRequests,
        dispatchExtendable,
        dispatchFetch,
        fetchCalls,
        matchCalls,
        openedCaches,
        putCalls,
        claimCalls: () => claimCalls,
        skipWaitingCalls: () => skipWaitingCalls,
    };
}

(async function run() {
    const install = createHarness();
    await install.dispatchExtendable("install");
    assert(install.addAllCalls.length === 1, "install deve preencher um único cache de shell");
    assert(
        install.addAllCalls[0].includes(`/static/js/pwa.js?v=${ASSET_VERSION}`),
        "pwa.js versionado deve permanecer no shell seguro"
    );
    assert(
        install.addAllCalls[0].every((asset) => !asset.startsWith("/api/")),
        "nenhuma API dinâmica pode entrar no precache"
    );
    assert(install.skipWaitingCalls() === 1, "install deve manter ativação da versão nova");

    const activeCoreRequest = { url: `${ORIGIN}/static/js/pwa.js?v=${ASSET_VERSION}` };
    const staleRequest = { url: `${ORIGIN}/static/js/pwa.js?v=stale` };
    const apiRequestInCache = { url: `${ORIGIN}/api/rebirth/wallet` };
    const activate = createHarness({
        cacheRequests: [activeCoreRequest, staleRequest, apiRequestInCache],
    });
    activate.caches.storedNames = [
        CACHE_NAME,
        "ambitionz-rebirth-shell-v106_ARENA_ACTIONS",
        "third-party-unrelated-cache",
    ];
    await activate.dispatchExtendable("activate");
    assert(
        activate.deletedCaches.includes("ambitionz-rebirth-shell-v106_ARENA_ACTIONS"),
        "activate deve remover cache antigo do Rebirth"
    );
    assert(
        !activate.deletedCaches.includes("third-party-unrelated-cache"),
        "activate não deve remover caches alheios"
    );
    assert(
        activate.deletedRequests.includes(staleRequest.url)
            && activate.deletedRequests.includes(apiRequestInCache.url),
        "activate deve podar entradas fora do shell permitido"
    );
    assert(
        !activate.deletedRequests.includes(activeCoreRequest.url),
        "activate deve preservar asset versionado ativo"
    );
    assert(activate.claimCalls() === 1, "activate deve assumir clientes para disponibilizar updates");

    const networkOnly = createHarness();
    const apiFetch = networkOnly.dispatchFetch({
        method: "GET",
        mode: "cors",
        url: `${ORIGIN}/api/rebirth/profile`,
    });
    assert(apiFetch.responsePromise, "API de estado deve receber resposta de rede explícita");
    await apiFetch.responsePromise;
    assert(networkOnly.fetchCalls.length === 1, "API de estado deve ir uma vez à rede");
    assert(networkOnly.openedCaches.length === 0, "API de estado não deve abrir cache");

    const cached = { source: "cache" };
    const shellFetch = createHarness({ cachedResponse: cached });
    const shellRequest = {
        method: "GET",
        mode: "cors",
        url: `${ORIGIN}/static/js/pwa.js?v=${ASSET_VERSION}`,
    };
    const shellEvent = shellFetch.dispatchFetch(shellRequest);
    assert(shellEvent.responsePromise, "asset do shell deve ser tratado pelo SW");
    assert(await shellEvent.responsePromise === cached, "asset do shell deve responder do cache imediatamente");
    await shellEvent.lifetime;
    assert(shellFetch.fetchCalls.length === 1, "asset em cache deve atualizar em background");
    assert(shellFetch.putCalls.length === 1, "resposta de rede válida deve renovar o cache");

    const ignored = createHarness();
    const ignoredEvent = ignored.dispatchFetch({
        method: "GET",
        mode: "cors",
        url: `${ORIGIN}/static/js/not-in-shell.js`,
    });
    assert(!ignoredEvent.responsePromise, "asset fora da allowlist deve ficar fora do cache do SW");

    console.log("service worker cache safety: OK (install, activate, API, SWR allowlist)");
})().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
