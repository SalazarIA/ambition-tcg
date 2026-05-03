(function () {

let hud;

function createHUD() {
  hud = document.createElement("div");
  hud.className = "ambition-hud-v2";

  hud.innerHTML = `
    <div class="row">
      <div>HP: <span id="p-hp">0</span></div>
      <div>Enemy HP: <span id="e-hp">0</span></div>
    </div>
    <div class="row">
      <div>Ambition: <span id="p-amb">0</span></div>
      <div>Energy: <span id="p-energy">0</span></div>
    </div>
    <div class="row">
      <div class="intent" id="p-intent">-</div>
      <div class="intent" id="e-intent">-</div>
    </div>
    <div id="summary"></div>
    <button class="unleash-btn" id="unleashBtn">UNLEASH</button>
  `;

  document.body.appendChild(hud);

  document.getElementById("unleashBtn").onclick = () => {
    if (window.socket) {
      window.socket.emit("toggle_unleash", {});
    }
  };
}

function updateHUD(state) {
  const player = state.player || state.me || {};
  const enemy = state.enemy || {};

  document.getElementById("p-hp").innerText = player.hp ?? 0;
  document.getElementById("e-hp").innerText = enemy.hp ?? 0;
  document.getElementById("p-amb").innerText = player.ambition ?? 0;
  document.getElementById("p-energy").innerText = player.energy ?? 0;

  document.getElementById("p-intent").innerText = player.intent || "-";
  document.getElementById("e-intent").innerText = enemy.intent || "-";
}

function applyEvents(events) {
  let summary = "";

  events.forEach(e => {
    if (e.type === "round_summary") {
      summary = e.title + " - " + e.description;
    }
  });

  document.getElementById("summary").innerText = summary;
}

document.addEventListener("DOMContentLoaded", () => {
  createHUD();

  if (window.socket) {
    window.socket.on("battle_events", (events) => {
      applyEvents(events);
    });

    window.socket.on("game_state_update", (state) => {
      updateHUD(state);
    });
  }
});

})();
