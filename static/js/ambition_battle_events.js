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
  document.getElementById("p-hp").innerText = state.player.hp;
  document.getElementById("e-hp").innerText = state.enemy.hp;
  document.getElementById("p-amb").innerText = state.player.ambition;
  document.getElementById("p-energy").innerText = state.player.energy;

  document.getElementById("p-intent").innerText = state.player.intent;
  document.getElementById("e-intent").innerText = state.enemy.intent;
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
