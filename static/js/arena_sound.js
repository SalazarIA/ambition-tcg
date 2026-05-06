/* =========================================================
   Ambitionz Arena Sound FX
   Procedural Web Audio. No external audio files.
   ========================================================= */

(function () {
    const isArenaRoute = () => window.location.pathname === "/training" || window.location.pathname === "/arena";

    if (!isArenaRoute()) return;

    const Sound = {
        ctx: null,
        enabled: true,
        unlocked: false,
        masterGain: null,
    };

    function getStoredMute() {
        try {
            return localStorage.getItem("ambitionz_arena_sound_muted") === "1";
        } catch (err) {
            return false;
        }
    }

    function setStoredMute(muted) {
        try {
            localStorage.setItem("ambitionz_arena_sound_muted", muted ? "1" : "0");
        } catch (err) {}
    }

    Sound.enabled = !getStoredMute();

    function ensureContext() {
        if (Sound.ctx) return Sound.ctx;

        const AudioContext = window.AudioContext || window.webkitAudioContext;

        if (!AudioContext) {
            Sound.enabled = false;
            return null;
        }

        Sound.ctx = new AudioContext();
        Sound.masterGain = Sound.ctx.createGain();
        Sound.masterGain.gain.value = Sound.enabled ? 0.20 : 0;
        Sound.masterGain.connect(Sound.ctx.destination);

        return Sound.ctx;
    }

    function unlock() {
        const ctx = ensureContext();

        if (!ctx) return;

        if (ctx.state === "suspended") {
            ctx.resume().catch(() => {});
        }

        Sound.unlocked = true;
    }

    function setMuted(muted) {
        ensureContext();

        Sound.enabled = !muted;
        setStoredMute(muted);

        if (Sound.masterGain) {
            Sound.masterGain.gain.setTargetAtTime(Sound.enabled ? 0.20 : 0, Sound.ctx.currentTime, 0.01);
        }

        updateMuteButton();
    }

    function isMuted() {
        return !Sound.enabled;
    }

    function now() {
        const ctx = ensureContext();
        return ctx ? ctx.currentTime : 0;
    }

    function envelope(gain, start, attack, decay, peak, end) {
        gain.gain.cancelScheduledValues(start);
        gain.gain.setValueAtTime(0.0001, start);
        gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, peak), start + attack);
        gain.gain.exponentialRampToValueAtTime(Math.max(0.0001, end), start + attack + decay);
    }

    function osc({ type = "sine", freq = 440, endFreq = null, start = null, duration = 0.12, gain = 0.10, attack = 0.006, decay = 0.10 }) {
        const ctx = ensureContext();

        if (!ctx || !Sound.enabled) return;

        const t = start ?? ctx.currentTime;
        const oscillator = ctx.createOscillator();
        const g = ctx.createGain();

        oscillator.type = type;
        oscillator.frequency.setValueAtTime(freq, t);

        if (endFreq) {
            oscillator.frequency.exponentialRampToValueAtTime(Math.max(20, endFreq), t + duration);
        }

        envelope(g, t, attack, decay, gain, 0.0001);

        oscillator.connect(g);
        g.connect(Sound.masterGain);

        oscillator.start(t);
        oscillator.stop(t + duration + 0.03);
    }

    function noise({ start = null, duration = 0.12, gain = 0.08, filter = 900, type = "lowpass" }) {
        const ctx = ensureContext();

        if (!ctx || !Sound.enabled) return;

        const t = start ?? ctx.currentTime;
        const bufferSize = Math.max(1, Math.floor(ctx.sampleRate * duration));
        const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
        const data = buffer.getChannelData(0);

        for (let i = 0; i < bufferSize; i += 1) {
            data[i] = Math.random() * 2 - 1;
        }

        const source = ctx.createBufferSource();
        const g = ctx.createGain();
        const f = ctx.createBiquadFilter();

        f.type = type;
        f.frequency.setValueAtTime(filter, t);
        envelope(g, t, 0.004, duration, gain, 0.0001);

        source.buffer = buffer;
        source.connect(f);
        f.connect(g);
        g.connect(Sound.masterGain);

        source.start(t);
        source.stop(t + duration + 0.02);
    }

    const SFX = {
        uiTap() {
            unlock();
            const t = now();
            osc({ type: "triangle", freq: 620, endFreq: 780, start: t, duration: 0.055, gain: 0.035, decay: 0.045 });
        },

        intent(intent) {
            unlock();
            const t = now();

            const map = {
                Strike: [180, 260, 420],
                Guard: [220, 180, 140],
                Focus: [320, 520, 760],
            };

            const notes = map[intent] || [260, 420];

            notes.forEach((freq, index) => {
                osc({
                    type: "sine",
                    freq,
                    start: t + index * 0.045,
                    duration: 0.12,
                    gain: 0.035,
                    attack: 0.006,
                    decay: 0.12,
                });
            });
        },

        ready() {
            unlock();
            const t = now();
            osc({ type: "square", freq: 140, endFreq: 90, start: t, duration: 0.12, gain: 0.045, decay: 0.12 });
            osc({ type: "triangle", freq: 520, endFreq: 760, start: t + 0.04, duration: 0.11, gain: 0.035, decay: 0.10 });
        },

        cardSelect() {
            unlock();
            const t = now();
            osc({ type: "triangle", freq: 430, endFreq: 520, start: t, duration: 0.07, gain: 0.040, decay: 0.06 });
        },

        cardFly(element) {
            unlock();
            const t = now();

            const base = {
                Fire: 520,
                Water: 410,
                Earth: 220,
                Plant: 360,
                Global: 620,
            }[element] || 440;

            osc({ type: "sine", freq: base, endFreq: base * 1.55, start: t, duration: 0.28, gain: 0.040, decay: 0.25 });
            osc({ type: "triangle", freq: base * 0.5, endFreq: base * 0.9, start: t + 0.04, duration: 0.24, gain: 0.026, decay: 0.23 });
        },

        cardImpact(element) {
            unlock();
            const t = now();

            const hit = {
                Fire: 120,
                Water: 180,
                Earth: 80,
                Plant: 160,
                Global: 100,
            }[element] || 120;

            osc({ type: "sawtooth", freq: hit, endFreq: 45, start: t, duration: 0.16, gain: 0.060, decay: 0.15 });
            noise({ start: t, duration: 0.12, gain: 0.035, filter: element === "Water" ? 1400 : 650 });
        },

        damage() {
            unlock();
            const t = now();
            osc({ type: "sawtooth", freq: 90, endFreq: 38, start: t, duration: 0.18, gain: 0.060, decay: 0.16 });
            noise({ start: t, duration: 0.11, gain: 0.045, filter: 520 });
        },

        roundResolve() {
            unlock();
            const t = now();
            osc({ type: "triangle", freq: 180, endFreq: 120, start: t, duration: 0.18, gain: 0.040, decay: 0.16 });
            noise({ start: t + 0.02, duration: 0.12, gain: 0.032, filter: 900 });
        },

        victory() {
            unlock();
            const t = now();
            [392, 523, 659, 784].forEach((freq, index) => {
                osc({ type: "sine", freq, start: t + index * 0.09, duration: 0.22, gain: 0.040, decay: 0.20 });
            });
        },

        defeat() {
            unlock();
            const t = now();
            [220, 185, 147, 110].forEach((freq, index) => {
                osc({ type: "triangle", freq, start: t + index * 0.08, duration: 0.22, gain: 0.035, decay: 0.20 });
            });
        },
    };

    function createMuteButton() {
        if (document.querySelector("#az-sound-toggle")) return;

        const btn = document.createElement("button");
        btn.id = "az-sound-toggle";
        btn.type = "button";
        btn.className = "az-sound-toggle";
        btn.addEventListener("click", () => {
            unlock();
            setMuted(!isMuted());
        });

        document.body.appendChild(btn);
        updateMuteButton();
    }

    function updateMuteButton() {
        const btn = document.querySelector("#az-sound-toggle");

        if (!btn) return;

        btn.textContent = isMuted() ? "Sound Off" : "Sound On";
        btn.classList.toggle("is-muted", isMuted());
    }

    document.addEventListener("pointerdown", unlock, { once: true });
    document.addEventListener("keydown", unlock, { once: true });

    document.addEventListener("DOMContentLoaded", () => {
        setTimeout(createMuteButton, 500);
    });

    window.AmbitionzSound = {
        unlock,
        setMuted,
        isMuted,
        play: function (name, payload) {
            if (SFX[name]) {
                SFX[name](payload && payload.element);
            }
        },
        sfx: SFX,
    };
})();
