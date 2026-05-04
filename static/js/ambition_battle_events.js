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
