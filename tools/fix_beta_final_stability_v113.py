from pathlib import Path
import re
import shutil
from datetime import datetime

ROOT = Path(".")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "backups" / f"beta_final_stability_v113_{STAMP}"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

FILES = [
    "app.py",
    "templates/beta_launch.html",
    "templates/shop.html",
    "capacitor.config.json",
]

def backup(path: Path):
    if path.exists():
        dest = BACKUP_DIR / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")

for file in FILES:
    backup(ROOT / file)

app_path = ROOT / "app.py"
app = read(app_path)

# ------------------------------------------------------------
# 1) Harden admin_required_redirect while preserving current call style.
# Expected usage in app.py:
#   auth_redirect = admin_required_redirect()
#   if auth_redirect:
#       return auth_redirect
# ------------------------------------------------------------
admin_pattern = re.compile(
    r"def admin_required_redirect\(\):\n(?P<body>(?:    .*\n|    \n)*)",
)

match = admin_pattern.search(app)
if match:
    start = match.start()
    body_start = match.start("body")
    # Stop before the next top-level decorator/function/route after function body.
    tail = app[body_start:]
    next_match = re.search(r"\n(?=@app\.route|@socketio\.on|def\s+\w+\(|class\s+\w+\()", tail)
    if next_match:
        end = body_start + next_match.start()
    else:
        end = match.end()

    new_admin = '''def admin_required_redirect():
    """Return a redirect response when the current user is not an admin.

    Kept as a response-returning helper because existing admin routes call it
    manually instead of using it as a decorator.
    """
    user_id = session.get("user_id")

    if not user_id:
        flash("Login required.", "warning")
        return redirect(url_for("login"))

    user = User.query.get(user_id)

    if not user:
        session.clear()
        flash("Login required.", "warning")
        return redirect(url_for("login"))

    is_admin = bool(
        getattr(user, "is_admin", False)
        or getattr(user, "admin", False)
        or getattr(user, "role", "") == "admin"
    )

    if not is_admin:
        flash("Admin access required.", "danger")
        return redirect(url_for("index"))

    return None
'''
    app = app[:start] + new_admin + app[end:]
    print("OK: admin_required_redirect hardened.")
else:
    print("WARN: admin_required_redirect not found. No admin helper patch applied.")

# ------------------------------------------------------------
# 2) Add beta starting hand helper.
# Goal: reduce dead first turns in training/mobile beta.
# Guarantees best effort:
#   - at least one playable card with energy 2
#   - at least one playable Monster with energy 2
# It preserves deck mutation by drawing from the same deck list.
# ------------------------------------------------------------
if "def draw_beta_starting_hand(" not in app:
    insert_anchor = "def admin_required_redirect():"
    helper = r'''
def _card_cost_value(card):
    try:
        return int(card.get("cost", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _is_playable_with_energy(card, energy):
    return _card_cost_value(card) <= energy


def _is_playable_monster_with_energy(card, energy):
    return card.get("type") == "Monster" and _is_playable_with_energy(card, energy)


def draw_beta_starting_hand(deck, size=5, starting_energy=2):
    """Draw a beta-friendly starting hand from a mutable deck list.

    This is a first-session safety net. It avoids a dead mobile opening where
    the player has no playable card or no playable monster.
    """
    hand = draw_starting_hand(deck, size)

    has_playable = any(_is_playable_with_energy(card, starting_energy) for card in hand)
    has_playable_monster = any(_is_playable_monster_with_energy(card, starting_energy) for card in hand)

    if has_playable and has_playable_monster:
        return hand

    def swap_in(predicate):
        for deck_index, candidate in enumerate(deck):
            if predicate(candidate):
                # Prefer replacing the highest-cost non-matching card.
                replace_index = None
                replacement_score = -1

                for hand_index, current in enumerate(hand):
                    if predicate(current):
                        continue

                    score = _card_cost_value(current)

                    if score > replacement_score:
                        replacement_score = score
                        replace_index = hand_index

                if replace_index is None and hand:
                    replace_index = len(hand) - 1

                if replace_index is not None:
                    removed = hand[replace_index]
                    hand[replace_index] = candidate
                    deck[deck_index] = removed
                return

    if not has_playable_monster:
        swap_in(lambda card: _is_playable_monster_with_energy(card, starting_energy))

    has_playable = any(_is_playable_with_energy(card, starting_energy) for card in hand)

    if not has_playable:
        swap_in(lambda card: _is_playable_with_energy(card, starting_energy))

    return hand

'''
    pos = app.find(insert_anchor)
    if pos != -1:
        app = app[:pos] + helper + "\n" + app[pos:]
        print("OK: draw_beta_starting_hand helper added.")
    else:
        print("WARN: insert anchor not found for beta starting hand helper.")
else:
    print("OK: draw_beta_starting_hand already exists.")

# Replace player starting hand draw only.
if "hand = draw_starting_hand(deck, 5)" in app:
    app = app.replace(
        "hand = draw_starting_hand(deck, 5)",
        "hand = draw_beta_starting_hand(deck, 5, starting_energy=2)",
        1
    )
    print("OK: player starting hand now uses beta-friendly draw.")
else:
    print("WARN: exact player draw_starting_hand(deck, 5) pattern not found.")

# ------------------------------------------------------------
# 3) Private room safety net.
# If any route/socket calls a missing helper, define a conservative fallback.
# This prevents beta crashes while private rooms are not core loop.
# ------------------------------------------------------------
private_refs = [
    "create_private_room",
    "join_private_room",
    "get_private_room",
    "private_room_exists",
]

for name in private_refs:
    if re.search(rf"\b{name}\(", app) and not re.search(rf"def\s+{name}\(", app):
        app += f'''


def {name}(*args, **kwargs):
    """Temporary beta fallback for private-room flow.

    Private rooms are intentionally not part of the first closed beta core loop.
    This fallback prevents NameError crashes if an old UI route reaches this path.
    """
    return None
'''
        print(f"OK: added fallback for missing {name}().")

# ------------------------------------------------------------
# 4) Standardize old public domain remnants to current Render production URL.
# ------------------------------------------------------------
app = app.replace("https://ambitionzgame.com", "https://ambition-tcg.onrender.com")
write(app_path, app)

for template in ["templates/beta_launch.html", "templates/shop.html"]:
    path = ROOT / template
    if path.exists():
        content = read(path)
        content = content.replace("https://ambitionzgame.com", "https://ambition-tcg.onrender.com")
        write(path, content)
        print(f"OK: standardized URLs in {template}")

# ------------------------------------------------------------
# 5) Capacitor consistency.
# Keep current appId, but make server URL explicit and stable.
# ------------------------------------------------------------
cap_path = ROOT / "capacitor.config.json"
if cap_path.exists():
    cap = read(cap_path)
    cap = cap.replace("https://ambitionzgame.com", "https://ambition-tcg.onrender.com")
    cap = cap.replace("https://ambition-tcg.onrender.com/", "https://ambition-tcg.onrender.com")
    write(cap_path, cap)
    print("OK: capacitor.config.json production URL checked.")

print(f"\nBackup created at: {BACKUP_DIR}")
