(function () {
    "use strict";

    let activeMatchId = null;
    let introTimer = null;

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function board() {
        return document.getElementById("rebirth-board");
    }

    function clearIntro() {
        const overlay = document.getElementById("rebirth-boss-intro");
        if (!overlay) return;
        overlay.classList.remove("is-active");
        overlay.setAttribute("aria-hidden", "true");
    }

    function clearAdvice() {
        const host = document.getElementById("campaign-defeat-advice");
        if (!host) return;
        host.hidden = true;
        host.innerHTML = "";
    }

    function reset() {
        activeMatchId = null;
        window.clearTimeout(introTimer);
        clearIntro();
        clearAdvice();
        const host = board();
        if (!host) return;
        host.classList.remove("is-campaign-boss", "is-boss-defeated");
        host.removeAttribute("data-boss-tone");
        host.removeAttribute("data-boss-intensity");
        host.style.removeProperty("--boss-accent");
    }

    function applyTheme(campaign) {
        const host = board();
        if (!host) return;
        const presentation = campaign.presentation || {};
        host.classList.add("is-campaign-boss");
        host.dataset.bossTone = presentation.tone || "fire";
        host.dataset.bossIntensity = presentation.intensity || "normal";
        host.style.setProperty("--boss-accent", presentation.accent || "#c79949");
    }

    function showIntro(campaign) {
        const overlay = document.getElementById("rebirth-boss-intro");
        if (!overlay) return;
        const presentation = campaign.presentation || {};
        const order = String(presentation.order || "").padStart(2, "0");
        const title = presentation.title || presentation.name || "Encontro";
        overlay.innerHTML = [
            '<span class="rb-boss-intro-kicker">Encontro ' + escapeHtml(order) + "</span>",
            "<strong>" + escapeHtml(title) + "</strong>",
            "<p>" + escapeHtml(presentation.name || "") + "</p>"
        ].join("");
        overlay.classList.add("is-active");
        overlay.setAttribute("aria-hidden", "false");
        window.clearTimeout(introTimer);
        introTimer = window.setTimeout(clearIntro, 1450);
    }

    function renderDefeatAdvice(state) {
        const host = document.getElementById("campaign-defeat-advice");
        const campaign = state && state.campaign;
        const advice = campaign && campaign.defeat_advice;
        if (!host || !state.is_finished || state.winner !== "bot" || !advice) {
            clearAdvice();
            return;
        }
        const keyCard = advice.key_card || {};
        host.hidden = false;
        host.innerHTML = [
            "<strong>Leitura para a revanche</strong>",
            "<p>" + escapeHtml(advice.tip || "Ajuste sua abertura e tente novamente.") + "</p>",
            keyCard.name ? '<span>Carta-chave inimiga: <b>' + escapeHtml(keyCard.name) + "</b></span>" : ""
        ].join("");
    }

    function observe(previousState, nextState) {
        if (!nextState || !nextState.campaign) {
            if (activeMatchId) reset();
            return;
        }
        applyTheme(nextState.campaign);
        if (activeMatchId !== nextState.match_id) {
            activeMatchId = nextState.match_id;
            showIntro(nextState.campaign);
        }
        renderDefeatAdvice(nextState);
        const host = board();
        if (host && nextState.is_finished && nextState.winner === "player") {
            host.classList.add("is-boss-defeated");
        }
    }

    window.RebirthBossFX = {
        observe: observe,
        reset: reset
    };
})();
