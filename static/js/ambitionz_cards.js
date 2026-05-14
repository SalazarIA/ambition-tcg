/* =========================================================
   Ambitionz Card System JS
   Adds progressive interaction to card grids.
   ========================================================= */

(function () {
    function isArenaPage() {
        return window.location.pathname === "/training" || window.location.pathname === "/arena";
    }

    function collectionFilterValues() {
        function value(id) {
            var element = document.getElementById(id);
            return element ? element.value : "";
        }

        return {
            search: value("collection-search").toLowerCase().trim(),
            type: value("filter-type"),
            element: value("filter-element"),
            sigil: value("filter-sigil"),
            role: value("filter-role"),
            faction: value("filter-faction"),
            rarity: value("filter-rarity"),
            ownership: value("filter-ownership")
        };
    }

    function filterCollectionCards() {
        var controlsExist = document.getElementById("collection-search");
        if (!controlsExist) return;

        var filters = collectionFilterValues();
        var visibleCount = 0;

        document.querySelectorAll(".az-game-collection-page .collection-card").forEach(function (card) {
            var matchesSearch = !filters.search || (card.dataset.name || "").indexOf(filters.search) !== -1;
            var matchesType = !filters.type || card.dataset.type === filters.type;
            var matchesElement = !filters.element || card.dataset.element === filters.element;
            var matchesSigil = !filters.sigil || card.dataset.sigil === filters.sigil;
            var matchesRole = !filters.role || card.dataset.role === filters.role;
            var matchesFaction = !filters.faction || card.dataset.faction === filters.faction;
            var matchesRarity = !filters.rarity || card.dataset.rarity === filters.rarity;
            var matchesOwnership = !filters.ownership || card.dataset.ownership === filters.ownership;
            var visible = (
                matchesSearch &&
                matchesType &&
                matchesElement &&
                matchesSigil &&
                matchesRole &&
                matchesFaction &&
                matchesRarity &&
                matchesOwnership
            );

            card.hidden = !visible;
            card.style.display = visible ? "" : "none";
            if (visible) visibleCount += 1;
        });

        var empty = document.getElementById("az-collection-no-results");
        if (empty) {
            empty.hidden = visibleCount !== 0;
        }

        var visible = document.getElementById("az-collection-visible-count");
        if (visible) {
            visible.textContent = String(visibleCount);
        }
    }

    function bindCollectionFilters() {
        [
            "collection-search",
            "filter-type",
            "filter-element",
            "filter-sigil",
            "filter-role",
            "filter-faction",
            "filter-rarity",
            "filter-ownership"
        ].forEach(function (id) {
            var element = document.getElementById(id);
            if (!element) return;

            var eventName = element.tagName === "INPUT" ? "input" : "change";
            element.addEventListener(eventName, filterCollectionCards);
        });

        document.querySelectorAll("[data-clear-collection-filters]").forEach(function (button) {
            button.addEventListener("click", function () {
                [
                    "collection-search",
                    "filter-type",
                    "filter-element",
                    "filter-sigil",
                    "filter-role",
                    "filter-faction",
                    "filter-rarity",
                    "filter-ownership"
                ].forEach(function (id) {
                    var element = document.getElementById(id);
                    if (element) element.value = "";
                });

                filterCollectionCards();
            });
        });
    }

    function enhanceCards() {
        if (isArenaPage()) return;

        document.querySelectorAll(".collection-card, .image-card").forEach(function (card, index) {
            card.dataset.azCard = "1";
            card.style.setProperty("--az-card-index", index);

            if (!card.getAttribute("tabindex")) {
                card.setAttribute("tabindex", "0");
            }

            card.addEventListener("keydown", function (event) {
                if (event.key === "Enter" || event.key === " ") {
                    var button = card.querySelector("button, a, input");
                    if (button) {
                        event.preventDefault();
                        button.click();
                    }
                }
            });
        });

        document.querySelectorAll(".card-grid, .deck-builder-grid, .mobile-card-grid").forEach(function (grid) {
            grid.classList.add("az-card-grid");
        });
    }

    function markRecentlyUnlockedCards() {
        var cards = Array.from(document.querySelectorAll(".az-game-collection-page .collection-card[data-card-id]"));
        if (!cards.length) return;

        var ownedIds = cards
            .filter(function (card) {
                return Number(card.dataset.owned || 0) > 0;
            })
            .map(function (card) {
                return card.dataset.cardId;
            })
            .filter(Boolean);

        var storageKey = "ambitionz_collection_owned_snapshot_v1";
        var previous = [];

        try {
            previous = JSON.parse(window.localStorage.getItem(storageKey) || "[]");
        } catch (error) {
            previous = [];
        }

        var previousSet = new Set(Array.isArray(previous) ? previous : []);
        var newSet = new Set(ownedIds);
        var newlyOwned = ownedIds.filter(function (id) {
            return !previousSet.has(id);
        });

        if (!previous.length) {
            newlyOwned = ownedIds.slice(0, 3);
        }

        cards.forEach(function (card) {
            var isNew = newlyOwned.indexOf(card.dataset.cardId) !== -1;
            card.classList.toggle("is-recently-unlocked", isNew);
            var badge = card.querySelector("[data-new-card-badge]");
            if (badge) badge.hidden = !isNew;
        });

        try {
            window.localStorage.setItem(storageKey, JSON.stringify(Array.from(newSet)));
        } catch (error) {}
    }

    document.addEventListener("DOMContentLoaded", enhanceCards);
    document.addEventListener("DOMContentLoaded", bindCollectionFilters);
    document.addEventListener("DOMContentLoaded", markRecentlyUnlockedCards);
    document.addEventListener("DOMContentLoaded", filterCollectionCards);
    window.filterCollectionCards = filterCollectionCards;
})();
