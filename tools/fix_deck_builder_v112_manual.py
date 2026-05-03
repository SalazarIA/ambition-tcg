from pathlib import Path
import re
import shutil
from datetime import datetime

ROOT = Path(".")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "backups" / f"deck_builder_v112_manual_{STAMP}"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

template_path = ROOT / "templates/deck_builder.html"
js_path = ROOT / "static/js/deck_builder.js"

def backup(path: Path):
    dest = BACKUP_DIR / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")

backup(template_path)
backup(js_path)

html = read(template_path)

old_block = '''                    <label

                        class="collection-card selectable-card"

                        data-name="{{ card.name|lower }}"

                        data-type="{{ card.type }}"

                        data-element="{{ card.element }}"

                        data-sigil="{{ card.sigil }}"

                        data-role="{{ card.role }}"

                        data-rarity="{{ card.rarity }}"

                        data-cost="{{ card.cost }}"

                    >

                        <input

                            type="checkbox"

                            name="deck_cards"

                            value="{{ card.id }}"

                            data-type="{{ card.type }}"

                            {% if card.id in deck_ids %}checked{% endif %}

                            onchange="updateLiveDeckCounts()"

                        >

                        <div class="card-shell">'''

new_block = '''                    <article

                        class="collection-card selectable-card builder-card"

                        data-card-id="{{ card.id }}"

                        data-owned="{{ collection_ids.count(card.id) if collection_ids is defined else 3 }}"

                        data-name="{{ card.name|lower }}"

                        data-type="{{ card.type }}"

                        data-element="{{ card.element }}"

                        data-sigil="{{ card.sigil }}"

                        data-role="{{ card.role }}"

                        data-rarity="{{ card.rarity }}"

                        data-cost="{{ card.cost }}"

                    >

                        <div class="deck-card-controls">

                            <button type="button" class="deck-copy-btn" onclick="removeCardFromDeck('{{ card.id }}')" aria-label="Remove copy">−</button>

                            <span class="deck-copy-count" id="count-{{ card.id }}">0</span>

                            <button type="button" class="deck-copy-btn" onclick="addCardToDeck('{{ card.id }}')" aria-label="Add copy">+</button>

                        </div>

                        <div id="inputs-{{ card.id }}" class="deck-hidden-inputs">

                            {% for _ in range(deck_ids.count(card.id)) %}

                                <input type="hidden" name="deck_cards" value="{{ card.id }}">

                            {% endfor %}

                        </div>

                        <div class="card-shell">'''

if old_block not in html:
    raise SystemExit("ERROR: old checkbox block not found exactly. No changes made.")

html = html.replace(old_block, new_block, 1)
html = html.replace("                    </label>", "                    </article>", 1)

# Add copy-counter CSS before </style>.
css = '''
        .deck-card-controls {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 0.5rem;
            margin-bottom: 0.75rem;
        }

        .deck-copy-btn {
            width: 34px;
            height: 34px;
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            color: #fff;
            font-size: 1.2rem;
            font-weight: 900;
            line-height: 1;
            cursor: pointer;
        }

        .deck-copy-btn:disabled {
            opacity: 0.35;
            cursor: not-allowed;
        }

        .deck-copy-count {
            min-width: 32px;
            text-align: center;
            font-weight: 900;
            font-size: 1rem;
        }

        .deck-hidden-inputs {
            display: none;
        }

        .builder-card[data-selected="0"] {
            opacity: 0.88;
        }

        .builder-card[data-selected]:not([data-selected="0"]) {
            outline: 1px solid rgba(255, 214, 102, 0.36);
        }
'''

if ".deck-card-controls" not in html:
    html = html.replace("</style>", css + "\n    </style>")

write(template_path, html)

js = read(js_path)

# Ensure limits include maxCopies.
js = js.replace(
'''const DECK_LIMITS = {
    total: 30,
    Monster: 21,
    Spell: 6,
    Trap: 3
};''',
'''const DECK_LIMITS = {
    total: 30,
    Monster: 21,
    Spell: 6,
    Trap: 3,
    maxCopies: 3
};'''
)

# Add safe text helper if missing.
if "function setText(" not in js:
    js = js.replace(
'''function getBuilderCards() {
    return Array.from(document.querySelectorAll(".builder-card"));
}''',
'''function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}

function getBuilderCards() {
    return Array.from(document.querySelectorAll(".builder-card"));
}'''
    )

# Make live counters safe if not already patched.
js = js.replace(
'''    document.getElementById("selected-count").textContent = counts.total;
    document.getElementById("live-total-count").textContent = counts.total;
    document.getElementById("live-monster-count").textContent = counts.Monster;
    document.getElementById("live-spell-count").textContent = counts.Spell;
    document.getElementById("live-trap-count").textContent = counts.Trap;
    document.getElementById("live-average-cost").textContent = averageCost;''',
'''    setText("selected-count", counts.total);
    setText("live-total-count", counts.total);
    setText("live-monster-count", counts.Monster);
    setText("live-spell-count", counts.Spell);
    setText("live-trap-count", counts.Trap);
    setText("live-average-cost", averageCost);'''
)

js = js.replace(
'''    const totalBar = document.getElementById("live-total-bar");
    const percent = Math.min(100, Math.round((counts.total / DECK_LIMITS.total) * 100));
    totalBar.style.width = `${percent}%`;

    const message = document.getElementById("live-deck-message");''',
'''    const totalBar = document.getElementById("live-total-bar");
    const percent = Math.min(100, Math.round((counts.total / DECK_LIMITS.total) * 100));

    if (totalBar) {
        totalBar.style.width = `${percent}%`;
    }

    const message = document.getElementById("live-deck-message");

    if (!message) {
        updateCopyButtons();
        return;
    }'''
)

# Add copy button state function if missing.
if "function updateCopyButtons()" not in js:
    js = js.replace(
'''function updateDeckLiveStatus() {
    const counts = getCurrentCounts();''',
'''function updateCopyButtons() {
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
    const counts = getCurrentCounts();'''
    )

    js = js.replace(
'''        card.dataset.selected = selected;
    });
}''',
'''        card.dataset.selected = selected;
    });

    updateCopyButtons();
}''',
    1
    )

# Enforce max 3 copies.
js = js.replace(
'''    if (selected >= owned) {
        return;
    }''',
'''    if (selected >= Math.min(owned, DECK_LIMITS.maxCopies)) {
        return;
    }'''
)

# Make filter use existing template IDs and include sigil/role.
js = re.sub(
r'''function filterBuilderCards\(\) \{.*?\n\}''',
'''function filterBuilderCards() {
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
}''',
js,
flags=re.S
)

# Restore global functions used by template buttons.
if "function quickDeckFilter(" not in js:
    js += '''

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
'''

write(js_path, js)

print(f"OK: manual Deck Builder V112 patch applied.")
print(f"Backup created at: {BACKUP_DIR}")
