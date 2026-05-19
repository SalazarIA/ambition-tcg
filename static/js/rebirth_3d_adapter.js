(function () {
    "use strict";

    const eventFlash = {
        "rebirth:strike": "strike",
        "rebirth:guard": "guard",
        "rebirth:focus": "focus",
        "rebirth:damage": "damage",
        "rebirth:ko": "ko",
        "rebirth:card_activated": "focus",
        "rebirth:round_end": "guard",
        "rebirth:round_resolved": "focus"
    };

    const Rebirth3D = {
        root: null,
        manifest: null,
        state: null,
        activeIntent: null,
        winner: null,

        init(rootElement) {
            this.root = rootElement || document.getElementById("rebirth-3d-stage");
            if (!this.root) return;
            this.renderPlaceholder();
            this.loadManifest();
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
            const coreNode = this.root.querySelector("[data-rb-3d-core]");
            if (playerNode) playerNode.textContent = initials(player.active_card && player.active_card.name || "Player");
            if (opponentNode) opponentNode.textContent = initials(opponent.active_card && opponent.active_card.name || "Rival");
            if (frameNode) {
                frameNode.textContent = player.active_card ? player.active_card.name : "Awaiting active card";
                frameNode.classList.toggle("has-card", Boolean(player.active_card));
            }
            if (coreNode) coreNode.setAttribute("aria-label", `Ambition ${player.ambition || 0}`);
            this.setActiveIntent(player.selected_intent || null);
            this.setWinner(state && state.is_finished ? state.winner : null);
        },

        playCinematic(eventName, payload) {
            if (!this.root) return;
            this.root.setAttribute("data-rb-last-event", eventName);

            if (eventName === "rebirth:match_start") {
                this.root.classList.remove("is-ko", "has-winner");
                this.setWinner(null);
                this.flash("focus");
                return;
            }

            if (eventName === "rebirth:intent_selected") {
                this.setActiveIntent(payload.intent || null);
                if (payload.intent) this.flash(String(payload.intent).toLowerCase());
                return;
            }

            if (eventName === "rebirth:card_activated") {
                const frameNode = this.root.querySelector("[data-rb-3d-frame]");
                if (frameNode && payload.card_name) frameNode.textContent = payload.card_name;
                this.flash("focus");
                return;
            }

            if (eventName === "rebirth:ko") {
                this.setWinner(payload.winner || "unknown");
            }

            this.flash(eventFlash[eventName] || "focus");
        },

        renderPlaceholder() {
            if (!this.root) return;
            // Future Three.js/GLB renderer enters here: preserve this DOM contract as the HUD-to-scene adapter.
            this.root.innerHTML = `
                <div class="rb-3d-scene" aria-hidden="true">
                    <i class="rb-stage-depth"></i>
                    <i class="rb-arena-orbit"></i>
                    <i class="rb-energy-core" data-rb-3d-core></i>
                    <span class="rb-avatar-node is-opponent" data-rb-3d-opponent>RV</span>
                    <span class="rb-card-frame-hologram" data-rb-3d-frame>Awaiting active card</span>
                    <span class="rb-avatar-node is-player" data-rb-3d-player>PL</span>
                    <i class="rb-fx-ring" data-rb-3d-fx></i>
                </div>
            `;
        },

        loadManifest() {
            const manifestUrl = window.REBIRTH_CONFIG && window.REBIRTH_CONFIG.manifestUrl;
            if (!manifestUrl || typeof fetch !== "function") {
                this.manifest = null;
                return Promise.resolve(null);
            }
            return fetch(manifestUrl)
                .then((response) => response.ok ? response.json() : null)
                .then((manifest) => {
                    this.manifest = manifest;
                    return manifest;
                })
                .catch(() => {
                    this.manifest = null;
                    return null;
                });
        },

        flash(type) {
            if (!this.root) return;
            const className = `is-${String(type || "focus").toLowerCase()}`;
            this.root.classList.add(className);
            this.spawnParticles(type, type === "ko" ? 18 : 10);
            window.setTimeout(() => {
                if (this.root && className !== "is-ko") this.root.classList.remove(className);
            }, type === "ko" ? 1200 : 620);
        },

        spawnParticles(type, count) {
            if (!this.root) return;
            const scene = this.root.querySelector(".rb-3d-scene");
            if (!scene) return;
            const color = colorFor(type);
            const total = Math.max(1, Math.min(24, Number(count || 8)));
            for (let index = 0; index < total; index += 1) {
                const particle = document.createElement("i");
                particle.className = "rb-particle";
                particle.style.color = color;
                particle.style.left = `${45 + Math.sin(index * 1.7) * 18}%`;
                particle.style.top = `${48 + Math.cos(index * 1.3) * 12}%`;
                particle.style.setProperty("--rb-px", `${Math.cos(index) * 46}px`);
                particle.style.setProperty("--rb-py", `${-32 - (index % 6) * 9}px`);
                scene.appendChild(particle);
                window.setTimeout(() => particle.remove(), 820);
            }
        },

        setActiveIntent(intent) {
            this.activeIntent = intent ? String(intent).toUpperCase() : null;
            if (!this.root) return;
            this.root.classList.remove("intent-strike", "intent-guard", "intent-focus");
            if (this.activeIntent) {
                this.root.classList.add(`intent-${this.activeIntent.toLowerCase()}`);
                this.root.setAttribute("data-rb-active-intent", this.activeIntent);
            } else {
                this.root.removeAttribute("data-rb-active-intent");
            }
        },

        setWinner(winner) {
            this.winner = winner || null;
            if (!this.root) return;
            this.root.classList.toggle("has-winner", Boolean(this.winner));
            if (this.winner) {
                this.root.setAttribute("data-rb-winner", this.winner);
                this.root.classList.add("is-ko");
            } else {
                this.root.removeAttribute("data-rb-winner");
                this.root.classList.remove("is-ko", "has-winner");
            }
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

    function colorFor(type) {
        const key = String(type || "").toLowerCase();
        if (key === "strike" || key === "damage" || key === "ko") return "#ff8d46";
        if (key === "guard") return "#74d8ff";
        if (key === "focus") return "#8b6cff";
        return "#e5b15b";
    }

    window.Rebirth3D = Rebirth3D;
}());
