const fs = require("fs");
const path = require("path");
const vm = require("vm");

const SCRIPT = fs.readFileSync(
    path.join(__dirname, "..", "..", "static", "js", "pwa.js"),
    "utf-8"
);

function assert(condition, message) {
    if (!condition) {
        throw new Error("ASSERTION FAILED: " + message);
    }
}

function eventTarget(extra = {}) {
    const listeners = new Map();
    return Object.assign(extra, {
        addEventListener(type, listener) {
            const current = listeners.get(type) || [];
            current.push(listener);
            listeners.set(type, current);
        },
        dispatch(type) {
            (listeners.get(type) || []).slice().forEach((listener) => listener());
        },
    });
}

function createHarness({ controlled, waiting }) {
    let reloads = 0;
    const postedMessages = [];
    const appended = [];
    const registration = eventTarget({
        installing: null,
        waiting: waiting ? {
            postMessage(message) {
                postedMessages.push(message);
            },
        } : null,
    });
    const serviceWorker = eventTarget({
        controller: controlled ? { scriptURL: "/service-worker.js" } : null,
        registerCalls: [],
        register(url, options) {
            this.registerCalls.push({ url, options });
            return Promise.resolve(registration);
        },
    });
    const window = eventTarget({
        location: {
            reload() {
                reloads += 1;
            },
        },
    });
    const document = {
        querySelector(selector) {
            if (selector !== "[data-rebirth-update]") {
                return null;
            }
            return appended.find((node) => node.attributes["data-rebirth-update"] !== undefined) || null;
        },
        createElement(tagName) {
            return eventTarget({
                tagName,
                attributes: {},
                disabled: false,
                setAttribute(name, value) {
                    this.attributes[name] = value;
                },
            });
        },
        body: {
            appendChild(node) {
                appended.push(node);
            },
        },
    };

    vm.runInNewContext(SCRIPT, {
        console,
        document,
        navigator: { serviceWorker },
        window,
    });

    return {
        appended,
        postedMessages,
        registration,
        serviceWorker,
        window,
        reloads: () => reloads,
    };
}

async function settleRegistration(harness) {
    harness.window.dispatch("load");
    await Promise.resolve();
    await Promise.resolve();
}

(async function run() {
    const firstBoot = createHarness({ controlled: false, waiting: false });
    await settleRegistration(firstBoot);
    firstBoot.serviceWorker.controller = { scriptURL: "/service-worker.js" };
    firstBoot.serviceWorker.dispatch("controllerchange");
    assert(firstBoot.reloads() === 0, "primeiro claim do service worker não deve forçar reload");

    const update = createHarness({ controlled: true, waiting: false });
    await settleRegistration(update);
    update.serviceWorker.controller = { scriptURL: "/service-worker.js?v=next" };
    update.serviceWorker.dispatch("controllerchange");
    update.serviceWorker.dispatch("controllerchange");
    assert(update.reloads() === 1, "update real deve recarregar exatamente uma vez");

    const waitingUpdate = createHarness({ controlled: true, waiting: true });
    await settleRegistration(waitingUpdate);
    assert(waitingUpdate.appended.length === 1, "worker em waiting deve exibir prompt de update");
    waitingUpdate.appended[0].dispatch("click");
    assert(waitingUpdate.postedMessages.length === 1, "prompt deve solicitar ativação do worker em waiting");
    assert(
        waitingUpdate.postedMessages[0].type === "SKIP_WAITING",
        "prompt deve preservar o protocolo SKIP_WAITING"
    );
    assert(waitingUpdate.reloads() === 0, "clique só deve recarregar após controllerchange");

    assert(firstBoot.serviceWorker.registerCalls.length === 1, "service worker deve ser registrado uma vez");
    assert(
        firstBoot.serviceWorker.registerCalls[0].url === "/service-worker.js"
            && firstBoot.serviceWorker.registerCalls[0].options.scope === "/",
        "registro deve manter script e escopo raiz"
    );

    console.log("pwa controllerchange lifecycle: OK (first boot, update, waiting)");
})().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
