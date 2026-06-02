(function () {
    "use strict";

    const AUDIO_BASE = "/static/assets/rebirth/audio/";
    const AUDIO_FILES = {
        heavy: "impact_heavy.wav",
        shield: "shield_shatter.wav",
        evolution: "evolution_burst.wav",
        click: "click_metallic.wav"
    };
    const EVENT_AUDIO = {
        DAMAGE_RESOLVED: "heavy",
        SHIELD_BROKEN: "shield",
        UNIT_DESTROYED: "heavy",
        MONSTER_DESTROYED: "heavy",
        MONSTERS_FUSED: "evolution",
        EVOLUTION_COMPLETED: "evolution",
        UI_CLICK_CONFIRMED: "click"
    };

    class RebirthAudioManager {
        constructor() {
            if (RebirthAudioManager.instance) return RebirthAudioManager.instance;
            this.AudioContext = window.AudioContext || window.webkitAudioContext || null;
            this.AudioBuffer = window.AudioBuffer || null;
            this.context = null;
            this.buffers = new Map();
            this.preloadPromise = null;
            this.lastPlayed = new Map();
            this.fusionExplosionKeys = new Set();
            this.fusionExplosionLockUntil = 0;
            this.debounceMs = 90;
            this.replayAudioMutedMode = false;
            this.userMuted = window.localStorage && window.localStorage.getItem("rebirth_audio_muted") === "true";
            this.resumeOnGesture = this.resumeOnGesture.bind(this);
            window.addEventListener("click", this.resumeOnGesture, { passive: true });
            window.addEventListener("DOMContentLoaded", () => this.bindToggle());
            RebirthAudioManager.instance = this;
        }

        ensureContext() {
            if (!this.AudioContext) return null;
            if (!this.context) {
                this.context = new this.AudioContext();
            }
            return this.context;
        }

        async resumeOnGesture() {
            const context = this.ensureContext();
            if (!context || context.state !== "suspended") {
                window.removeEventListener("click", this.resumeOnGesture);
                return;
            }
            try {
                await context.resume();
                if (context.state === "running") {
                    window.removeEventListener("click", this.resumeOnGesture);
                }
            } catch (_error) {}
        }

        preload() {
            if (this.preloadPromise) return this.preloadPromise;
            const context = this.ensureContext();
            if (!context) {
                this.preloadPromise = Promise.resolve(false);
                return this.preloadPromise;
            }
            this.preloadPromise = Promise.all(
                Object.entries(AUDIO_FILES).map(async ([key, filename]) => {
                    try {
                        const response = await fetch(`${AUDIO_BASE}${filename}`, { credentials: "same-origin" });
                        if (!response.ok) return false;
                        const raw = await response.arrayBuffer();
                        const buffer = await context.decodeAudioData(raw);
                        if (this.AudioBuffer && !(buffer instanceof this.AudioBuffer)) return false;
                        this.buffers.set(key, buffer);
                        return true;
                    } catch (_error) {
                        return false;
                    }
                })
            ).then(() => true);
            return this.preloadPromise;
        }

        setReplayMutedMode(enabled) {
            this.replayAudioMutedMode = Boolean(enabled);
        }

        isMuted() {
            return Boolean(this.userMuted || this.replayAudioMutedMode);
        }

        setMuted(enabled) {
            this.userMuted = Boolean(enabled);
            try {
                window.localStorage.setItem("rebirth_audio_muted", this.userMuted ? "true" : "false");
            } catch (_error) {}
            this.syncToggle();
        }

        syncToggle() {
            const button = document.querySelector("[data-rebirth-audio-toggle]");
            if (!button) return;
            button.setAttribute("aria-pressed", this.userMuted ? "true" : "false");
            button.textContent = this.userMuted ? "Som off" : "Som";
        }

        bindToggle() {
            const button = document.querySelector("[data-rebirth-audio-toggle]");
            if (!button || button.dataset.rebirthAudioBound === "true") return;
            button.dataset.rebirthAudioBound = "true";
            this.syncToggle();
            button.addEventListener("click", () => {
                this.setMuted(!this.userMuted);
                if (!this.userMuted) {
                    this.uiClickConfirmed();
                }
            });
        }

        eventKey(event, soundKey) {
            // Dedup por chain de efeito: chains longas (até 15 eventos) reproduzem
            // um único impacto por janela do debounce. Sem effect_chain_id, cai
            // para soundKey puro como fallback estável.
            const chain = event.effect_chain_id || "";
            return chain ? `${soundKey}:${chain}` : soundKey;
        }

        fusionEventKey(event) {
            const payload = event && event.payload ? event.payload : {};
            return [
                "fusion",
                event && (event.event_id || event.id || event.sequence_id || event.replay_frame) || "",
                payload.resulting_instance_id || "",
                event && event.effect_chain_id || ""
            ].join(":");
        }

        shouldPlayFusion(event) {
            if (this.isMuted()) return false;
            const now = window.performance && window.performance.now ? window.performance.now() : Date.now();
            const key = this.fusionEventKey(event);
            if (this.fusionExplosionKeys.has(key)) return false;
            if (now < this.fusionExplosionLockUntil) return false;
            this.fusionExplosionKeys.add(key);
            if (this.fusionExplosionKeys.size > 40) {
                this.fusionExplosionKeys = new Set(Array.from(this.fusionExplosionKeys).slice(-24));
            }
            this.fusionExplosionLockUntil = now + 420;
            return true;
        }

        shouldPlay(event, soundKey) {
            if (this.isMuted()) return false;
            const eventType = String(event && (event.event_type || event.type) || "");
            if (eventType === "MONSTERS_FUSED" && soundKey === "evolution") {
                return this.shouldPlayFusion(event);
            }
            const key = this.eventKey(event, soundKey);
            const now = window.performance && window.performance.now ? window.performance.now() : Date.now();
            const previous = this.lastPlayed.get(key);
            if (previous !== undefined && now - previous < this.debounceMs) return false;
            this.lastPlayed.set(key, now);
            if (this.lastPlayed.size > 80) {
                const trim = Array.from(this.lastPlayed.keys()).slice(0, 24);
                trim.forEach((item) => this.lastPlayed.delete(item));
            }
            return true;
        }

        async play(soundKey, options) {
            const context = this.ensureContext();
            if (!context || this.userMuted) return false;
            await this.preload();
            const buffer = this.buffers.get(soundKey);
            if (!buffer) return false;
            const source = context.createBufferSource();
            const gainNode = context.createGain();
            const volume = Number(options && options.volume || 0.34);
            gainNode.gain.setValueAtTime(Math.max(0.0001, volume), context.currentTime);
            source.buffer = buffer;
            source.connect(gainNode);
            gainNode.connect(context.destination);
            const delay = Math.max(0, Number(options && options.delayMs || 0) / 1000);
            source.start(context.currentTime + delay);
            return true;
        }

        eventVolume(event, soundKey) {
            if (soundKey === "click") return 0.22;
            if (soundKey === "evolution") return 0.62;
            if (soundKey === "shield") return 0.38;
            const payload = event && event.payload ? event.payload : {};
            const heroDamage = payload.hero_damage || {};
            const damage = Math.max(
                Number(payload.amount || 0),
                Number(heroDamage.player || 0),
                Number(heroDamage.bot || 0),
                Number(payload.damage || 0)
            );
            if (soundKey === "heavy") {
                if (damage >= 5) return 0.48;
                if (damage >= 2) return 0.4;
                return 0.38;
            }
            return 0.34;
        }

        eventPriority(event, soundKey) {
            const eventType = String(event && (event.event_type || event.type) || "");
            if (eventType === "MONSTERS_FUSED") return 0;
            if (soundKey === "heavy") return 1;
            if (soundKey === "shield") return 2;
            if (soundKey === "evolution") return 3;
            return 4;
        }

        eventDelayMs(eventType, soundKey, fallbackDelayMs) {
            if (eventType === "MONSTERS_FUSED" || soundKey === "heavy") return 0;
            return fallbackDelayMs;
        }

        observeEvents(events, options) {
            const list = Array.isArray(events) ? events.slice() : [];
            this.setReplayMutedMode(Boolean(options && options.replayAudioMutedMode));
            if (!list.length || this.isMuted()) return;
            const delayMs = Math.max(0, Number(options && options.hitPauseMs || 0));
            const fusionChains = new Set(
                list
                    .filter((event) => String(event.event_type || event.type || "") === "MONSTERS_FUSED")
                    .map((event) => event.effect_chain_id)
                    .filter(Boolean)
            );
            list.sort((a, b) => {
                const frameDelta = Number(a.replay_frame || a.sequence_id || a.id || 0) - Number(b.replay_frame || b.sequence_id || b.id || 0);
                if (frameDelta) return frameDelta;
                const priorityDelta = this.eventPriority(a, EVENT_AUDIO[String(a.event_type || a.type || "")])
                    - this.eventPriority(b, EVENT_AUDIO[String(b.event_type || b.type || "")]);
                if (priorityDelta) return priorityDelta;
                return String(a.event_type || a.type || "").localeCompare(String(b.event_type || b.type || ""));
            }).forEach((event) => {
                const eventType = String(event.event_type || event.type || "");
                const soundKey = EVENT_AUDIO[eventType];
                if (!soundKey || !this.shouldPlay(event, soundKey)) return;
                if (eventType !== "MONSTERS_FUSED" && fusionChains.has(event.effect_chain_id)) return;
                this.play(soundKey, { delayMs: this.eventDelayMs(eventType, soundKey, delayMs), volume: this.eventVolume(event, soundKey) }).catch(() => false);
            });
        }

        uiClickConfirmed() {
            const event = {
                event_type: "UI_CLICK_CONFIRMED",
                event_id: "ui-click",
                effect_chain_id: "client-presentation",
                replay_frame: 0,
                sequence_id: 0
            };
            if (this.shouldPlay(event, "click")) {
                this.play("click", { volume: 0.22 }).catch(() => false);
            }
        }
    }

    window.RebirthAudioManager = new RebirthAudioManager();
})();
