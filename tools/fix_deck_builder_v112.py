from pathlib import Path
import re
import shutil
from datetime import datetime

ROOT = Path(".")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "backups" / f"deck_builder_v112_{STAMP}"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

template_path = ROOT / "templates/deck_builder.html"
js_path = ROOT / "static/js/deck_builder.js"

def backup(path: Path):
    if path.exists():
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

# 1) Remove old inline deck filtering/counting script and replace with external script.
# Keep the template clean and force one source of truth: static/js/deck_builder.js
html = re.sub(
    r"\n\s*<script>\s*function filterDeckCards\(\).*?</script>",
    '\n    <script src="{{ url_for(\'static\', filename=\'js/deck_builder.js\') }}"></script>',
    html,
    flags=re.S,
)

# If regex did not catch because the script has extra spaces, append the external script safely.
if "js/deck_builder.js" not in html:
    html = html.replace(
        "</body>",
        '    <script src="{{ url_for(\'static\', filename=\'js/deck_builder.js\') }}"></script>\n</body>'
    )

# 2) Normalize filter IDs used by static/js/deck_builder.js.
replacements = {
    'id="deck-search"': 'id="builder-search"',
    'id="filter-type"': 'id="builder-type-filter"',
    'id="filter-element"': 'id="builder-element-filter"',
    'id="filter-cost"': 'id="builder-cost-filter"',
    'id="filter-rarity"': 'id="builder-rarity-filter"',
    'onchange="filterDeckCards()"': 'onchange="filterBuilderCards()"',
    'oninput="filterDeckCards()"': 'oninput="filterBuilderCards()"',
}
for old, new in replacements.items():
    html = html.replace(old, new)

# 3) Convert selectable-card label blocks from checkbox model to builder-card model.
# This targets each card label containing name deck_cards.
pattern = re.compile(
    r"""<label\s+class="selectable-card(?P<class_extra>[^"]*)"\s+
(?P<attrs>.*?)
>\s*
\s*<input\s+
(?P<input_attrs>.*?)
type="checkbox"
(?P<input_rest>.*?)
>\s*
(?P<body><div class="card-shell">.*?</div>)\s*
</label>""",
    flags=re.S,
)

def convert_card_block(match: re.Match) -> str:
    attrs = match.group("attrs")
    input_attrs = match.group("input_attrs") + match.group("input_rest")
    body = match.group("body")

    value_match = re.search(r'value="{{\s*card\.id\s*}}"', input_attrs)
    # Most cards use card.id; keep Jinja generic.
    card_id = "{{ card.id }}"

    # Keep existing data attrs from the old label.
    attrs_clean = attrs.strip()

    return f'''<article class="builder-card selectable-card" {attrs_clean} data-card-id="{card_id}" data-owned="{{{{ collection_ids.count(card.id) if collection_ids is defined else 3 }}}}">
                        <div class="deck-card-controls">
                            <button type="button" class="deck-copy-btn" onclick="removeCardFromDeck('{card_id}')" aria-label="Remove copy">−</button>
                            <span class="deck-copy-count" id="count-{card_id}">0</span>
                            <button type="button" class="deck-copy-btn" onclick="addCardToDeck('{card_id}')" aria-label="Add copy">+</button>
                        </div>

                        <div id="inputs-{card_id}" class="deck-hidden-inputs">
                            {{% for _ in range(deck_ids.count(card.id)) %}}
                                <input type="hidden" name="deck_cards" value="{card_id}">
                            {{% endfor %}}
                        </div>

                        {body}
                    </article>'''

new_html, converted = pattern.subn(convert_card_block, html)

if converted == 0:
    print("WARN: Could not auto-convert selectable-card checkbox blocks. Template structure may differ.")
else:
    html = new_html
    print(f"OK: converted {converted} card blocks to copy counters.")

# 4) Remove obsolete selected filter option if present or keep it functional by data-selected.
# static/js/deck_builder.js does not currently use selected filter, so remove the dropdown block when possible.
html = re.sub(
    r"""\s*<select id="filter-selected".*?</select>""",
    "",
    html,
    flags=re.S,
)

# 5) Add selected filter support to JS instead, if template still has builder-selected-filter later.
# Not needed for now.

# 6) Add CSS for copy controls if not already present.
if ".deck-card-controls" not in html:
    css = """
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
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            color: #fff;
            font-size: 1.2rem;
            font-weight: 800;
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
            outline: 1px solid rgba(255, 214, 102, 0.35);
        }
"""
    html = html.replace("</style>", css + "\n    </style>")

write(template_path, html)

# 7) Harden static/js/deck_builder.js: max 3 copies per card, not only owned count.
js = read(js_path)

js = js.replace(
    """const DECK_LIMITS = {
    total: 30,
    Monster: 21,
    Spell: 6,
    Trap: 3
};""",
    """const DECK_LIMITS = {
    total: 30,
    Monster: 21,
    Spell: 6,
    Trap: 3,
    maxCopies: 3
};"""
)

js = js.replace(
    """    if (selected >= owned) {
        return;
    }""",
    """    if (selected >= Math.min(owned, DECK_LIMITS.maxCopies)) {
        return;
    }"""
)

# Add button disabled state refresh.
if "function updateCopyButtons()" not in js:
    js = js.replace(
        """function updateDeckLiveStatus() {
    const counts = getCurrentCounts();""",
        """function updateCopyButtons() {
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
    const counts = getCurrentCounts();"""
    )

    js = js.replace(
        """        card.dataset.selected = selected;
    });
}""",
        """        card.dataset.selected = selected;
    });

    updateCopyButtons();
}"""
    )

# Make filter compatible with missing controls.
js = js.replace(
    """    const search = document.getElementById("builder-search").value.toLowerCase();
    const type = document.getElementById("builder-type-filter").value;
    const element = document.getElementById("builder-element-filter").value;
    const cost = document.getElementById("builder-cost-filter").value;
    const rarity = document.getElementById("builder-rarity-filter").value;""",
    """    const search = (document.getElementById("builder-search")?.value || "").toLowerCase();
    const type = document.getElementById("builder-type-filter")?.value || "";
    const element = document.getElementById("builder-element-filter")?.value || "";
    const cost = document.getElementById("builder-cost-filter")?.value || "";
    const rarity = document.getElementById("builder-rarity-filter")?.value || "";"""
)

# Make live status compatible if some metric nodes are missing.
js = js.replace(
    """    document.getElementById("selected-count").textContent = counts.total;
    document.getElementById("live-total-count").textContent = counts.total;
    document.getElementById("live-monster-count").textContent = counts.Monster;
    document.getElementById("live-spell-count").textContent = counts.Spell;
    document.getElementById("live-trap-count").textContent = counts.Trap;
    document.getElementById("live-average-cost").textContent = averageCost;""",
    """    setText("selected-count", counts.total);
    setText("live-total-count", counts.total);
    setText("live-monster-count", counts.Monster);
    setText("live-spell-count", counts.Spell);
    setText("live-trap-count", counts.Trap);
    setText("live-average-cost", averageCost);"""
)

if "function setText(" not in js:
    js = js.replace(
        """function getBuilderCards() {
    return Array.from(document.querySelectorAll(".builder-card"));
}""",
        """function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}

function getBuilderCards() {
    return Array.from(document.querySelectorAll(".builder-card"));
}"""
    )

js = js.replace(
    """    const totalBar = document.getElementById("live-total-bar");
    const percent = Math.min(100, Math.round((counts.total / DECK_LIMITS.total) * 100));
    totalBar.style.width = `${percent}%`;

    const message = document.getElementById("live-deck-message");""",
    """    const totalBar = document.getElementById("live-total-bar");
    const percent = Math.min(100, Math.round((counts.total / DECK_LIMITS.total) * 100));

    if (totalBar) {
        totalBar.style.width = `${percent}%`;
    }

    const message = document.getElementById("live-deck-message");

    if (!message) {
        updateCopyButtons();
        return;
    }"""
)

write(js_path, js)

print(f"Backup created at: {BACKUP_DIR}")
