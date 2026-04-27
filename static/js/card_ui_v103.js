function normalizeClass(value) {
    return String(value || "global")
        .trim()
        .toLowerCase()
        .replace(/\s+/g, "-");
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function cardFrameHtml(card, options = {}) {
    if (!card) {
        return `
            <div class="empty-slot-v103">
                <span>${escapeHtml(options.emptyText || "Empty Zone")}</span>
            </div>
        `;
    }

    const name = escapeHtml(card.name || "Unknown Card");
    const type = escapeHtml(card.type || "Card");
    const element = escapeHtml(card.element || "Global");
    const rarity = escapeHtml(card.rarity || "Common");
    const cost = escapeHtml(card.cost ?? 0);
    const power = escapeHtml(card.power ?? "-");
    const sigil = escapeHtml(card.sigil || "Global");
    const role = escapeHtml(card.role || "Balancer");
    const effect = escapeHtml(card.effect || card.description || "No effect.");
    const archetype = escapeHtml(card.archetype || "");
    const identityRole = escapeHtml(card.identity_role || "");
    const lore = escapeHtml(card.lore || "");
    const tacticalHint = escapeHtml(card.tactical_hint || "");

    const elementClass = `az-element-${normalizeClass(element)}`;
    const rarityClass = `az-rarity-${normalizeClass(rarity)}`;
    const sigilClass = `az-sigil-${normalizeClass(sigil)}`;

    const showPower = String(card.type || "").toLowerCase() === "monster" || card.power !== undefined;

    return `
        <article class="az-card-frame ${elementClass} ${rarityClass}">
            <div class="az-card-inner">
                <div class="az-card-header">
                    <div class="az-card-name">${name}</div>
                    <div class="az-card-cost">${cost}</div>
                </div>

                <div class="az-card-art">${element}</div>

                <div class="az-card-meta">
                    <span class="az-chip">${type}</span>
                    <span class="az-chip">${rarity}</span>
                </div>

                <div class="az-card-tags">
                    <span class="az-chip ${sigilClass}">${sigil}</span>
                    <span class="az-chip">${role}</span>
                </div>

                ${showPower ? `
                    <div class="az-card-power">
                        <span>Power</span>
                        <strong>${power}</strong>
                    </div>
                ` : ""}

                <p class="az-card-effect">${effect}</p>

                ${(archetype || identityRole) ? `
                    <div class="az-card-identity">
                        ${archetype ? `<span>${archetype}</span>` : ""}
                        ${identityRole ? `<span>${identityRole}</span>` : ""}
                    </div>
                ` : ""}

                ${lore ? `<p class="az-card-lore">${lore}</p>` : ""}
                ${tacticalHint ? `<p class="az-card-hint">${tacticalHint}</p>` : ""}
            </div>
        </article>
    `;
}

window.AmbitionzCardUI = {
    cardFrameHtml,
    escapeHtml,
    normalizeClass,
};
