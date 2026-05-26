(function () {
    "use strict";

    function number(value, fallback) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : Number(fallback || 0);
    }

    function abilityBias(card, mode) {
        const key = String((card && card.ability_key) || "").toLowerCase();
        const attackBias = {
            inferno_bite: 3,
            apex_rend: 3,
            molten_bite: 2,
            rending_strike: 2,
            silent_pursuit: 2,
            storm_dive: 2,
            bleed_mark: 1,
            fade_cut: 1,
            life_drain: 1
        };
        const guardBias = {
            bulwark: 3,
            immovable: 3,
            brace: 2,
            fortress_hit: 2,
            high_guard: 2,
            shield_bloom: 1
        };
        return mode === "attack" ? (attackBias[key] || 0) : (guardBias[key] || 0);
    }

    function cardName(card, fallback) {
        return String((card && card.name) || fallback || "unit").trim();
    }

    function clashRisk(attacker, defender) {
        if (!attacker) {
            return {
                tone: "neutral",
                label: "Select attacker",
                copy: "Choose a ready unit first.",
                score: 0
            };
        }
        if (!defender) {
            return {
                tone: "favorable",
                label: "Strong advantage",
                copy: "Open lane. Direct pressure is available.",
                score: 4
            };
        }

        const attack = number(attacker.attack || attacker.power, 0) + abilityBias(attacker, "attack");
        const guard = number(attacker.current_guard != null ? attacker.current_guard : attacker.guard, 0) + abilityBias(attacker, "guard");
        const defense = number(defender.current_guard != null ? defender.current_guard : defender.guard, 0) + abilityBias(defender, "guard");
        const counter = number(defender.attack || defender.power, 0) + abilityBias(defender, "attack");
        const breakMargin = attack - defense;
        const survivalMargin = guard - counter;
        const score = breakMargin + Math.min(2, survivalMargin);

        if (breakMargin >= 2 && survivalMargin >= 0) {
            return {
                tone: "favorable",
                label: "Strong advantage",
                copy: cardName(attacker, "Your unit") + " is favored into " + cardName(defender, "the enemy") + ".",
                score
            };
        }
        if (breakMargin >= 0 && survivalMargin >= -2) {
            return {
                tone: "risky",
                label: "Trade likely",
                copy: cardName(attacker, "Your unit") + " can trade, but may lose guard.",
                score
            };
        }
        return {
            tone: "losing",
            label: "High chance to lose unit",
            copy: cardName(defender, "Enemy unit") + " has the better clash profile.",
            score
        };
    }

    function actionCopy(context) {
        const state = context.state || {};
        const selected = context.selected || null;
        const selectedAttacker = context.selectedAttacker || null;
        const risk = context.risk || null;
        const cost = number(context.cost, 0);
        const energy = number(context.energy, 0);

        if (state.is_finished) return "Match ended. Start another duel.";
        if (state.phase === "result") return "Resolved - advance the turn.";
        if (context.pending) return "Resolving action...";
        if (selectedAttacker) {
            if (context.directLocked) return "Direct attack locked until bot responds.";
            if (!context.attackerReady) return "This unit already acted.";
            if (risk && risk.tone === "losing") return "Risky attack detected.";
            if (risk && risk.tone === "risky") return "Trade likely.";
            return "Attack enemy unit.";
        }
        if (!selected) return "Choose the best card first.";
        if (!context.canPay) return "Not enough mana.";
        if (context.noOpenSlot) return "No monster slot open.";
        return "Play " + cardName(selected).toUpperCase() + (cost ? " (" + cost + " mana)." : ".");
    }

    function resultLine(state) {
        const clash = (state && state.last_clash) || {};
        const result = (state && state.result) || {};
        const player = clash.player_card || {};
        const bot = clash.bot_card || {};
        const outcome = String(result.outcome || "");

        if (outcome === "Victory") {
            return cardName(player, "Your unit") + " broke " + cardName(bot, "enemy unit") + ".";
        }
        if (outcome === "Defeat") {
            return cardName(bot, "Enemy unit") + " destroyed " + cardName(player, "your unit") + ".";
        }
        if (outcome === "Clash") {
            return cardName(player, "Your unit") + " traded with " + cardName(bot, "enemy unit") + ".";
        }
        return result.message || "";
    }

    window.RebirthHotfixUI = {
        clashRisk,
        actionCopy,
        resultLine
    };
})();
