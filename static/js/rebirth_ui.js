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
                label: "Selecione o atacante",
                copy: "Escolha primeiro uma unidade pronta.",
                score: 0
            };
        }
        if (!defender) {
            return {
                tone: "favorable",
                label: "Vantagem forte",
                copy: "Linha aberta. Pressão direta disponível.",
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
                label: "Vantagem forte",
                copy: cardName(attacker, "Sua unidade") + " tem vantagem contra " + cardName(defender, "o inimigo") + ".",
                score
            };
        }
        if (breakMargin >= 0 && survivalMargin >= -2) {
            return {
                tone: "risky",
                label: "Troca provável",
                copy: cardName(attacker, "Sua unidade") + " pode trocar, mas deve perder Guarda.",
                score
            };
        }
        return {
            tone: "losing",
            label: "Alto risco de perder",
            copy: cardName(defender, "A unidade inimiga") + " leva vantagem no confronto.",
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

        if (state.is_finished) return "Partida encerrada. Inicie outro duelo.";
        if (state.phase === "result") return "Resolvido - avance o turno.";
        if (context.pending) return "Resolvendo ação...";
        if (selectedAttacker) {
            if (context.directLocked) return "Ataque direto bloqueado até o bot responder.";
            if (!context.attackerReady) return "Esta unidade já agiu.";
            if (risk && risk.tone === "losing") return "Ataque arriscado detectado.";
            if (risk && risk.tone === "risky") return "Troca provável.";
            return "Ataque a unidade inimiga.";
        }
        if (!selected) return "Escolha a melhor carta primeiro.";
        if (!context.canPay) return "Mana insuficiente.";
        if (context.noOpenSlot) return "Não há slot aberto para monstro.";
        return "Jogue " + cardName(selected).toUpperCase() + (cost ? " (" + cost + " mana)." : ".");
    }

    function resultLine(state) {
        const clash = (state && state.last_clash) || {};
        const result = (state && state.result) || {};
        const player = clash.player_card || {};
        const bot = clash.bot_card || {};
        const outcome = String(result.outcome || "");

        if (outcome === "Victory") {
            return cardName(player, "Sua unidade") + " destruiu " + cardName(bot, "a unidade inimiga") + ".";
        }
        if (outcome === "Defeat") {
            return cardName(bot, "A unidade inimiga") + " destruiu " + cardName(player, "sua unidade") + ".";
        }
        if (outcome === "Clash") {
            return cardName(player, "Sua unidade") + " trocou com " + cardName(bot, "a unidade inimiga") + ".";
        }
        return result.message || "";
    }

    window.RebirthHotfixUI = {
        clashRisk,
        actionCopy,
        resultLine
    };
})();
