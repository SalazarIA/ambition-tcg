const socket = io({
    transports: ["websocket", "polling"],
});

let latestState = null;
let selectedIntent = "Strike";

const DOM = window.AmbitionzDOM || {
    byId: (id) => document.getElementById(id),
    setText: (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    },
    setHtml: (id, html) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = html;
    },
    appendLog: (id, message) => {
        const el = document.getElementById(id);
        if (!el) return;
        const div = document.createElement("div");
        div.className = "log-line";
        div.textContent = message;
        el.prepend(div);
    },
    onClick: (id, handler) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener("click", handler);
    },
    qsa: (selector) => Array.from(document.querySelectorAll(selector)),
};

function logLine(message) {
    DOM.appendLog("battle-log", message || "Battle event.");
}

function renderCard(card, options = {}) {
    if (window.AmbitionzCardUI && window.AmbitionzCardUI.cardFrameHtml) {
        return window.AmbitionzCardUI.cardFrameHtml(card, options);
    }

    if (!card) {
        return `<div class="empty-slot-v103">${options.emptyText || "Empty"}</div>`;
    }

    return `
        <article class="collection-card">
            <strong>${card.name || "Card"}</strong>
            <p>${card.type || ""} / ${card.element || ""}</p>
            <p>${card.effect || ""}</p>
        </article>
    `;
}

function updateHud(state) {
    DOM.setText("round-label", state.round || 1);
    DOM.setText("phase-label", state.phase || (state.resolving ? "Resolve Phase" : "Set Phase"));

    const me = state.me || {};
    const enemy = state.enemy || {};

    DOM.setText("my-name", me.name || "Player");
    DOM.setText("my-hp", me.hp ?? 4000);
    DOM.setText("my-deck", me.deck_count ?? 0);
    DOM.setText("my-gy", me.graveyard_count ?? 0);
    DOM.setText("my-ready", me.ready ? "Yes" : "No");

    DOM.setText("enemy-name", enemy.name || "Opponent");
    DOM.setText("enemy-hp", enemy.hp ?? 4000);
    DOM.setText("enemy-deck", enemy.deck_count ?? 0);
    DOM.setText("enemy-hand", enemy.hand_count ?? 0);
    DOM.setText("enemy-ready", enemy.ready ? "Yes" : "No");
}

function renderField(state) {
    const me = state.me || {};
    const enemy = state.enemy || {};

    DOM.setHtml("my-monster-slot", renderCard(me.field_m, { emptyText: "Empty Monster Zone" }));
    DOM.setHtml("my-st-slot", renderCard(me.field_st, { emptyText: "Empty Spell/Trap Zone" }));

    if (enemy.field_m_rev) {
        DOM.setHtml("enemy-monster-slot", renderCard(enemy.field_m_rev, { emptyText: "Hidden" }));
    } else {
        DOM.setHtml("enemy-monster-slot", `<div class="empty-slot-v103">${enemy.field_m_status || "Hidden"}</div>`);
    }

    DOM.setHtml("enemy-st-slot", `<div class="empty-slot-v103">${enemy.field_st_status || "Empty"}</div>`);
}

function renderHand(state) {
    const hand = DOM.byId("hand");

    if (!hand) return;

    hand.innerHTML = "";

    const cards = state.me?.hand || [];

    if (!cards.length) {
        hand.innerHTML = `<div class="empty-slot-v103">No cards in hand</div>`;
        return;
    }

    cards.forEach((card, index) => {
        const wrapper = document.createElement("button");
        wrapper.type = "button";
        wrapper.className = "arena-hand-card";
        wrapper.setAttribute("data-card-index", String(index));
        wrapper.innerHTML = renderCard(card);

        wrapper.addEventListener("click", () => {
            socket.emit("play_to_field", { index });
        });

        hand.appendChild(wrapper);
    });
}

function renderState(state) {
    latestState = state || {};

    updateHud(latestState);
    renderField(latestState);
    renderHand(latestState);
}

function setQueueStatus(message) {
    DOM.setText("queue-status", message || "Status updated.");
}

function setIntent(intent) {
    selectedIntent = intent || "Strike";

    DOM.qsa(".intent-btn-v103").forEach((button) => {
        button.classList.toggle("active", button.dataset.intent === selectedIntent);
    });

    socket.emit("set_intent", { intent: selectedIntent });
    logLine(`Intent selected: ${selectedIntent}`);
}

function bootArenaControls() {
    DOM.qsa(".intent-btn-v103").forEach((button) => {
        button.addEventListener("click", () => setIntent(button.dataset.intent));
    });

    DOM.onClick("join-queue-btn", () => {
        const trainingMode = Boolean(window.AMBITIONZ_TRAINING_MODE);
        setQueueStatus(trainingMode ? "Starting training..." : "Searching for opponent...");
        socket.emit(trainingMode ? "join_training" : "join_queue");
    });

    DOM.onClick("ready-btn", () => {
        socket.emit("declare_ready");
    });

    setIntent(selectedIntent);
}

document.addEventListener("DOMContentLoaded", bootArenaControls);

socket.on("connect", () => {
    setQueueStatus("Connected.");
    logLine("Connected to Ambitionz server.");
});

socket.on("disconnect", () => {
    setQueueStatus("Disconnected.");
    logLine("Disconnected from server.");
});

socket.on("queue_status", (data) => {
    setQueueStatus(data?.msg || "Queue updated.");
});

socket.on("match_found", (data) => {
    setQueueStatus(data?.msg || "Match found.");
    logLine(data?.msg || "Match found.");
});

socket.on("game_state_update", (state) => {
    renderState(state);
});

socket.on("battle_log", (data) => {
    logLine(data?.msg || "Battle event.");
});

socket.on("game_over", (data) => {
    logLine(`Game Over: ${data?.result || "Unknown"}`);
    setQueueStatus(`Game Over: ${data?.result || "Unknown"}`);
});

socket.on("opponent_left", (data) => {
    logLine(data?.msg || "Opponent left.");
    setQueueStatus(data?.msg || "Opponent left.");
});
