(function () {

function appendBattleEvent(message) {
  const log = document.getElementById("battle-log");

  if (!log || !message) {
    return;
  }

  const line = document.createElement("div");
  line.className = "log-line battle-event-line-v148";
  line.textContent = message;
  log.prepend(line);
}

function applyEvents(events) {
  const list = Array.isArray(events) ? events : [];

  list.forEach(e => {
    if (e.type === "intent_revealed") {
      appendBattleEvent(`${e.side || "player"} intent revealed: ${e.intent || "Strike"}.`);
    }

    if (e.type === "card_played") {
      appendBattleEvent(`${e.side || "player"} revealed ${e.card_name || "a card"} in ${e.zone || "field"}.`);
    }

    if (e.type === "damage_dealt") {
      appendBattleEvent(`${e.to || "target"} took ${e.amount || 0} damage.`);
    }

    if (e.type === "ambition_gained") {
      appendBattleEvent(`${e.side || "player"} gained ${e.amount || 0} Ambition.`);
    }

    if (e.type === "unleash_ready" && e.ready) {
      appendBattleEvent(`${e.side || "player"} can use Ambition Unleash next setup.`);
    }

    if (e.type === "round_summary") {
      appendBattleEvent(`${e.title || "Round Summary"} - ${e.description || "Battle resolved."}`);
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  window.addEventListener("ambition:battle_events", (event) => {
    applyEvents(event.detail || []);
  });
});

})();
