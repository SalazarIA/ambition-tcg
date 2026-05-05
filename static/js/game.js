
// =========================================================
// AMBITIONZ V1.12 — BATTLE UI POLISH + OVERREACH FEEDBACK
// =========================================================

function setElementClass(id, className, enabled) {
    const el = DOM.byId(id);

    if (!el) {
        return;
    }

    el.classList.toggle(className, Boolean(enabled));
}

function setBodyBattleState(state) {
    const body = document.body;

    if (!body) {
        return;
    }

    const me = state?.me || {};
    const enemy = state?.enemy || {};
    const phase = String(state?.phase || "").toLowerCase();

    body.classList.toggle("battle-active-v112", Boolean(state));
    body.classList.toggle("battle-resolving-v112", Boolean(state?.resolving) || phase.includes("resolve"));
    body.classList.toggle("battle-ready-v112", Boolean(me.ready));
    body.classList.toggle("enemy-ready-v112", Boolean(enemy.ready));
}

function updateReadyVisuals(state) {
    const me = state?.me || {};
    const enemy = state?.enemy || {};

    setElementClass("my-ready", "ready-pill-v112", Boolean(me.ready));
    setElementClass("enemy-ready", "ready-pill-v112", Boolean(enemy.ready));
    setElementClass("ready-btn", "ready-btn-active-v112", Boolean(me.ready));
}

function updateIntentVisuals() {
    const overreachActive = selectedIntent === "Ambition Unleash" || Boolean(latestState?.me?.wants_unleash);

    document.body.classList.toggle("overreach-armed-v112", overreachActive);

    DOM.qsa(".intent-btn-v103").forEach((button) => {
        const isOverreach = button.dataset.intent === "Ambition Unleash";
        button.classList.toggle("overreach-btn-v112", isOverreach);
        button.classList.toggle("overreach-active-v112", isOverreach && overreachActive);
    });

    const status = DOM.byId("queue-status");

    if (status) {
        status.classList.toggle("overreach-status-v112", overreachActive);
    }
}

function normalizeBattleLogMessage(message) {
    const text = String(message || "Battle event.");

    if (text.toLowerCase().includes("overreach")) {
        return "⚠ OVERREACH: " + text;
    }

    if (text.toLowerCase().includes("ready")) {
        return "READY: " + text;
    }

    if (text.toLowerCase().includes("damage")) {
        return "DAMAGE: " + text;
    }

    if (text.toLowerCase().includes("heal")) {
        return "HEAL: " + text;
    }

    return text;
}


function showPostMatchSummary(data) {
    const modal = document.getElementById("post-match-modal");

    if (!modal) {
        return;
    }

    const result = data?.result || "UNKNOWN";
    const rewards = data?.rewards || {};
    const viewer = data?.viewer || {};
    const opponent = data?.opponent || {};
    const summary = data?.summary || {};

    const title = summary.title || result;
    const message = summary.message || "Match finished.";

    DOM.setText("post-match-title", title);
    DOM.setText("post-match-message", message);
    DOM.setText("post-match-viewer-hp", String(viewer.hp ?? 0));
    DOM.setText("post-match-opponent-hp", String(opponent.hp ?? 0));
    DOM.setText("post-match-rounds", String(data?.rounds ?? 0));
    DOM.setText("post-match-coins", `+${rewards.coins ?? 0}`);
    DOM.setText("post-match-xp", `+${rewards.xp ?? 0}`);

    modal.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");
}

function closePostMatchSummary() {
    const modal = document.getElementById("post-match-modal");

    if (!modal) {
        return;
    }

    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
}

document.addEventListener("DOMContentLoaded", () => {
    const playAgain = document.getElementById("post-match-play-again");

    if (playAgain) {
        playAgain.addEventListener("click", () => {
            closePostMatchSummary();
            window.location.reload();
        });
    }
});

const socket = io({
    transports: ["websocket", "polling"],
});

window.socket = socket;

let latestState = null;
let selectedIntent = "Strike";
let matchmakingTimer = null;
let matchmakingDeadline = 0;

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
    DOM.appendLog("battle-log", normalizeBattleLogMessage(message));
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
    DOM.setText("my-energy", `${me.energy ?? 0}/${me.max_energy ?? 0}`);
    DOM.setText("my-ambition", me.wants_unleash ? `${me.ambition ?? 0} armed` : `${me.ambition ?? 0}`);
    DOM.setText("my-intent", me.wants_unleash ? "Unleash" : (me.intent || "Strike"));
    DOM.setText("my-deck", me.deck_count ?? 0);
    DOM.setText("my-gy", me.graveyard_count ?? 0);
    DOM.setText("my-ready", me.ready ? "Yes" : "No");

    DOM.setText("enemy-name", enemy.name || "Opponent");
    DOM.setText("enemy-hp", enemy.hp ?? 4000);
    DOM.setText("enemy-energy", `${enemy.energy ?? 0}/${enemy.max_energy ?? 0}`);
    DOM.setText("enemy-ambition", enemy.wants_unleash ? `${enemy.ambition ?? 0} armed` : `${enemy.ambition ?? 0}`);
    DOM.setText("enemy-intent", enemy.intent || "Hidden");
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
    const me = state.me || {};
    const energy = Number(me.energy || 0);
    const monsterOccupied = Boolean(me.field_m);
    const spellTrapOccupied = Boolean(me.field_st);
    const lockedByState = Boolean(me.ready || state.resolving);

    if (!cards.length) {
        hand.innerHTML = `<div class="empty-slot-v103">No cards in hand</div>`;
        return;
    }

    cards.forEach((card, index) => {
        const cost = Number(card?.cost || 0);
        const type = String(card?.type || "");
        const zoneBlocked = (type === "Monster" && monsterOccupied) || (["Spell", "Trap"].includes(type) && spellTrapOccupied);
        const canAfford = cost <= energy;
        const playable = !lockedByState && !zoneBlocked && canAfford;
        const wrapper = document.createElement("button");
        wrapper.type = "button";
        wrapper.className = `arena-hand-card ${playable ? "is-playable-v151" : "is-locked-v151"}`;
        wrapper.disabled = !playable;
        wrapper.setAttribute("data-card-index", String(index));
        wrapper.setAttribute("aria-disabled", playable ? "false" : "true");
        wrapper.title = playable
            ? `Play ${card?.name || "card"}`
            : zoneBlocked
                ? "Zone already occupied"
                : canAfford
                    ? "Wait until your next action"
                    : `Needs ${cost} energy`;
        wrapper.innerHTML = renderCard(card);

        wrapper.addEventListener("click", () => {
            if (!playable) {
                return;
            }

            socket.emit("play_to_field", { index });
        });

        hand.appendChild(wrapper);
    });
}

function renderState(state) {
    latestState = state || {};

    if (selectedIntent === "Ambition Unleash" && !latestState?.me?.wants_unleash) {
        selectedIntent = latestState?.me?.intent || "Strike";
    }

    updateHud(latestState);
    renderField(latestState);
    renderHand(latestState);
    setBodyBattleState(latestState);
    updateReadyVisuals(latestState);
    updateIntentVisuals();

    window.dispatchEvent(new CustomEvent("ambition:state_update", { detail: latestState }));
}


function setButtonBusy(id, busy, labelWhenBusy) {
    const button = DOM.byId(id);

    if (!button) {
        return;
    }

    if (!button.dataset.originalLabel) {
        button.dataset.originalLabel = button.textContent.trim();
    }

    button.disabled = Boolean(busy);
    button.textContent = busy ? labelWhenBusy : button.dataset.originalLabel;
}


function setQueueStatus(message) {
    DOM.setText("queue-status", message || "Status updated.");
}

function clearMatchmakingCountdown(message) {
    if (matchmakingTimer) {
        window.clearInterval(matchmakingTimer);
        matchmakingTimer = null;
    }

    matchmakingDeadline = 0;

    if (message) {
        DOM.setText("matchmaking-countdown", message);
    }

    const countdown = DOM.byId("matchmaking-countdown");

    if (countdown) {
        countdown.classList.remove("searching", "fallback");
    }
}

function tickMatchmakingCountdown() {
    const remaining = Math.max(0, Math.ceil((matchmakingDeadline - Date.now()) / 1000));
    const countdown = DOM.byId("matchmaking-countdown");

    if (!countdown) {
        return;
    }

    countdown.classList.add("searching");
    countdown.classList.remove("fallback");
    countdown.textContent = remaining > 0
        ? `Searching real players. Bot fallback in ${remaining}s.`
        : "No real opponent yet. Starting bot fallback...";
}

function startMatchmakingCountdown(seconds) {
    clearMatchmakingCountdown();

    matchmakingDeadline = Date.now() + Math.max(0, Number(seconds || 0)) * 1000;
    tickMatchmakingCountdown();
    matchmakingTimer = window.setInterval(tickMatchmakingCountdown, 250);
}

function setSearchUi(searching) {
    document.body.classList.toggle("matchmaking-searching-v150", Boolean(searching));
    setButtonBusy("join-queue-btn", Boolean(searching), "Searching...");

    const cancelButton = DOM.byId("cancel-queue-btn");

    if (cancelButton) {
        cancelButton.hidden = !searching;
        cancelButton.disabled = false;
    }
}

function updatePresence(data) {
    const online = Number(data?.online || 0);
    const queued = Number(data?.queued || 0);
    const activeMatches = Number(data?.active_matches || 0);
    const pvpMatches = Number(data?.pvp_matches || 0);
    const botMatches = Number(data?.bot_matches || 0);

    DOM.setText(
        "presence-status",
        `${online} online • ${queued} searching • ${activeMatches} active (${pvpMatches} PvP / ${botMatches} bot)`
    );
}

function setIntent(intent) {
    selectedIntent = intent || "Strike";

    DOM.qsa(".intent-btn-v103").forEach((button) => {
        button.classList.toggle("active", button.dataset.intent === selectedIntent);
    });

    updateIntentVisuals();

    if (selectedIntent === "Ambition Unleash") {
        socket.emit("toggle_unleash");
        setQueueStatus("Ambition Unleash armed: high pressure, high risk.");
        logLine("Ambition Unleash selected. Commit only when the reward is worth the exposure.");
    } else {
        socket.emit("set_intent", { intent: selectedIntent });
        logLine(`Intent selected: ${selectedIntent}`);
    }
}

function bootArenaControls() {
    DOM.qsa(".intent-btn-v103").forEach((button) => {
        button.addEventListener("click", () => setIntent(button.dataset.intent));
    });

    DOM.onClick("join-queue-btn", () => {
        const trainingMode = Boolean(window.AMBITIONZ_TRAINING_MODE);
        const difficultySelect = DOM.byId("bot-difficulty");
        const difficulty = difficultySelect ? difficultySelect.value : "normal";

        setQueueStatus(trainingMode ? `Starting ${difficulty} training...` : "Searching for opponent...");

        if (trainingMode) {
            setButtonBusy("join-queue-btn", true, "Starting...");
            socket.emit("join_training", { difficulty });
        } else {
            setSearchUi(true);
            startMatchmakingCountdown(10);
            socket.emit("join_queue");
        }
    });

    DOM.onClick("ready-btn", () => {
        socket.emit("declare_ready");
        setQueueStatus("Ready declared. Waiting for battle resolution.");
        logLine("Ready declared.");
    });


    DOM.onClick("join-private-room-btn", () => {
        const input = DOM.byId("private-room-code");
        const code = String(input?.value || "").trim().toUpperCase().replace(/\s+/g, "");

        if (!code || code.length !== 5) {
            setQueueStatus("Enter a valid 5-character private room code.");
            logLine("Invalid private room code.");
            return;
        }

        setQueueStatus(`Joining private room ${code}...`);
        socket.emit("join_private_room", { code });
    });

    DOM.onClick("join-bot-match-btn", () => {
        setQueueStatus("Starting bot duel...");
        setButtonBusy("join-bot-match-btn", true, "Starting...");
        socket.emit("join_bot_match");
    });

    DOM.onClick("cancel-queue-btn", () => {
        setQueueStatus("Cancelling match search...");
        socket.emit("cancel_queue");
    });

    setIntent(selectedIntent);
}

document.addEventListener("DOMContentLoaded", bootArenaControls);

window.addEventListener("ambition:unleash_requested", () => {
    socket.emit("toggle_unleash");
    setQueueStatus("Ambition Unleash toggled.");
});

socket.on("connect", () => {
    setQueueStatus("Connected.");
    logLine("Connected to Ambitionz server.");
});

socket.on("disconnect", () => {
    clearMatchmakingCountdown("Disconnected from matchmaking.");
    setSearchUi(false);
    setButtonBusy("join-queue-btn", false);
    setButtonBusy("join-bot-match-btn", false);
    setQueueStatus("Disconnected.");
    logLine("Disconnected from server.");
});

socket.on("queue_status", (data) => {
    setQueueStatus(data?.msg || "Queue updated.");
});

socket.on("match_found", (data) => {
    document.body.classList.remove("overreach-armed-v112");
    clearMatchmakingCountdown("Match found. Entering battle.");
    setSearchUi(false);
    setButtonBusy("join-queue-btn", false);
    setButtonBusy("join-bot-match-btn", false);
    setQueueStatus(data?.msg || "Match found.");
    logLine(data?.msg || "Match found.");
});

socket.on("matchmaking_status", (data) => {
    const status = data?.status || "idle";

    if (status === "searching") {
        if (data?.mode === "pvp") {
            setSearchUi(true);
            startMatchmakingCountdown(data?.fallback_seconds || 10);
        } else {
            setSearchUi(false);
            clearMatchmakingCountdown("Private room created. Waiting for the invited tester.");
        }

        return;
    }

    if (status === "fallback") {
        clearMatchmakingCountdown("No real player found. Bot duel started.");
        const countdown = DOM.byId("matchmaking-countdown");

        if (countdown) {
            countdown.classList.add("fallback");
        }

        setSearchUi(false);
        return;
    }

    if (status === "matched") {
        clearMatchmakingCountdown("Real opponent found.");
        setSearchUi(false);
        return;
    }

    if (status === "cancelled") {
        clearMatchmakingCountdown("Search cancelled.");
        setSearchUi(false);
        return;
    }

    if (status === "error") {
        clearMatchmakingCountdown("Matchmaking needs another try.");
        setSearchUi(false);
    }
});

socket.on("presence_update", (data) => {
    updatePresence(data);
});

socket.on("game_state_update", (state) => {
    renderState(state);
});

socket.on("battle_events", (events) => {
    window.dispatchEvent(new CustomEvent("ambition:battle_events", { detail: events || [] }));
});

socket.on("battle_log", (data) => {
    logLine(data?.msg || "Battle event.");
});

socket.on("game_over", (data) => {
    clearMatchmakingCountdown("Match complete.");
    setSearchUi(false);
    setButtonBusy("join-queue-btn", false);
    setButtonBusy("join-bot-match-btn", false);
    logLine(`Game Over: ${data?.result || "Unknown"}`);
    setQueueStatus(`Game Over: ${data?.result || "Unknown"}`);
});

socket.on("post_match_summary", (data) => {
    const title = data?.summary?.title || data?.result || "Match Complete";
    logLine(`Post Match: ${title}`);
    showPostMatchSummary(data);
});

socket.on("opponent_left", (data) => {
    logLine(data?.msg || "Opponent left.");
    setQueueStatus(data?.msg || "Opponent left.");
});
