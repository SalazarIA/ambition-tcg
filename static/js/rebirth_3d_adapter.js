(function () {
    "use strict";

    const classByEvent = {
        "rebirth:strike": "is-strike",
        "rebirth:guard": "is-guard",
        "rebirth:focus": "is-focus",
        "rebirth:damage": "is-damage",
        "rebirth:ko": "is-ko",
        "rebirth:card_activated": "is-focus",
        "rebirth:round_end": "is-guard"
    };

    const Rebirth3D = {
        root: null,
        manifest: null,
        state: null,

        init(rootElement) {
            this.root = rootElement || document.getElementById("rebirth-3d-stage");
            if (!this.root) return;
            this.renderPlaceholder();
            const manifestUrl = window.REBIRTH_CONFIG && window.REBIRTH_CONFIG.manifestUrl;
            if (manifestUrl) {
                fetch(manifestUrl)
                    .then((response) => response.ok ? response.json() : null)
                    .then((manifest) => {
                        this.manifest = manifest;
                    })
                    .catch(() => {
                        this.manifest = null;
                    });
            }
        },

        emit(eventName, payload) {
            const normalized = String(eventName || "").startsWith("rebirth:")
                ? String(eventName)
                : `rebirth:${eventName}`;
            this.playCinematic(normalized, payload || {});
        },

        setState(state) {
            this.state = state;
            if (!this.root) return;
            const player = state && state.player ? state.player : {};
            const opponent = state && state.opponent ? state.opponent : {};
            const playerNode = this.root.querySelector("[data-rb-3d-player]");
            const opponentNode = this.root.querySelector("[data-rb-3d-opponent]");
            const frameNode = this.root.querySelector("[data-rb-3d-frame]");
            if (playerNode) playerNode.textContent = initials(player.active_card && player.active_card.name || "Player");
            if (opponentNode) opponentNode.textContent = initials(opponent.active_card && opponent.active_card.name || "Rival");
            if (frameNode) frameNode.textContent = player.active_card ? player.active_card.name : "Awaiting active card";
        },

        playCinematic(eventName, payload) {
            if (!this.root) return;
            const className = classByEvent[eventName] || "";
            if (className) {
                this.root.classList.add(className);
                window.setTimeout(() => {
                    if (this.root) this.root.classList.remove(className);
                }, eventName === "rebirth:ko" ? 1100 : 620);
            }
            this.root.setAttribute("data-rb-last-event", eventName);
            if (payload && payload.side) {
                this.root.setAttribute("data-rb-last-side", payload.side);
            }
        },

        renderPlaceholder() {
            if (!this.root) return;
            this.root.innerHTML = `
                <div class="rb-3d-scene" aria-hidden="true">
                    <i class="rb-3d-orbit"></i>
                    <i class="rb-3d-ring"></i>
                    <i class="rb-3d-core"></i>
                    <span class="rb-3d-avatar is-opponent" data-rb-3d-opponent>RV</span>
                    <span class="rb-3d-frame" data-rb-3d-frame>Awaiting active card</span>
                    <span class="rb-3d-avatar is-player" data-rb-3d-player>PL</span>
                    <i class="rb-3d-fx"></i>
                </div>
            `;
        }
    };

    function initials(name) {
        return String(name || "?")
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map((part) => part.charAt(0).toUpperCase())
            .join("");
    }

    window.Rebirth3D = Rebirth3D;
}());
