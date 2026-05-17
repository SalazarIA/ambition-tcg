(function () {
    "use strict";

    function bindFilters() {
        var buttons = document.querySelectorAll("[data-ax-filter-type]");
        var cards = document.querySelectorAll("[data-ax-card-type]");
        buttons.forEach(function (button) {
            button.addEventListener("click", function () {
                var type = button.getAttribute("data-ax-filter-type");
                buttons.forEach(function (item) {
                    item.classList.toggle("is-selected", item === button);
                });
                cards.forEach(function (card) {
                    var visible = type === "all" || card.getAttribute("data-ax-card-type") === type;
                    card.hidden = !visible;
                });
            });
        });
    }

    function bindDetails() {
        var panel = document.getElementById("ax-card-detail");
        if (!panel) return;
        document.querySelectorAll("[data-ax-card-name]").forEach(function (card) {
            card.addEventListener("click", function () {
                panel.innerHTML = [
                    "<strong>" + card.getAttribute("data-ax-card-name") + "</strong>",
                    "<p>" + card.getAttribute("data-ax-card-text") + "</p>",
                    "<span>" + card.getAttribute("data-ax-card-role") + "</span>",
                    "<small>" + card.getAttribute("data-ax-card-strategy") + "</small>"
                ].join("");
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        bindFilters();
        bindDetails();
    });
}());
