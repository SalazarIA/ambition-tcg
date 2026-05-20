from collections import Counter
from copy import deepcopy
from random import Random

from services.rebirth_cards import BASE_MONSTERS, EVOLVED_MONSTERS, PLAYER_DECK, catalog_payload, get_card


PRODUCT_NAV = [
    {"key": "play", "label": "Play", "href": "/rebirth"},
    {"key": "collection", "label": "Collection", "href": "/rebirth/collection"},
    {"key": "shop", "label": "Shop", "href": "/rebirth/shop"},
    {"key": "progression", "label": "Progression", "href": "/rebirth/progression"},
    {"key": "profile", "label": "Profile", "href": "/rebirth/profile"},
    {"key": "history", "label": "History", "href": "/rebirth/history"},
    {"key": "tutorial", "label": "Tutorial", "href": "/rebirth/onboarding"},
    {"key": "balance", "label": "Balance", "href": "/rebirth/balance"},
    {"key": "support", "label": "Support", "href": "/rebirth/support"},
    {"key": "account", "label": "Account", "href": "/rebirth/account"},
    {"key": "desktop", "label": "Desktop", "href": "/rebirth/desktop"},
    {"key": "release", "label": "Release", "href": "/rebirth/release"},
]

DEFAULT_LOADOUT = [
    "dreadclaw",
    "dreadclaw",
    "stoneshell",
    "shadewisp",
    "skywarden",
    "ironbastion",
    "embermaw",
    "voidstalker",
]

AUTH_PLAN_STEPS = [
    {
        "title": "Identity",
        "status": "Live",
        "copy": "Email and password accounts with unique username, normalized email and beta-safe JSON errors.",
    },
    {
        "title": "Session",
        "status": "Live",
        "copy": "Flask signed session cookie with HttpOnly and SameSite defaults for the active Rebirth app.",
    },
    {
        "title": "Mutations",
        "status": "Live",
        "copy": "Rebirth POST APIs use a session CSRF token and auth endpoints have a small in-memory rate limit.",
    },
    {
        "title": "Ownership",
        "status": "Live",
        "copy": "Collection, loadout, rewards and booster history attach to the signed-in Rebirth user.",
    },
    {
        "title": "Migration",
        "status": "Future",
        "copy": "No legacy account table is active. Any migration must map old data into Rebirth-native records.",
    },
]

TUTORIAL_STEPS = [
    {
        "step": 1,
        "title": "Pick One Monster",
        "copy": "Your hand is public to you. Choose the monster that creates the cleanest clash.",
    },
    {
        "step": 2,
        "title": "Read The Answer",
        "copy": "The bot answers with one monster. Attack decides the winner; guard reduces damage.",
    },
    {
        "step": 3,
        "title": "Combine Duplicates",
        "copy": "Two matching base monsters can evolve before you commit a card.",
    },
    {
        "step": 4,
        "title": "Claim Progress",
        "copy": "Clashes, boosters and tutorial completion now persist to your Rebirth account.",
    },
]

RELEASE_CHECKS = [
    {"name": "Product Truth", "state": "passed", "copy": "Ambitionz Rebirth is the active product surface."},
    {"name": "Legacy Disabled", "state": "passed", "copy": "Retired browser routes redirect and retired APIs return 410."},
    {"name": "Persistence", "state": "passed", "copy": "Auth, collection, loadout, progression and boosters persist in SQLite."},
    {"name": "Account Safety", "state": "passed", "copy": "CSRF, auth throttling and password changes are active in the Rebirth shell."},
    {"name": "Frontend", "state": "passed", "copy": "Vanilla Rebirth pages avoid old Arena/Ascension assets."},
    {"name": "Card Feel", "state": "passed", "copy": "Clash results expose ability events, impact feedback and persisted reward moments."},
    {"name": "Balance Lab", "state": "passed", "copy": "Bot personality simulations report card, ability and profile impact."},
    {"name": "History", "state": "passed", "copy": "Signed-in matches persist commands, events, state hash and final snapshot."},
    {"name": "Economy Ledger", "state": "passed", "copy": "XP, starter cards, boosters, daily rewards and admin grants write an auditable ledger."},
    {"name": "Support Tools", "state": "passed", "copy": "Players can export/reset account state; admin grants require an explicit server token."},
    {"name": "QA Gate", "state": "passed", "copy": "py_compile, pytest, node checks and Browser smoke passed for this block."},
]

PROGRESSION_TRACK = [
    {"level": 1, "name": "First Spark", "reward": "Starter booster demo", "state": "claimed"},
    {"level": 2, "name": "Second Clash", "reward": "50 Gold preview", "state": "ready"},
    {"level": 3, "name": "Monster Bond", "reward": "Loadout slot preview", "state": "locked"},
    {"level": 4, "name": "Apex Trial", "reward": "Evolved art frame", "state": "locked"},
]


def nav(active):
    items = []
    for item in PRODUCT_NAV:
        copy = dict(item)
        copy["active"] = copy["key"] == active
        items.append(copy)
    return items


def page_payload(key, title, subtitle, primary_label="Play Rebirth", primary_href="/rebirth"):
    return {
        "key": key,
        "title": title,
        "subtitle": subtitle,
        "primary_label": primary_label,
        "primary_href": primary_href,
        "nav": nav(key),
    }


def guest_account():
    return {"authenticated": False, "user": None}


def account_payload(user=None):
    return {"authenticated": bool(user), "user": deepcopy(user) if user else None}


def product_shell_payload(account=None):
    account = account or guest_account()
    payload = page_payload(
        "home",
        "Ambitionz Rebirth",
        "One active product shell around the persisted one-card clash MVP.",
    )
    payload.update(
        {
            "account": account,
            "status": [
                {"label": "Runtime", "value": "Rebirth only"},
                {"label": "Legacy", "value": "Retired"},
                {"label": "Store", "value": "SQLite MVP"},
            ],
            "blocks": [
                {
                    "title": "Real Auth/Persistence",
                    "copy": "Create a Rebirth account and attach ownership to the active session.",
                    "href": "/rebirth/account",
                },
                {
                    "title": "Collection + Loadout",
                    "copy": "Persist owned monsters and the active eight-card Rebirth loadout.",
                    "href": "/rebirth/collection",
                },
                {
                    "title": "Shop + Booster",
                    "copy": "Open a no-payment booster that mutates signed-in ownership.",
                    "href": "/rebirth/shop",
                },
                {
                    "title": "Progression + Rewards",
                    "copy": "Track persisted XP, wins, clashes, tutorial and daily reward state.",
                    "href": "/rebirth/progression",
                },
                {
                    "title": "Profile + Achievements",
                    "copy": "Inspect player identity, collection stats and unlocked Rebirth achievements.",
                    "href": "/rebirth/profile",
                },
                {
                    "title": "History + Ledger",
                    "copy": "Review persisted matches, event counts, state hashes and economy movements.",
                    "href": "/rebirth/history",
                },
                {
                    "title": "Onboarding + QA",
                    "copy": "Run the tutorial, balance simulation and release checks.",
                    "href": "/rebirth/onboarding",
                },
            ],
        }
    )
    return payload


def auth_plan_payload(account=None):
    account = account or guest_account()
    payload = page_payload(
        "account",
        "Real Login/Auth Plan",
        "Rebirth now has its own account/session layer, backed by SQLite and isolated from retired legacy auth.",
        primary_label="Open Collection",
        primary_href="/rebirth/collection",
    )
    payload["account"] = account
    payload["steps"] = deepcopy(AUTH_PLAN_STEPS)
    payload["constraints"] = [
        "No SQLAlchemy runtime is active in the current MVP.",
        "Passwords are hashed with PBKDF2 before storage.",
        "Mutating Rebirth APIs are guarded by a session CSRF token.",
        "Auth endpoints have a small in-memory rate limit for the current runtime.",
        "Collection, loadout, booster history and rewards persist per Rebirth user.",
        "Signed-in players can change their password from the Rebirth profile screen.",
        "Legacy users require an explicit future migration task.",
    ]
    return payload


def owned_counts(collection_counts=None):
    if collection_counts is not None:
        return Counter(collection_counts)
    return Counter(PLAYER_DECK)


def card_collection(collection_counts=None, loadout_card_ids=None):
    counts = owned_counts(collection_counts)
    loadout_counts = Counter(loadout_card_ids or DEFAULT_LOADOUT)
    cards = []
    for card in catalog_payload():
        card_copy = deepcopy(card)
        card_copy["owned_count"] = counts.get(card["id"], 0)
        card_copy["in_loadout_count"] = loadout_counts.get(card["id"], 0)
        card_copy["unlock_state"] = "owned" if card_copy["owned_count"] else "preview"
        card_copy["is_evolved"] = int(card_copy.get("tier", 1)) > 1
        cards.append(card_copy)
    return cards


def collection_payload(account=None, collection_counts=None, loadout_card_ids=None):
    account = account or guest_account()
    loadout_ids = loadout_card_ids or DEFAULT_LOADOUT
    cards = card_collection(collection_counts=collection_counts, loadout_card_ids=loadout_ids)
    base_owned = [card for card in cards if card["owned_count"]]
    payload = page_payload(
        "collection",
        "Collection + Loadout",
        "Owned monsters and the active eight-card loadout now persist to the signed-in Rebirth account.",
        primary_label="Enter Arena",
        primary_href="/rebirth",
    )
    payload.update(
        {
            "account": account,
            "is_persisted": bool(account.get("authenticated")),
            "cards": cards,
            "loadout": [get_card(card_id) for card_id in loadout_ids],
            "summary": {
                "owned_cards": sum(card["owned_count"] for card in cards),
                "unique_owned": len(base_owned),
                "loadout_size": len(loadout_ids),
                "preview_evolutions": len(EVOLVED_MONSTERS),
            },
        }
    )
    return payload


def validate_loadout(card_ids, collection_counts=None):
    if not isinstance(card_ids, list):
        raise ValueError("card_ids must be a list.")
    selected = [str(card_id) for card_id in card_ids if str(card_id or "").strip()]
    if len(selected) != 8:
        raise ValueError("Rebirth loadout preview requires exactly 8 cards.")

    owned = owned_counts(collection_counts)
    selected_counts = Counter(selected)
    for card_id, amount in selected_counts.items():
        if card_id not in owned:
            raise ValueError(f"{card_id} is not owned in the Rebirth collection.")
        if amount > owned[card_id]:
            raise ValueError(f"{card_id} exceeds owned copies.")

    loadout = [get_card(card_id) for card_id in selected]
    families = sorted({card["family"] for card in loadout})
    return {
        "loadout": loadout,
        "summary": {
            "size": len(loadout),
            "families": families,
            "attack_total": sum(int(card["attack"]) for card in loadout),
            "guard_total": sum(int(card["guard"]) for card in loadout),
            "duplicate_pairs": sum(1 for count in selected_counts.values() if count >= 2),
        },
    }


def shop_payload(account=None, booster_history=None):
    account = account or guest_account()
    payload = page_payload(
        "shop",
        "Shop + Booster Demo",
        "A no-payment booster flow that adds cards to the signed-in Rebirth collection.",
        primary_label="Open Demo Booster",
        primary_href="/rebirth/shop",
    )
    payload.update(
        {
            "offers": [
                {
                    "id": "starter_booster_demo",
                    "name": "Rebirth Starter Booster",
                    "price": "Demo",
                    "contents": "4 cards, one elevated slot, persisted ownership",
                    "state": "available",
                }
            ],
            "account": account,
            "history": booster_history or [],
            "disclaimer": "No currency, payment processor or legacy economy is active. Booster cards persist only for signed-in Rebirth accounts.",
        }
    )
    return payload


def open_booster(seed=None):
    rng = Random(str(seed or "rebirth-booster-demo"))
    base_pool = [card["id"] for card in BASE_MONSTERS]
    elevated_pool = [card["id"] for card in EVOLVED_MONSTERS] + ["embermaw", "dreadclaw"]
    card_ids = [rng.choice(base_pool) for _ in range(3)]
    card_ids.append(rng.choice(elevated_pool))
    cards = [get_card(card_id) for card_id in card_ids]
    return {
        "booster_id": "starter_booster_demo",
        "cards": cards,
        "summary": {
            "count": len(cards),
            "highest_attack": max(card["attack"] for card in cards),
            "elevated_slot": cards[-1]["name"],
        },
    }


def progression_payload(account=None, progression=None):
    account = account or guest_account()
    profile = progression or {
        "level": 1,
        "xp": 0,
        "next_level_xp": 500,
        "wins": 0,
        "losses": 0,
        "clashes": 0,
        "boosters_opened": 0,
        "tutorial_step": 0,
        "tutorial_complete": False,
    }
    payload = page_payload(
        "progression",
        "Progression + Rewards",
        "A Rebirth-native reward loop persisted per account and separate from retired economy systems.",
        primary_label="Play For XP",
        primary_href="/rebirth",
    )
    payload.update(
        {
            "account": account,
            "profile": profile,
            "track": progression_track(profile),
            "daily": {
                "name": "Play one clash",
                "progress": min(1, int(profile.get("clashes", 0))),
                "goal": 1,
                "reward": "25 XP",
                "state": "ready" if int(profile.get("clashes", 0)) >= 1 else "locked",
            },
        }
    )
    return payload


def progression_track(profile):
    level = int(profile.get("level", 1))
    track = deepcopy(PROGRESSION_TRACK)
    for item in track:
        if item["level"] < level:
            item["state"] = "claimed"
        elif item["level"] == level:
            item["state"] = "ready"
        else:
            item["state"] = "locked"
    return track


def guest_profile():
    return {
        "user": None,
        "progression": {
            "level": 1,
            "xp": 0,
            "next_level_xp": 500,
            "wins": 0,
            "losses": 0,
            "clashes": 0,
            "boosters_opened": 0,
            "tutorial_step": 0,
            "tutorial_complete": False,
        },
        "collection": {"owned_cards": len(PLAYER_DECK), "unique_owned": len(set(PLAYER_DECK)), "loadout_size": 8},
        "achievements": [
            {
                "key": key,
                "name": name,
                "copy": copy,
                "unlocked": False,
                "unlocked_at": None,
            }
            for key, name, copy in [
                ("founder", "Rebirth Founder", "Create a Rebirth account."),
                ("first_clash", "First Clash", "Resolve one persisted Rebirth clash."),
                ("first_win", "First Victory", "Win a persisted Rebirth match."),
                ("first_booster", "Booster Opened", "Open one no-payment Rebirth booster."),
                ("daily_claimed", "Daily Spark", "Claim the first-clash daily reward."),
                ("tutorial_complete", "Awakened", "Complete the Rebirth onboarding path."),
            ]
        ],
        "unlocked_achievements": 0,
        "recent_boosters": [],
    }


def profile_payload(account=None, profile=None):
    account = account or guest_account()
    profile = profile or guest_profile()
    progress = profile.get("progression") or guest_profile()["progression"]
    collection = profile.get("collection") or guest_profile()["collection"]
    payload = page_payload(
        "profile",
        "Player Profile",
        "Persisted identity, achievements and account controls for the active Rebirth player.",
        primary_label="Open Collection",
        primary_href="/rebirth/collection",
    )
    payload.update(
        {
            "account": account,
            "profile": profile,
            "stats": [
                {"label": "Level", "value": progress.get("level", 1)},
                {"label": "XP", "value": f"{progress.get('xp', 0)}/{progress.get('next_level_xp', 500)}"},
                {"label": "Owned", "value": collection.get("owned_cards", 0)},
                {"label": "Badges", "value": profile.get("unlocked_achievements", 0)},
            ],
        }
    )
    return payload


def history_payload(account=None, matches=None, ledger=None):
    account = account or guest_account()
    matches = matches or []
    ledger = ledger or []
    payload = page_payload(
        "history",
        "Match History + Economy Ledger",
        "Persisted Rebirth matches now save command/event counts, state hashes and reward movements.",
        primary_label="Play For History",
        primary_href="/rebirth",
    )
    payload.update(
        {
            "account": account,
            "matches": matches,
            "ledger": ledger,
            "summary": {
                "matches": len(matches),
                "ledger_entries": len(ledger),
                "finished": len([match for match in matches if match.get("status") == "finished"]),
            },
        }
    )
    return payload


def support_payload(account=None, export=None):
    account = account or guest_account()
    payload = page_payload(
        "support",
        "Support + Admin Safety",
        "Account export, account reset and token-protected admin grants for the Rebirth MVP.",
        primary_label="Open Profile",
        primary_href="/rebirth/profile",
    )
    payload.update(
        {
            "account": account,
            "export": export,
            "checks": [
                "Player export is self-service and scoped to the signed-in account.",
                "Reset requires an explicit confirmation payload.",
                "Admin grant is disabled unless REBIRTH_ADMIN_TOKEN is configured.",
                "Every admin grant writes admin_audit_log and economy_ledger entries.",
            ],
        }
    )
    return payload


def desktop_payload():
    payload = page_payload(
        "desktop",
        "Desktop Arena Polish",
        "The desktop shell frames the portrait board with useful Rebirth status rails instead of stretching the game.",
        primary_label="Open Arena",
        primary_href="/rebirth",
    )
    payload.update(
        {
            "checks": [
                "Portrait board remains fixed and centered.",
                "Desktop rails add status without changing game rules.",
                "No document scroll on the playable arena.",
                "Mobile keeps the single-screen composition.",
            ]
        }
    )
    return payload


def onboarding_payload(account=None, progression=None):
    account = account or guest_account()
    progress = progression or {}
    payload = page_payload(
        "tutorial",
        "Onboarding/Tutorial Rebirth",
        "A short playable tutorial path for the persisted Rebirth loop.",
        primary_label="Play Tutorial Clash",
        primary_href="/rebirth",
    )
    payload.update(
        {
            "account": account,
            "steps": deepcopy(TUTORIAL_STEPS),
            "current_step": int(progress.get("tutorial_step", 0) or 0),
            "complete": bool(progress.get("tutorial_complete", False)),
        }
    )
    return payload


def balance_payload(simulation=None):
    payload = page_payload(
        "balance",
        "Balance + Bot Tuning",
        "Deterministic simulations watch card, ability and bot personality impact without adding legacy battle systems.",
        primary_label="Open Arena",
        primary_href="/rebirth",
    )
    payload.update(
        {
            "simulation": simulation,
            "notes": [
                "Defensive bot prioritizes guarded wins and absorption lines.",
                "Aggressive bot pushes high attack and quick pressure.",
                "Opportunist bot looks for ability swings, finishers and pressure windows.",
                "The simulation is deterministic, capped and reports per-card/per-ability impact.",
                "The player simulator now evolves available duplicates before choosing a tactical clash line.",
            ],
        }
    )
    return payload


def release_payload():
    payload = page_payload(
        "release",
        "Release Candidate Hygiene",
        "The final gate for Rebirth deploy truth, offline cache, tests and legacy containment.",
        primary_label="Health",
        primary_href="/health",
    )
    payload.update(
        {
            "checks": deepcopy(RELEASE_CHECKS),
            "commands": [
                "python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py services/rebirth_match_store.py services/rebirth_product.py services/rebirth_persistence.py services/rebirth_balance.py",
                "python3 -m pytest -q",
                "python3 tools/rebirth_balance_report.py --matches 120 --output docs/REBIRTH_BALANCE_REPORT.md",
                "node --check static/js/rebirth.js",
                "node --check static/js/service-worker.js",
                "node --check static/js/pwa.js",
                "node --check static/js/rebirth_product.js",
            ],
        }
    )
    return payload
