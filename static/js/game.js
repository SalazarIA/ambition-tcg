const socket = io();

let lastMyHp = null;
let lastEnemyHp = null;

function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function getElementIcon(element) {
    const icons = {
        Fire: "🔥",
        Water: "💧",
        Earth: "🪨",
        Plant: "🌿",
        Global: "◇",
        Neutral: "◇",
        Dark: "☾"
    };

    return icons[element] || "◇";
}

function getCardImageUrl(card) {
    if (!card || !card.image) {
        return "/static/img/cards/placeholders/card_placeholder.svg";
    }

    return `/static/img/${card.image}`;
}

function pulseElement(elementId, className) {
    const el = document.getElementById(elementId);

    if (!el) {
        return;
    }

    el.classList.remove(className);

    void el.offsetWidth;

    el.classList.add(className);

    setTimeout(() => {
        el.classList.remove(className);
    }, 550);
}

function renderCard(card, index = -1, hidden = false, setCard = false) {
    if (hidden) {
        return `
            <div class="card card-back">
                <div class="card-back-inner">
                    <div class="card-back-logo">A</div>
                    <p>Hidden Monster</p>
                </div>
            </div>
        `;
    }

    if (setCard) {
        return `
            <div class="card card-set">
                <div class="card-back-inner">
                    <div class="card-back-logo">?</div>
                    <p>Set Card</p>
                </div>
            </div>
        `;
    }

    if (!card) {
        return "";
    }

    const type = escapeHtml(card.type);
    const rarity = escapeHtml(card.rarity);
    const name = escapeHtml(card.name);
    const element = escapeHtml(card.element || "Global");
    const description = escapeHtml(card.description || card.effect || "None");
    const power = Number(card.power || 0);
    const value = Number(card.value || 0);
    const img = escapeHtml(getCardImageUrl(card));

    const clickable = index >= 0 ? `onclick="playToField(${index})"` : "";

    const statValue = type === "Monster" ? power : value;
    const statLabel = type === "Monster" ? "POWER" : "VALUE";

    return `
        <article class="card image-card ${type.toLowerCase()} ${rarity.toLowerCase()}" ${clickable}>
            <div class="image-card-frame">
                <header class="image-card-header">
                    <h4>${name}</h4>
                    <span>${rarity}</span>
                </header>

                <div class="image-card-art">
                    <img
                        src="${img}"
                        alt="${name}"
                        loading="lazy"
                        onerror="this.onerror=null; this.src='/static/img/cards/placeholders/card_placeholder.svg';"
                    >
                </div>

                <div class="image-card-meta">
                    <span>${getElementIcon(element)} ${element}</span>
                    <span>${type}</span>
                </div>

                <div class="image-card-effect">
                    <p>${description}</p>
                </div>

                <footer class="image-card-footer">
                    <span>${statLabel}</span>
                    <strong>${statValue}</strong>
                </footer>
            </div>
        </article>
    `;
}

function playToField(index) {
    socket.emit("play_to_field", { index });
    pulseElement("my-hand", "soft-pulse");
}

function declareReady() {
    socket.emit("declare_ready");
    pulseElement("btn-ready", "button-pulse");
}

function addLog(message) {
    const log = document.getElementById("battle-log");

    if (!log) {
        return;
    }

    const line = document.createElement("p");
    line.textContent = `> ${message}`;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
}

function syncRound(data) {
    const round = String(data.round);

    const desktopRound = document.getElementById("round");
    const mobileRound = document.getElementById("round-mobile");

    if (desktopRound) {
        desktopRound.textContent = round;
    }

    if (mobileRound) {
        mobileRound.textContent = round;
    }
}

function updateHpWithFeedback(data) {
    const myHp = Number(data.me.hp);
    const enemyHp = Number(data.enemy.hp);

    const myHpEl = document.getElementById("my-hp");
    const enemyHpEl = document.getElementById("enemy-hp");

    if (myHpEl) {
        myHpEl.textContent = myHp;
    }

    if (enemyHpEl) {
        enemyHpEl.textContent = enemyHp;
    }

    if (lastMyHp !== null && myHp < lastMyHp) {
        pulseElement("my-hp", "damage-pulse");
    }

    if (lastEnemyHp !== null && enemyHp < lastEnemyHp) {
        pulseElement("enemy-hp", "damage-pulse");
    }

    if (lastMyHp !== null && myHp > lastMyHp) {
        pulseElement("my-hp", "heal-pulse");
    }

    if (lastEnemyHp !== null && enemyHp > lastEnemyHp) {
        pulseElement("enemy-hp", "heal-pulse");
    }

    lastMyHp = myHp;
    lastEnemyHp = enemyHp;
}

socket.on("connect", () => {
    addLog("Connected to server.");
    socket.emit("join_queue");
});

socket.on("queue_status", (data) => {
    addLog(data.msg);
});

socket.on("match_found", (data) => {
    addLog(data.msg);
});

socket.on("battle_log", (data) => {
    addLog(data.msg);
});

socket.on("game_state_update", (data) => {
    syncRound(data);
    updateHpWithFeedback(data);

    const enemyName = document.getElementById("enemy-name");

    if (enemyName) {
        enemyName.textContent = data.enemy.name;
    }

    document.getElementById("my-deck-count").textContent = data.me.deck_count;
    document.getElementById("enemy-deck-count").textContent = data.enemy.deck_count;

    document.getElementById("my-graveyard-count").textContent = data.me.graveyard_count;
    document.getElementById("enemy-graveyard-count").textContent = data.enemy.graveyard_count;

    document.getElementById("enemy-hand-count").textContent = data.enemy.hand_count;

    document.getElementById("my-hand").innerHTML = data.me.hand
        .map((card, index) => renderCard(card, index))
        .join("");

    document.getElementById("my-monster-zone").innerHTML = data.me.field_m
        ? renderCard(data.me.field_m)
        : "<span>My Monster</span>";

    document.getElementById("my-st-zone").innerHTML = data.me.field_st
        ? renderCard(data.me.field_st)
        : "<span>My Spell/Trap</span>";

    if (data.enemy.field_m_status === "HIDDEN") {
        document.getElementById("enemy-monster-zone").innerHTML = renderCard(null, -1, true);
    } else if (data.enemy.field_m_status === "REVEALED") {
        document.getElementById("enemy-monster-zone").innerHTML = renderCard(data.enemy.field_m_rev);
    } else {
        document.getElementById("enemy-monster-zone").innerHTML = "<span>Enemy Monster</span>";
    }

    if (data.enemy.field_st_status === "SET") {
        document.getElementById("enemy-st-zone").innerHTML = renderCard(null, -1, false, true);
    } else {
        document.getElementById("enemy-st-zone").innerHTML = "<span>Enemy Spell/Trap</span>";
    }

    const btn = document.getElementById("btn-ready");

    btn.disabled = data.me.ready || data.resolving;
    btn.textContent = data.me.ready ? "Waiting opponent..." : "Ready for Battle";
});

socket.on("game_over", (data) => {
    if (data.result === "WIN") {
        alert("Victory. You earned 150 coins.");
    } else if (data.result === "LOSE") {
        alert("Defeat.");
    } else {
        alert("Draw.");
    }

    window.location.href = "/";
});

socket.on("opponent_left", (data) => {
    alert(data.msg);
    window.location.href = "/";
});