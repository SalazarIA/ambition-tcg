const socket = io({
    transports: ["websocket", "polling"],
});

let latestState = null;
let selectedIntent = "Strike";

const $ = (id) => document.getElementById(id);

function logLine(message) {
    const log = $("battle-log");

    if (!log) return;

    const div = document.createElement("div");
    div.className = "log-line";
    div.textContent = message;

    log.prepend(div);
}

function setText(id, value) {
    const element = $(id);

    if (element) {
        element.textContent = value;
    }
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
    setText("round-label", state.round || 1);
    setText("phase-label", state.phase || (state.resolving ? "Resolve Phase" : "Set Phase"));

    if (state.me) {
        setText("my-name", state.me.name || "Player");
        setText("my-hp", state.me.hp ?? 4000);
        setText("my-deck", state.me.deck_count ?? 0);
        setText("my-gy", state.me.graveyard_count ?? 0);
        setText("my-ready", state.me.ready ? "Yes" : "No");
    }

    if (state.enemy) {
        setText("enemy-name", state.enemy.name || "Opponent");
        setText("enemy-hp", state.enemy.hp ?? 4000);
        setText("enemy-deck", state.enemy.deck_count ?? 0);
        setText("enemy-hand", state.enemy.hand_count ?? 0);
        setText("enemy-ready", state.enemy.ready ? "Yes" : "No");
    }
}

function renderField(state) {
    const myMonster = $("my-monster-slot");
    const myST = $("my-st-slot");
    const enemyMonster = $("enemy-monster-slot");
    const enemyST = $("enemy-st-slot");

    if (myMonster) {
        myMonster.innerHTML = renderCard(state.me?.field_m, { emptyText: "Empty Monster Zone" });
    }

    if (myST) {
        myST.innerHTML = renderCard(state.me?.field_st, { emptyText: "Empty Spell/Trap Zone" });
    }

    if (enemyMonster) {
        if (state.enemy?.field_m_rev) {
            enemyMonster.innerHTML = renderCard(state.enemy.field_m_rev, { emptyText: "Hidden" });
        } else {
            enemyMonster.innerHTML = `<div class="empty-slot-v103">${state.enemy?.field_m_status || "Hidden"}</div>`;
        }
    }

    if (enemyST) {
        enemyST.innerHTML = `<div class="empty-slot-v103">${state.enemy?.field_st_status || "Empty"}</div>`;
    }
}

function renderHand(state) {
    const hand = $("hand");

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
        wrapper.innerHTML = renderCard(card);
        wrapper.addEventListener("click", () => {
            socket.emit("play_to_field", { index });
        });

        hand.appendChild(wrapper);
    });
}

function renderState(state) {
    latestState = state;

    updateHud(state);
    renderField(state);
    renderHand(state);
}

function setQueueStatus(message) {
    const status = $("queue-status");

    if (status) {
        status.textContent = message;
    }
}

function setIntent(intent) {
    selectedIntent = intent;

    document.querySelectorAll(".intent-btn-v103").forEach((button) => {
        button.classList.toggle("active", button.dataset.intent === intent);
    });

    socket.emit("set_intent", { intent });
    logLine(`Intent selected: ${intent}`);
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".intent-btn-v103").forEach((button) => {
        button.addEventListener("click", () => setIntent(button.dataset.intent));
    });

    const joinButton = $("join-queue-btn");

    if (joinButton) {
        joinButton.addEventListener("click", () => {
            setQueueStatus(window.AMBITIONZ_TRAINING_MODE ? "Starting training..." : "Searching for opponent...");
            socket.emit(window.AMBITIONZ_TRAINING_MODE ? "join_training" : "join_queue");
        });
    }

    const readyButton = $("ready-btn");

    if (readyButton) {
        readyButton.addEventListener("click", () => {
            socket.emit("declare_ready");
        });
    }

    setIntent(selectedIntent);
});

socket.on("connect", () => {
    setQueueStatus("Connected.");
    logLine("Connected to Ambitionz server.");
});

socket.on("disconnect", () => {
    setQueueStatus("Disconnected.");
    logLine("Disconnected from server.");
});

socket.on("queue_status", (data) => {
    setQueueStatus(data.msg || "Queue updated.");
});

socket.on("match_found", (data) => {
    setQueueStatus(data.msg || "Match found.");
    logLine(data.msg || "Match found.");
});

socket.on("game_state_update", (state) => {
    renderState(state);
});

socket.on("battle_log", (data) => {
    logLine(data.msg || "Battle event.");
});

socket.on("game_over", (data) => {
    logLine(`Game Over: ${data.result}`);
    setQueueStatus(`Game Over: ${data.result}`);
});

socket.on("opponent_left", (data) => {
    logLine(data.msg || "Opponent left.");
    setQueueStatus(data.msg || "Opponent left.");
});
