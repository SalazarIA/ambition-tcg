(function () {
    "use strict";

    function reducedMotion() {
        return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    function wait(ms) {
        return new Promise((resolve) => window.setTimeout(resolve, Math.max(0, Number(ms || 0))));
    }

    function addRestartedClass(node, className, duration) {
        if (!node || reducedMotion()) return;
        node.classList.remove(className);
        void node.offsetWidth;
        node.classList.add(className);
        window.setTimeout(() => {
            node.classList.remove(className);
        }, Math.max(80, Number(duration || 420)));
    }

    function damageAmount(result, side) {
        const damage = (result && result.damage) || {};
        const hero = Number(damage[side] || 0);
        if (hero > 0) return hero;
        const guard = (result && result.guard_damage) || {};
        return Math.max(0, Number(guard[side] || 0));
    }

    function spawnNumber(node, amount, label) {
        if (!node || !amount || reducedMotion()) return;
        const chip = document.createElement("span");
        chip.className = "rb-damage-number";
        chip.textContent = "-" + amount + (label ? " " + label : "");
        chip.setAttribute("aria-hidden", "true");
        node.appendChild(chip);
        window.setTimeout(() => {
            if (chip.parentNode) chip.parentNode.removeChild(chip);
        }, 720);
    }

    async function hitStop(node, ms) {
        if (!node || reducedMotion()) return;
        node.classList.add("is-hit-paused");
        await wait(Math.min(90, Math.max(60, Number(ms || 72))));
        node.classList.remove("is-hit-paused");
    }

    function clashImpact(options) {
        const attacker = options && options.attacker;
        const target = options && options.target;
        const state = options && options.resolvedState;
        const result = (state && state.result) || {};
        const winner = String(result.winner || "");

        let winnerNode = null;
        let loserNode = null;
        if (winner === "player") {
            winnerNode = attacker;
            loserNode = target;
        } else if (winner === "bot") {
            winnerNode = target;
            loserNode = attacker;
        }

        addRestartedClass(winnerNode, "is-combat-winner", 680);
        addRestartedClass(loserNode, "is-combat-loser", 680);

        spawnNumber(attacker, damageAmount(result, "player"), "HP");
        spawnNumber(target, damageAmount(result, "bot"), "HP");

        if (String(result.outcome || "").toLowerCase() === "clash") {
            addRestartedClass(attacker, "is-combat-trading", 620);
            addRestartedClass(target, "is-combat-trading", 620);
        }
    }

    window.RebirthHotfixFX = {
        hitStop,
        clashImpact
    };
})();
