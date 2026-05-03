(function () {
  const state = {
    round: 1,
    player: {
      name: "You",
      hp: 4000,
      energy: 2,
      ambition: 0,
      intent: "-",
      card: "-"
    },
    enemy: {
      name: "Enemy",
      hp: 4000,
      energy: 2,
      ambition: 0,
      intent: "-",
      card: "-"
    },
    summary: "Choose your Intent",
    subsummary: "Strike, Guard or Focus",
    details: [],
    unleashReady: false
  };

  const INTENT_CLASS = {
    Strike: "intent-strike",
    Guard: "intent-guard",
    Focus: "intent-focus"
  };

  function ensureHud() {
    let hud = document.getElementById("ambition-hud-v2");
    if (hud) return hud;

    hud = document.createElement("section");
    hud.id = "ambition-hud-v2";
    hud.className = "ambition-hud-v2";
    hud.innerHTML = `
      <div class="ambition-hud-grid">
        <div class="ambition-panel">
          <div class="ambition-name" data-hud="player-name">You</div>
          <div class="ambition-stat-row"><span>HP</span><strong data-hud="player-hp">4000</strong></div>
          <div class="ambition-stat-row"><span>Energy</span><strong data-hud="player-energy">2</strong></div>
          <div class="ambition-stat-row"><span>Ambition</span><strong data-hud="player-ambition">0</strong></div>
          <div class="ambition-stat-row"><span>Intent</span><strong data-hud="player-intent">-</strong></div>
          <div class="ambition-stat-row"><span>Card</span><strong data-hud="player-card">-</strong></div>
        </div>

        <div class="ambition-panel ambition-center">
          <div class="ambition-round" data-hud="round">Round 1</div>
          <div class="ambition-summary" data-hud="summary">Choose your Intent</div>
          <div class="ambition-subsummary" data-hud="subsummary">Strike, Guard or Focus</div>

          <div class="ambition-intent-row">
            <span class="intent-pill intent-strike">Strike</span>
            <span class="intent-pill intent-guard">Guard</span>
            <span class="intent-pill intent-focus">Focus</span>
          </div>

          <button class="unleash-button" data-hud="unleash" disabled>UNLEASH</button>
          <button class="ambition-details-toggle" data-hud="details-toggle">Details</button>
          <div class="ambition-details" data-hud="details"></div>
        </div>

        <div class="ambition-panel">
          <div class="ambition-name" data-hud="enemy-name">Enemy</div>
          <div class="ambition-stat-row"><span>HP</span><strong data-hud="enemy-hp">4000</strong></div>
          <div class="ambition-stat-row"><span>Energy</span><strong data-hud="enemy-energy">2</strong></div>
          <div class="ambition-stat-row"><span>Ambition</span><strong data-hud="enemy-ambition">0</strong></div>
          <div class="ambition-stat-row"><span>Intent</span><strong data-hud="enemy-intent">-</strong></div>
          <div class="ambition-stat-row"><span>Card</span><strong data-hud="enemy-card">-</strong></div>
        </div>
      </div>
    `;

    document.body.appendChild(hud);

    hud.querySelector('[data-hud="details-toggle"]').addEventListener("click", () => {
      hud.querySelector('[data-hud="details"]').classList.toggle("open");
    });

    hud.querySelector('[data-hud="unleash"]').addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("ambition:unleash_requested"));
    });

    return hud;
  }

  function setText(hud, key, value) {
    const el = hud.querySelector(`[data-hud="${key}"]`);
    if (el) el.textContent = value;
  }

  function intentHtml(intent) {
    const cls = INTENT_CLASS[intent] || "";
    return `<span class="${cls}">${intent || "-"}</span>`;
  }

  function cardLabel(card, fallback) {
    if (!card) return fallback || "-";
    return card.name || card.title || fallback || "Card";
  }

  function syncFromGameState(payload) {
    if (!payload) return;

    const me = payload.me || {};
    const enemy = payload.enemy || {};

    state.round = payload.round ?? state.round;

    state.player.name = me.name || state.player.name;
    state.player.hp = me.hp ?? state.player.hp;
    state.player.energy = me.energy ?? state.player.energy;
    state.player.ambition = me.ambition ?? state.player.ambition;
    state.player.intent = me.wants_unleash ? "Ambition Unleash" : (me.intent || state.player.intent);
    state.player.card = cardLabel(me.field_m, "-");

    state.enemy.name = enemy.name || state.enemy.name;
    state.enemy.hp = enemy.hp ?? state.enemy.hp;
    state.enemy.energy = enemy.energy ?? state.enemy.energy;
    state.enemy.ambition = enemy.ambition ?? state.enemy.ambition;
    state.enemy.intent = enemy.wants_unleash ? "Ambition Unleash" : (enemy.intent || state.enemy.intent);
    state.enemy.card = enemy.field_m_rev
      ? cardLabel(enemy.field_m_rev, "-")
      : (enemy.field_m_status || "-");

    state.unleashReady = Boolean(me.wants_unleash) || (Number(me.ambition || 0) >= 5 && Boolean(me.field_m));
    state.summary = payload.phase || state.summary;
    state.subsummary = me.wants_unleash ? "Ambition Unleash armed" : state.subsummary;

    renderHud();
  }

  function renderHud() {
    const hud = ensureHud();

    setText(hud, "player-name", state.player.name);
    setText(hud, "player-hp", state.player.hp);
    setText(hud, "player-energy", state.player.energy);
    setText(hud, "player-ambition", state.player.ambition);
    setText(hud, "player-card", state.player.card || "-");

    setText(hud, "enemy-name", state.enemy.name);
    setText(hud, "enemy-hp", state.enemy.hp);
    setText(hud, "enemy-energy", state.enemy.energy);
    setText(hud, "enemy-ambition", state.enemy.ambition);
    setText(hud, "enemy-card", state.enemy.card || "-");

    const playerIntent = hud.querySelector('[data-hud="player-intent"]');
    const enemyIntent = hud.querySelector('[data-hud="enemy-intent"]');
    if (playerIntent) playerIntent.innerHTML = intentHtml(state.player.intent);
    if (enemyIntent) enemyIntent.innerHTML = intentHtml(state.enemy.intent);

    setText(hud, "round", `Round ${state.round}`);
    setText(hud, "summary", state.summary);
    setText(hud, "subsummary", state.subsummary);

    const unleash = hud.querySelector('[data-hud="unleash"]');
    if (unleash) {
      unleash.disabled = !state.unleashReady;
      unleash.textContent = state.unleashReady ? "UNLEASH READY" : "UNLEASH LOCKED";
    }

    const details = hud.querySelector('[data-hud="details"]');
    if (details) {
      details.innerHTML = state.details.length
        ? state.details.map(item => `<div>${item}</div>`).join("")
        : "<div>No details yet.</div>";
    }
  }

  function applyEvent(event) {
    if (!event || !event.type) return;

    switch (event.type) {
      case "round_started":
        state.round = event.round ?? state.round;
        state.summary = "Round started";
        state.subsummary = "Choose your Intent";
        state.details = [];
        break;

      case "intent_revealed":
        if (event.side === "player") state.player.intent = event.intent;
        if (event.side === "enemy") state.enemy.intent = event.intent;
        state.details.push(`${event.side} intent: ${event.intent}`);
        break;

      case "card_played":
        if (event.side === "player") state.player.card = event.card_name;
        if (event.side === "enemy") state.enemy.card = event.card_name;
        state.details.push(`${event.side} played ${event.card_name}`);
        break;

      case "power_calculated":
        state.details.push(`${event.side} power: ${event.power}`);
        break;

      case "element_bonus":
        state.details.push(`${event.side} element bonus: ${event.bonus}`);
        break;

      case "damage_dealt":
        if (event.to === "player") state.player.hp = Math.max(0, state.player.hp - event.amount);
        if (event.to === "enemy") state.enemy.hp = Math.max(0, state.enemy.hp - event.amount);
        state.details.push(`${event.to} took ${event.amount} damage`);
        break;

      case "hp_changed":
        if (event.side === "player") state.player.hp = event.value;
        if (event.side === "enemy") state.enemy.hp = event.value;
        break;

      case "ambition_gained":
        if (event.side === "player") state.player.ambition += event.amount;
        if (event.side === "enemy") state.enemy.ambition += event.amount;
        state.details.push(`${event.side} gained +${event.amount} Ambition`);
        break;

      case "ambition_changed":
        if (event.side === "player") state.player.ambition = event.value;
        if (event.side === "enemy") state.enemy.ambition = event.value;
        break;

      case "card_drawn":
        state.details.push(`${event.side} drew ${event.amount || 1} card`);
        break;

      case "energy_changed":
        if (event.side === "player") state.player.energy = event.value;
        if (event.side === "enemy") state.enemy.energy = event.value;
        break;

      case "unleash_ready":
        if (event.side === "player") state.unleashReady = Boolean(event.ready);
        break;

      case "round_summary":
        state.summary = event.title || state.summary;
        state.subsummary = event.description || state.subsummary;
        break;

      default:
        state.details.push(`${event.type}: ${JSON.stringify(event)}`);
    }
  }

  function renderRoundEvents(events) {
    if (!Array.isArray(events)) return;
    events.forEach(applyEvent);
    renderHud();
  }

  window.AmbitionHUDV2 = {
    state,
    renderHud,
    renderRoundEvents,
    applyEvent,
    syncFromGameState
  };

  document.addEventListener("DOMContentLoaded", renderHud);

  window.addEventListener("ambition:battle_events", function (e) {
    renderRoundEvents(e.detail || []);
  });

  window.addEventListener("ambition:state_update", function (e) {
    syncFromGameState(e.detail);
  });
})();
