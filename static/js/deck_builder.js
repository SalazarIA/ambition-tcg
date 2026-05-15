const DECK_LIMITS = {
    total: 30,
    Monster: 21,
    Spell: 6,
    Trap: 3,
    maxCopies: 3
};

function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function getBuilderCards() {
    return Array.from(document.querySelectorAll(".builder-card"));
}

function getCardElement(cardId) {
    return document.querySelector(`.builder-card[data-card-id="${cardId}"]`);
}

function getSelectedInputs(cardId) {
    const container = document.getElementById(`inputs-${cardId}`);

    if (!container) {
        return [];
    }

    return Array.from(container.querySelectorAll('input[name="deck_cards"]'));
}

function getCurrentCounts() {
    const counts = {
        total: 0,
        Monster: 0,
        Spell: 0,
        Trap: 0,
        totalCost: 0,
        duplicates: 0,
        maxCopiesUsed: 0,
        highCostCards: 0,
        elements: {}
    };

    getBuilderCards().forEach((card) => {
        const selected = getSelectedInputs(card.dataset.cardId).length;
        const type = card.dataset.type;
        const cost = Number(card.dataset.cost || 1);
        const element = card.dataset.element || "Neutral";

        counts.total += selected;
        counts[type] += selected;
        counts.totalCost += selected * cost;
        counts.highCostCards += cost >= 4 ? selected : 0;
        counts.elements[element] = (counts.elements[element] || 0) + selected;

        if (selected > 1) {
            counts.duplicates += 1;
        }

        counts.maxCopiesUsed = Math.max(counts.maxCopiesUsed, selected);
    });

    return counts;
}

function isDeckValid(counts) {
    return (
        counts.total === DECK_LIMITS.total &&
        counts.Monster === DECK_LIMITS.Monster &&
        counts.Spell === DECK_LIMITS.Spell &&
        counts.Trap === DECK_LIMITS.Trap &&
        counts.maxCopiesUsed <= DECK_LIMITS.maxCopies
    );
}

function updateCardSelectionStates() {
    getBuilderCards().forEach((card) => {
        const selected = getSelectedInputs(card.dataset.cardId).length;
        const countEl = document.getElementById(`count-${card.dataset.cardId}`);

        if (countEl) {
            countEl.textContent = selected;
        }

        card.dataset.selected = selected;
        card.classList.toggle("is-in-deck", selected > 0);
        card.classList.toggle("is-at-copy-limit", selected >= DECK_LIMITS.maxCopies);
    });
}

function updateCopyButtons() {
    const counts = getCurrentCounts();

    getBuilderCards().forEach((card) => {
        const cardId = card.dataset.cardId;
        const selected = getSelectedInputs(cardId).length;
        const owned = Number(card.dataset.owned || 0);
        const type = card.dataset.type;
        const maxAllowed = Math.min(owned, DECK_LIMITS.maxCopies);

        const removeBtn = card.querySelector(".deck-copy-btn:first-of-type");
        const addBtn = card.querySelector(".deck-copy-btn:last-of-type");

        if (removeBtn) {
            removeBtn.disabled = selected <= 0;
        }

        if (addBtn) {
            addBtn.disabled =
                selected >= maxAllowed ||
                counts.total >= DECK_LIMITS.total ||
                counts[type] >= DECK_LIMITS[type];
        }
    });
}

function updateDeckLiveStatus() {
    const counts = getCurrentCounts();
    const averageCost = counts.total > 0 ? (counts.totalCost / counts.total).toFixed(2) : "0.00";
    const isValid = isDeckValid(counts);

    setText("selected-count", counts.total);
    setText("live-total-count", `${counts.total}/${DECK_LIMITS.total}`);
    setText("live-monster-count", `${counts.Monster}/${DECK_LIMITS.Monster}`);
    setText("live-spell-count", `${counts.Spell}/${DECK_LIMITS.Spell}`);
    setText("live-trap-count", `${counts.Trap}/${DECK_LIMITS.Trap}`);
    setText("az-deck-summary-total", `${counts.total}/${DECK_LIMITS.total}`);
    setText("az-deck-summary-monsters", `${counts.Monster}/${DECK_LIMITS.Monster}`);
    setText("az-deck-summary-spells", `${counts.Spell}/${DECK_LIMITS.Spell}`);
    setText("az-deck-summary-traps", `${counts.Trap}/${DECK_LIMITS.Trap}`);
    setText("az-deck-summary-duplicates", counts.duplicates);
    setText("az-deck-summary-max-copies", `${counts.maxCopiesUsed}/${DECK_LIMITS.maxCopies}`);
    setText("live-average-cost", averageCost);

    const totalBar = document.getElementById("live-total-bar");
    const percent = Math.min(100, Math.round((counts.total / DECK_LIMITS.total) * 100));

    if (totalBar) {
        totalBar.style.width = `${percent}%`;
    }

    const message = document.getElementById("live-deck-message");

    if (message) {
        if (isValid) {
            message.textContent = "Deck is valid for beta.";
            message.className = "deck-live-message valid";
        } else {
            const remaining = DECK_LIMITS.total - counts.total;
            message.textContent = remaining >= 0
                ? `Need ${remaining} more total cards. Target: 21 monsters, 6 spells, 3 traps.`
                : `Remove ${Math.abs(remaining)} card(s). Target: 21 monsters, 6 spells, 3 traps.`;
            message.className = "deck-live-message invalid";
        }
    }

    const validityPill = document.getElementById("az-deck-validity-pill");
    const saveHint = document.getElementById("az-deck-save-hint");
    const validationSummary = document.getElementById("az-deck-validation-summary");

    if (validityPill) {
        validityPill.textContent = isValid ? "Ready to save" : "Fix deck first";
        validityPill.className = `az-deck-validity-pill-v2 ${isValid ? "is-valid" : "is-invalid"}`;
    }

    if (saveHint) {
        saveHint.textContent = isValid
            ? "Backend validation should accept this beta deck."
            : "Match the beta rule: 30 cards, 21 monsters, 6 spells, 3 traps, max 3 copies.";
    }

    if (validationSummary) {
        validationSummary.classList.toggle("az-deck-valid-v2", isValid);
        validationSummary.classList.toggle("az-deck-invalid-v2", !isValid);
    }

    const saveButton = document.getElementById("az-save-deck-btn");
    if (saveButton) {
        saveButton.classList.toggle("is-ready-to-save", isValid);
        saveButton.classList.toggle("is-needs-fixes", !isValid);
        saveButton.setAttribute("aria-disabled", isValid ? "false" : "true");
        saveButton.textContent = isValid ? "Save Active Deck" : "Save Deck / Show Errors";
    }

    updateDeckGuidance(counts, averageCost, isValid);
    updateCardSelectionStates();
    updateCopyButtons();
    updateDeckPreview();
}

function deckGuidanceLines(counts, averageCost, isValid) {
    const lines = [];
    const elementEntries = Object.entries(counts.elements || {}).filter((entry) => entry[1] > 0);

    if (isValid) {
        lines.push("Deck is valid for the fixed beta rule.");
    } else if (counts.total !== DECK_LIMITS.total) {
        lines.push(`Set the deck to exactly ${DECK_LIMITS.total} cards.`);
    }

    if (counts.Monster < 18) {
        lines.push("Add more creatures so lanes do not collapse early.");
    } else {
        lines.push("Creature count can contest lanes.");
    }

    if (Number(averageCost) > 2.9 || counts.highCostCards > 8) {
        lines.push("Lower the curve; too many expensive cards can die in hand.");
    } else {
        lines.push("Curve is playable for early Training rounds.");
    }

    if (elementEntries.length < 3) {
        lines.push("Use at least three elements for a clearer starter identity spread.");
    } else {
        lines.push("Element spread supports Fire pressure, Water focus, Earth defense and Plant control.");
    }

    if (counts.maxCopiesUsed > DECK_LIMITS.maxCopies) {
        lines.push("Reduce duplicate copies to the beta max of 3.");
    } else {
        lines.push("Duplicate limit is respected.");
    }

    return lines.slice(0, 5);
}

function updateDeckGuidance(counts, averageCost, isValid) {
    setText("az-guidance-total", `${counts.total}/${DECK_LIMITS.total}`);
    setText("az-guidance-average-cost", averageCost);
    setText("az-guidance-copy-health", `${counts.maxCopiesUsed}/${DECK_LIMITS.maxCopies}`);

    const elementEntries = Object.entries(counts.elements || {}).filter((entry) => entry[1] > 0);
    setText("az-guidance-element-balance", `${elementEntries.length} elements`);

    const list = document.getElementById("az-deck-guidance-list");
    if (!list) return;

    list.innerHTML = deckGuidanceLines(counts, averageCost, isValid)
        .map((line) => `<li>${escapeHtml(line)}</li>`)
        .join("");
}

function addCardToDeck(cardId) {
    const card = getCardElement(cardId);

    if (!card) {
        return;
    }

    const owned = Number(card.dataset.owned || 0);
    const selected = getSelectedInputs(cardId).length;

    if (selected >= Math.min(owned, DECK_LIMITS.maxCopies)) {
        return;
    }

    const counts = getCurrentCounts();
    const type = card.dataset.type;

    if (counts.total >= DECK_LIMITS.total) {
        return;
    }

    if (counts[type] >= DECK_LIMITS[type]) {
        return;
    }

    const container = document.getElementById(`inputs-${cardId}`);
    const input = document.createElement("input");

    input.type = "hidden";
    input.name = "deck_cards";
    input.value = cardId;

    container.appendChild(input);

    updateDeckLiveStatus();
}

function removeCardFromDeck(cardId) {
    const inputs = getSelectedInputs(cardId);

    if (inputs.length <= 0) {
        return;
    }

    inputs[inputs.length - 1].remove();

    updateDeckLiveStatus();
}

function filterBuilderCards() {
    const search = (document.getElementById("builder-search")?.value || "").toLowerCase();
    const type = document.getElementById("builder-type-filter")?.value || "";
    const element = document.getElementById("builder-element-filter")?.value || "";
    const sigil = document.getElementById("filter-sigil")?.value || "";
    const role = document.getElementById("filter-role")?.value || "";
    const cost = document.getElementById("builder-cost-filter")?.value || "";
    const rarity = document.getElementById("builder-rarity-filter")?.value || "";

    let visibleCount = 0;

    getBuilderCards().forEach((card) => {
        const cardName = (card.dataset.name || "").toLowerCase();
        const cardType = card.dataset.type || "";
        const cardElement = card.dataset.element || "";
        const cardSigil = card.dataset.sigil || "";
        const cardRole = card.dataset.role || "";
        const cardCost = card.dataset.cost || "";
        const cardRarity = card.dataset.rarity || "";

        const matchesSearch = !search || cardName.includes(search);
        const matchesType = !type || cardType === type;
        const matchesElement = !element || cardElement === element;
        const matchesSigil = !sigil || cardSigil === sigil;
        const matchesRole = !role || cardRole === role;
        const matchesCost = !cost || cardCost === cost;
        const matchesRarity = !rarity || cardRarity === rarity;

        const visible = (
            matchesSearch &&
            matchesType &&
            matchesElement &&
            matchesSigil &&
            matchesRole &&
            matchesCost &&
            matchesRarity
        );

        card.hidden = !visible;
        card.style.display = visible ? "" : "none";
        if (visible) {
            visibleCount += 1;
        }
    });

    const empty = document.getElementById("az-deck-no-results");
    if (empty) {
        empty.hidden = visibleCount !== 0;
    }

    updateDeckPreview();
}

function selectedPreviewCard() {
    const selected = getBuilderCards().find((card) => Number(card.dataset.selected || 0) > 0);
    return selected || getBuilderCards().find((card) => !card.hidden && card.style.display !== "none") || null;
}

function deckPreviewStats(card) {
    if (!card) {
        return [
            ["Cost", "--"],
            ["Type", "--"],
            ["Owned", "--"],
            ["In Deck", "--"]
        ];
    }

    return [
        ["Cost", card.dataset.cost || "--"],
        ["Type", card.dataset.type || "Card"],
        ["Owned", card.dataset.owned || "0"],
        ["In Deck", card.dataset.selected || "0"]
    ];
}

function deckCardArtHtml(card) {
    if (!card) {
        return "";
    }

    if (window.AmbitionzCardArt && typeof window.AmbitionzCardArt.renderCardArt === "function") {
        return window.AmbitionzCardArt.renderCardArt(card);
    }

    const element = card.dataset.element || "Neutral";
    return `<div class="az-card-art-v6"><span class="az-card-art-rune-v6">${escapeHtml(element.slice(0, 1).toUpperCase())}</span><span class="az-card-art-name-v6">${escapeHtml(card.dataset.name || "Card")}</span></div>`;
}

function deckCardFunction(card) {
    if (!card) return "Select a card to read its role.";
    const type = card.dataset.type || "Card";
    const effect = `${card.dataset.effect || ""} ${card.dataset.lore || ""}`.toLowerCase();
    if (type === "Monster") {
        if (/shield|guard|defend|resolve/.test(effect)) return "Defender: holds a lane and buys time.";
        if (/burn|damage|strike|fury/.test(effect)) return "Attacker: pressures HP and forces trades.";
        return "Creature: contests lanes and converts strategy into combat.";
    }
    if (type === "Spell") {
        if (/shield|heal|protect/.test(effect)) return "Support spell: protects your hero or board.";
        if (/draw|ambition|focus/.test(effect)) return "Focus spell: builds resources for stronger turns.";
        return "Spell damage: choose pressure or cast for immediate value.";
    }
    if (type === "Trap") return "Trap: prepare it, then let the round punish or protect at resolution.";
    return "Flexible card: check cost, element and role before adding copies.";
}

function updateDeckPreview(card) {
    const previewName = document.getElementById("az-deck-preview-name");
    const previewText = document.getElementById("az-deck-preview-text");
    const previewStats = document.getElementById("az-deck-preview-stats");
    const previewArt = document.getElementById("az-deck-preview-art");
    const target = card || selectedPreviewCard();

    if (!previewName || !previewText || !previewStats) {
        return;
    }

    if (!target) {
        previewName.textContent = "No cards available";
        previewText.textContent = "Your collection has no cards to preview yet.";
    } else {
        const name = target.querySelector(".card-topline strong")?.textContent || "Selected card";
        const lore = target.dataset.lore || target.dataset.effect || "Ambitionz beta card identity.";
        previewName.textContent = name;
        previewText.textContent = `${deckCardFunction(target)} ${lore}`;
    }

    if (previewArt) {
        previewArt.innerHTML = target ? deckCardArtHtml(target) : "";
    }

    previewStats.innerHTML = deckPreviewStats(target).map((row) => {
        return `<span><b>${escapeHtml(row[0])}</b>${escapeHtml(row[1])}</span>`;
    }).join("");
}

document.addEventListener("DOMContentLoaded", () => {
    bindDeckBuilderControls();
    updateDeckLiveStatus();
    if (window.AmbitionzCardArt && typeof window.AmbitionzCardArt.loadCardArtManifest === "function") {
        window.AmbitionzCardArt.loadCardArtManifest().then(() => {
            if (typeof window.AmbitionzCardArt.enhanceAllCards === "function") window.AmbitionzCardArt.enhanceAllCards();
            updateDeckPreview();
        });
    }
});


function bindDeckBuilderControls() {
    [
        "builder-search",
        "builder-type-filter",
        "builder-element-filter",
        "filter-sigil",
        "filter-role",
        "builder-rarity-filter",
        "builder-cost-filter"
    ].forEach((id) => {
        const element = document.getElementById(id);

        if (!element) {
            return;
        }

        const eventName = element.tagName === "INPUT" ? "input" : "change";
        element.addEventListener(eventName, filterBuilderCards);
    });

    document.querySelectorAll("[data-quick-filter-kind][data-quick-filter-value]").forEach((button) => {
        button.addEventListener("click", () => {
            quickDeckFilter(button.dataset.quickFilterKind, button.dataset.quickFilterValue);
        });
    });

    document.querySelectorAll("[data-clear-deck-filters]").forEach((button) => {
        button.addEventListener("click", clearDeckFilters);
    });

    document.querySelectorAll("[data-deck-action][data-card-id]").forEach((button) => {
        button.addEventListener("click", () => {
            if (button.dataset.deckAction === "add") {
                addCardToDeck(button.dataset.cardId);
                return;
            }

            if (button.dataset.deckAction === "remove") {
                removeCardFromDeck(button.dataset.cardId);
            }
        });
    });

    getBuilderCards().forEach((card) => {
        card.addEventListener("mouseover", () => updateDeckPreview(card));
        card.addEventListener("focusin", () => updateDeckPreview(card));
        card.addEventListener("click", () => updateDeckPreview(card));
    });
}


function quickDeckFilter(kind, value) {
    if (kind === "element") {
        const elementFilter = document.getElementById("builder-element-filter");

        if (elementFilter) {
            elementFilter.value = value;
        }
    }

    if (kind === "sigil") {
        const sigilFilter = document.getElementById("filter-sigil");

        if (sigilFilter) {
            sigilFilter.value = value;
        }
    }

    filterBuilderCards();
    updateDeckPreview();
}

function clearDeckFilters() {
    [
        "builder-search",
        "builder-type-filter",
        "builder-element-filter",
        "filter-sigil",
        "filter-role",
        "builder-rarity-filter",
        "builder-cost-filter"
    ].forEach((id) => {
        const element = document.getElementById(id);

        if (element) {
            element.value = "";
        }
    });

    filterBuilderCards();
}
