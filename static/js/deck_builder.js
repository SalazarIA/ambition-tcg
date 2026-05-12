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
        maxCopiesUsed: 0
    };

    getBuilderCards().forEach((card) => {
        const selected = getSelectedInputs(card.dataset.cardId).length;
        const type = card.dataset.type;
        const cost = Number(card.dataset.cost || 1);

        counts.total += selected;
        counts[type] += selected;
        counts.totalCost += selected * cost;

        if (selected > 1) {
            counts.duplicates += 1;
        }

        counts.maxCopiesUsed = Math.max(counts.maxCopiesUsed, selected);
    });

    return counts;
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

    if (!message) {
        updateCopyButtons();
        return;
    }

    const isValid =
        counts.total === DECK_LIMITS.total &&
        counts.Monster === DECK_LIMITS.Monster &&
        counts.Spell === DECK_LIMITS.Spell &&
        counts.Trap === DECK_LIMITS.Trap;

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

    getBuilderCards().forEach((card) => {
        const selected = getSelectedInputs(card.dataset.cardId).length;
        const countEl = document.getElementById(`count-${card.dataset.cardId}`);

        if (countEl) {
            countEl.textContent = selected;
        }

        card.dataset.selected = selected;
    });

    updateCopyButtons();
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

        card.style.display = (
            matchesSearch &&
            matchesType &&
            matchesElement &&
            matchesSigil &&
            matchesRole &&
            matchesCost &&
            matchesRarity
        ) ? "" : "none";
    });
}

document.addEventListener("DOMContentLoaded", () => {
    bindDeckBuilderControls();
    updateDeckLiveStatus();
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
