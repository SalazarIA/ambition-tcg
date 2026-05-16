/* =========================================================
   Ambitionz Card System JS
   Adds progressive interaction to card grids.
   ========================================================= */

(function () {
    function isArenaPage() {
        return window.location.pathname === "/training" || window.location.pathname === "/arena";
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
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
            var matchesRole = !filters.role || card.dataset.role === filters.role || card.dataset.cardArtRole === filters.role;
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
        var serverRecent = [];
        var serverData = document.getElementById("az-recent-unlocks-data");

        if (serverData) {
            try {
                serverRecent = JSON.parse(serverData.textContent || "[]");
                if (!Array.isArray(serverRecent)) serverRecent = [];
                serverRecent = serverRecent.map(String).filter(Boolean);
            } catch (error) {
                serverRecent = [];
            }
        }

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

        if (serverRecent.length) {
            newlyOwned = ownedIds.filter(function (id) {
                return serverRecent.indexOf(id) !== -1;
            });
        }

        if (!previous.length && !serverRecent.length) {
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

    function cardArtHtml(card) {
        if (window.AmbitionzCardArt && typeof window.AmbitionzCardArt.renderCardArt === "function") {
            return window.AmbitionzCardArt.renderCardArt(card);
        }

        var element = card.dataset.element || "Neutral";
        return '<div class="az-card-art-v6"><span class="az-card-art-rune-v6">' + escapeHtml(element.slice(0, 1).toUpperCase()) + '</span><span class="az-card-art-name-v6">' + escapeHtml(card.dataset.name || "Card") + '</span></div>';
    }

    function ensureCollectionModal() {
        var modal = document.getElementById("az-collection-card-modal");
        if (modal) return modal;

        modal = document.createElement("aside");
        modal.id = "az-collection-card-modal";
        modal.className = "az-collection-card-modal-v6";
        modal.hidden = true;
        modal.setAttribute("aria-label", "Card detail");
        modal.innerHTML = [
            '<div class="az-collection-modal-backdrop-v6" data-card-modal-close></div>',
            '<article class="az-collection-modal-panel-v6">',
            '<button type="button" class="az-collection-modal-close-v6" data-card-modal-close aria-label="Close card detail">Close</button>',
            '<div id="az-collection-modal-art"></div>',
            '<div class="az-collection-modal-copy-v6">',
            '<span id="az-collection-modal-meta">Card</span>',
            '<h2 id="az-collection-modal-title">Card detail</h2>',
            '<p id="az-collection-modal-text">Inspect card identity.</p>',
            '<dl id="az-collection-modal-stats"></dl>',
            '<div class="progression-action-row">',
            '<a class="btn" href="/deck-builder">Open Deck Builder</a>',
            '<a class="btn btn-secondary" href="/shop">Open Booster</a>',
            '</div>',
            '</div>',
            '</article>',
        ].join("");
        document.body.appendChild(modal);
        return modal;
    }

    function openCollectionModal(card) {
        if (!card) return;
        var modal = ensureCollectionModal();
        var name = card.querySelector(".az-card-body-v1 strong, .card-topline strong")?.textContent || card.dataset.name || "Card";
        var type = card.dataset.type || "Card";
        var element = card.dataset.element || "Neutral";
        var rarity = card.dataset.rarity || "Common";
        var art = window.AmbitionzCardArt && typeof window.AmbitionzCardArt.getCardArt === "function"
            ? window.AmbitionzCardArt.getCardArt(card)
            : {};
        var owned = Number(card.dataset.owned || 0);
        var ownership = card.dataset.ownership || (owned > 0 ? "owned" : "locked");
        var role = card.dataset.cardArtRole || card.dataset.role || art.role || "Flexible";
        var howToUse = card.dataset.simpleUseText || art.simple_use_text || "Play this card when its cost and type fit the round.";
        var description = card.dataset.shortLore || art.short_lore || card.dataset.lore || card.dataset.effect || "Ambitionz beta card identity.";

        modal.querySelector("#az-collection-modal-art").innerHTML = cardArtHtml(card);
        modal.querySelector("#az-collection-modal-title").textContent = name;
        modal.querySelector("#az-collection-modal-meta").textContent = [rarity, element, type].filter(Boolean).join(" / ");
        modal.querySelector("#az-collection-modal-text").textContent = description + " How to use: " + howToUse;
        modal.querySelector("#az-collection-modal-stats").innerHTML = [
            ["Type", type],
            ["Element", element],
            ["Rarity", rarity],
            ["Faction", card.dataset.faction || "Arcane Neutral"],
            ["Role", role],
            ["How to use", howToUse],
            ["Status", ownership === "owned" ? "Owned x" + owned : "Locked"],
        ].map(function (row) {
            return '<div><dt>' + escapeHtml(row[0]) + '</dt><dd>' + escapeHtml(row[1]) + '</dd></div>';
        }).join("");
        modal.hidden = false;
        modal.classList.add("is-open");
        document.body.classList.add("az-card-modal-open-v6");
    }

    function closeCollectionModal() {
        var modal = document.getElementById("az-collection-card-modal");
        if (!modal) return;
        modal.hidden = true;
        modal.classList.remove("is-open");
        document.body.classList.remove("az-card-modal-open-v6");
    }

    function bindCollectionModal() {
        document.addEventListener("click", function (event) {
            var close = event.target.closest("[data-card-modal-close]");
            if (close) {
                event.preventDefault();
                closeCollectionModal();
                return;
            }

            var card = event.target.closest(".az-game-collection-page .collection-card[data-card-id]");
            if (!card || event.target.closest("a, button, input, select, label")) return;
            event.preventDefault();
            openCollectionModal(card);
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") closeCollectionModal();
        });
    }

    document.addEventListener("DOMContentLoaded", enhanceCards);
    document.addEventListener("DOMContentLoaded", bindCollectionFilters);
    document.addEventListener("DOMContentLoaded", bindCollectionModal);
    document.addEventListener("DOMContentLoaded", markRecentlyUnlockedCards);
    document.addEventListener("DOMContentLoaded", filterCollectionCards);
    window.filterCollectionCards = filterCollectionCards;
})();
