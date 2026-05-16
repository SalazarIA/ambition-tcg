(function () {
    "use strict";

    var manifestPromise = null;
    var manifestCards = new Map();
    var fallbackPalettes = {
        fire: ["#ff4d3d", "#ffb347", "#ffd36b"],
        water: ["#1f8cff", "#29f0ff", "#d5fbff"],
        earth: ["#2fd38f", "#8f6d3a", "#f0d18a"],
        plant: ["#23e87d", "#8cff5a", "#124d34"],
        global: ["#9b5cff", "#42f0ff", "#f8d57a"],
        neutral: ["#9b5cff", "#d7dcff", "#0bd3ff"],
    };
    var symbols = {
        fire: "F",
        water: "W",
        earth: "E",
        plant: "P",
        global: "A",
        neutral: "A",
    };

    function str(value, fallback) {
        if (value === undefined || value === null || value === "") return fallback || "";
        return String(value);
    }

    function slug(value, fallback) {
        return str(value, fallback || "neutral").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || (fallback || "neutral");
    }

    function esc(value) {
        return str(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function cardId(card) {
        return str(card && (card.id || card.card_id || card.cardId || card.dataset && card.dataset.cardId), "");
    }

    function normalizeType(value) {
        var key = slug(value || "card", "card");
        if (key === "monster" || key === "unit") return "creature";
        if (key === "magic") return "spell";
        return key;
    }

    function fallbackArt(card) {
        card = card || {};
        var element = slug(card.element || card.dataset && card.dataset.element || "neutral", "neutral");
        var type = normalizeType(card.type || card.dataset && card.dataset.type || "card");
        var rarity = slug(card.rarity || card.dataset && card.dataset.rarity || "common", "common");
        var palette = fallbackPalettes[element] || fallbackPalettes.neutral;
        return {
            id: cardId(card),
            name: str(card.name || card.dataset && card.dataset.name || "Ambitionz Card"),
            element: element,
            type: type,
            rarity: rarity,
            image: "",
            art_path: "",
            symbol: symbols[element] || "A",
            gradient: "linear-gradient(135deg, " + palette[0] + " 0%, " + palette[1] + " 52%, " + palette[2] + " 100%)",
            palette: palette,
            visual_identity: "premium fantasy neon placeholder art",
            role: "",
            simple_use_text: "",
            short_lore: "",
            placeholder: true,
        };
    }

    function normalizeManifestCard(entry) {
        var fallback = fallbackArt(entry);
        var palette = Array.isArray(entry && entry.palette) && entry.palette.length ? entry.palette : fallback.palette;
        return {
            id: str(entry && entry.id, fallback.id),
            name: str(entry && entry.name, fallback.name),
            element: slug(entry && entry.element, fallback.element),
            type: normalizeType(entry && entry.type),
            rarity: slug(entry && entry.rarity, fallback.rarity),
            image: str(entry && entry.art_path, ""),
            art_path: str(entry && entry.art_path, ""),
            symbol: str(entry && entry.symbol, fallback.symbol),
            gradient: str(entry && entry.fallback_gradient, "linear-gradient(135deg, " + palette.join(", ") + ")"),
            palette: palette,
            visual_identity: str(entry && entry.visual_identity, fallback.visual_identity),
            role: str(entry && entry.role, ""),
            simple_use_text: str(entry && entry.simple_use_text, ""),
            short_lore: str(entry && entry.short_lore, ""),
            placeholder: Boolean(!entry || entry.placeholder !== false || !entry.art_path),
        };
    }

    function applyManifest(data) {
        manifestCards = new Map();
        (Array.isArray(data && data.cards) ? data.cards : []).forEach(function (entry) {
            var normalized = normalizeManifestCard(entry || {});
            if (normalized.id) manifestCards.set(normalized.id, normalized);
        });
        return data || {};
    }

    function loadCardArtManifest() {
        if (manifestPromise) return manifestPromise;
        manifestPromise = fetch("/static/assets/cards/card_art_manifest.json", {
            credentials: "same-origin",
            cache: "no-cache",
        })
            .then(function (response) {
                if (!response.ok) throw new Error("card art manifest unavailable");
                return response.json();
            })
            .then(applyManifest)
            .catch(function () {
                applyManifest({ cards: [] });
                return { cards: [] };
            });
        return manifestPromise;
    }

    function getCardArt(card) {
        var id = cardId(card);
        if (id && manifestCards.has(id)) return manifestCards.get(id);
        return fallbackArt(card || {});
    }

    function getCardVisualClasses(card) {
        var art = getCardArt(card || {});
        return [
            "az-card-v6",
            "az-card-frame-" + art.rarity,
            "az-card-type-" + art.type,
            "az-card-element-" + art.element,
        ].join(" ");
    }

    function renderCardArt(card) {
        var art = getCardArt(card || {});
        var name = str(card && (card.name || card.dataset && card.dataset.name), art.name);
        return [
            '<div class="az-card-art-v6" style="--az-card-v6-gradient:' + esc(art.gradient) + ';">',
            art.image ? '<img src="' + esc(art.image) + '" alt="">' : "",
            '<span class="az-card-art-rune-v6" aria-hidden="true">' + esc(art.symbol) + '</span>',
            '<span class="az-card-art-name-v6">' + esc(name) + '</span>',
            '<span class="az-card-art-texture-v6" aria-hidden="true"></span>',
            '</div>',
        ].join("");
    }

    function enhanceCardElement(card) {
        if (!card || card.dataset.azCardArtEnhanced === "1") return;
        var art = getCardArt(card);
        card.dataset.azCardArtEnhanced = "1";
        card.classList.add("az-card-v6");
        getCardVisualClasses(card).split(" ").forEach(function (className) {
            if (className) card.classList.add(className);
        });
        card.style.setProperty("--az-card-v6-gradient", art.gradient);
        card.style.setProperty("--az-card-v6-symbol", art.symbol);
        if (art.role) card.dataset.cardArtRole = art.role;
        if (art.simple_use_text) card.dataset.simpleUseText = art.simple_use_text;
        if (art.short_lore) card.dataset.shortLore = art.short_lore;

        var existing = card.querySelector(".az-card-art-v6");
        if (existing) return;

        var anchor = card.querySelector(".az-card-art-v1, .card-shell, .az48-art");
        if (!anchor) return;

        if (anchor.classList.contains("card-shell")) {
            anchor.insertAdjacentHTML("afterbegin", renderCardArt(card));
        } else {
            anchor.insertAdjacentHTML("beforebegin", renderCardArt(card));
        }
    }

    function enhanceAllCards() {
        document.querySelectorAll(".collection-card[data-card-id], .builder-card[data-card-id], .az48-card[data-card-id]").forEach(enhanceCardElement);
    }

    window.AmbitionzCardArt = {
        loadCardArtManifest: loadCardArtManifest,
        getCardArt: getCardArt,
        renderCardArt: renderCardArt,
        getCardVisualClasses: getCardVisualClasses,
        enhanceAllCards: enhanceAllCards,
    };

    document.addEventListener("DOMContentLoaded", function () {
        loadCardArtManifest().then(enhanceAllCards);
    });
})();
