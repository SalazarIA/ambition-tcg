// Standalone Node test for the v69 audio chain dedup contract.
// Executa o script real do RebirthAudioManager num sandbox mínimo, sem
// depender de AudioContext do navegador, e valida que chains longas
// (15 DAMAGE_RESOLVED no mesmo effect_chain_id) reproduzem um único som.

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const SCRIPT = fs.readFileSync(
    path.join(__dirname, "..", "..", "static", "js", "rebirth_audio.js"),
    "utf-8"
);

const fakeWindow = {
    addEventListener() {},
    removeEventListener() {},
    performance: { now: () => fakeNow },
    AudioContext: null,
    webkitAudioContext: null,
    AudioBuffer: null,
};
let fakeNow = 0;
const sandbox = { window: fakeWindow, document: {}, console };
vm.createContext(sandbox);
vm.runInContext(SCRIPT, sandbox);

const manager = sandbox.window.RebirthAudioManager;
if (!manager) {
    throw new Error("RebirthAudioManager not exposed");
}

function reset() {
    manager.lastPlayed = new Map();
    manager.replayAudioMutedMode = false;
    fakeNow = 0;
}

function assert(cond, msg) {
    if (!cond) {
        throw new Error("ASSERTION FAILED: " + msg);
    }
}

// 1. 15 DAMAGE_RESOLVED na mesma chain → 1 reprodução permitida.
reset();
let permitted = 0;
for (let i = 0; i < 15; i += 1) {
    const event = {
        event_type: "DAMAGE_RESOLVED",
        event_id: 100 + i,
        sequence_id: 100 + i,
        replay_frame: 100 + i,
        effect_chain_id: "combat-000042",
    };
    fakeNow += 5;
    if (manager.shouldPlay(event, "heavy")) {
        permitted += 1;
    }
}
assert(permitted === 1, `chain de 15 eventos deveria permitir 1 reprodução, obteve ${permitted}`);

// 2. Chain diferente passa de novo (não é mute global).
reset();
fakeNow = 0;
assert(manager.shouldPlay({ event_type: "DAMAGE_RESOLVED", effect_chain_id: "chain-A", event_id: 1 }, "heavy"), "chain A deveria tocar");
fakeNow += 10;
assert(!manager.shouldPlay({ event_type: "DAMAGE_RESOLVED", effect_chain_id: "chain-A", event_id: 2 }, "heavy"), "chain A repetida deveria ser dedupada");
fakeNow += 10;
assert(manager.shouldPlay({ event_type: "DAMAGE_RESOLVED", effect_chain_id: "chain-B", event_id: 3 }, "heavy"), "chain B independente deveria tocar");

// 3. Sem effect_chain_id, dedupa por soundKey puro (fallback estável).
reset();
fakeNow = 0;
assert(manager.shouldPlay({ event_type: "UI_CLICK_CONFIRMED" }, "click"), "primeiro click deveria tocar");
fakeNow += 30;
assert(!manager.shouldPlay({ event_type: "UI_CLICK_CONFIRMED" }, "click"), "click consecutivo dentro do debounce deveria ser dedupado");

// 4. Após debounceMs+ o evento pode reentrar.
reset();
fakeNow = 0;
manager.shouldPlay({ event_type: "DAMAGE_RESOLVED", effect_chain_id: "chain-C", event_id: 10 }, "heavy");
fakeNow += manager.debounceMs + 5;
assert(manager.shouldPlay({ event_type: "DAMAGE_RESOLVED", effect_chain_id: "chain-C", event_id: 11 }, "heavy"), "depois do debounce deveria reentrar");

// 5. eventKey real para chain → forma esperada.
const key = manager.eventKey({ effect_chain_id: "chain-XYZ" }, "heavy");
assert(key === "heavy:chain-XYZ", `eventKey esperado 'heavy:chain-XYZ', obteve '${key}'`);
const keyFallback = manager.eventKey({}, "click");
assert(keyFallback === "click", `fallback esperado 'click', obteve '${keyFallback}'`);

console.log("audio chain dedup: OK (5 asserts)");
