(function () {
    "use strict";

    function defaultEscape(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function render(reward, escapeFn) {
        const recap = reward && reward.recap;
        if (!recap || !Array.isArray(recap.bullets) || !recap.bullets.length) {
            return "";
        }
        const esc = typeof escapeFn === "function" ? escapeFn : defaultEscape;
        const bullets = recap.bullets
            .slice(0, 4)
            .map((item) => "<li>" + esc(item) + "</li>")
            .join("");
        return [
            '<section class="rb-postmatch-recap" data-outcome="' + esc(recap.outcome || "match") + '">',
            "<strong>" + esc(recap.title || "Resumo da partida") + "</strong>",
            "<ul>" + bullets + "</ul>",
            recap.next_step ? "<p>" + esc(recap.next_step) + "</p>" : "",
            "</section>"
        ].join("");
    }

    window.RebirthPostMatchRecap = { render };
}());
