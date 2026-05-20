import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from collections import Counter
from datetime import datetime, timezone

from services.rebirth_cards import PLAYER_DECK, get_card


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

HASH_ITERATIONS = 180000
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,24}$")

ACHIEVEMENTS = [
    {
        "key": "founder",
        "name": "Rebirth Founder",
        "copy": "Create a Rebirth account.",
    },
    {
        "key": "first_clash",
        "name": "First Clash",
        "copy": "Resolve one persisted Rebirth clash.",
    },
    {
        "key": "first_win",
        "name": "First Victory",
        "copy": "Win a persisted Rebirth match.",
    },
    {
        "key": "first_booster",
        "name": "Booster Opened",
        "copy": "Open one no-payment Rebirth booster.",
    },
    {
        "key": "daily_claimed",
        "name": "Daily Spark",
        "copy": "Claim the first-clash daily reward.",
    },
    {
        "key": "tutorial_complete",
        "name": "Awakened",
        "copy": "Complete the Rebirth onboarding path.",
    },
]


class RebirthPersistenceError(ValueError):
    def __init__(self, message, code="persistence_error", status=400):
        super().__init__(message)
        self.code = code
        self.status = status


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_email(email):
    return str(email or "").strip().lower()


def normalize_username(username):
    return str(username or "").strip()


def calculate_level(xp):
    return max(1, int(xp or 0) // 500 + 1)


def next_level_xp(level):
    return int(level) * 500


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS,
    ).hex()
    return salt, digest


def verify_password(password, salt, expected_digest):
    _, digest = hash_password(password, salt=salt)
    return hmac.compare_digest(digest, expected_digest)


def starter_collection_counts():
    return Counter(PLAYER_DECK)


class RebirthRepository:
    def __init__(self, db_path):
        self.db_path = db_path

    def connect(self):
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def ensure_schema(self):
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_collection (
                    user_id INTEGER NOT NULL,
                    card_id TEXT NOT NULL,
                    copies INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, card_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_loadout (
                    user_id INTEGER NOT NULL,
                    slot INTEGER NOT NULL,
                    card_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, slot),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_progress (
                    user_id INTEGER PRIMARY KEY,
                    xp INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    clashes INTEGER NOT NULL DEFAULT 0,
                    boosters_opened INTEGER NOT NULL DEFAULT 0,
                    tutorial_step INTEGER NOT NULL DEFAULT 0,
                    tutorial_complete INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS reward_claims (
                    user_id INTEGER NOT NULL,
                    reward_key TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, reward_key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS booster_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    booster_id TEXT NOT NULL,
                    seed TEXT NOT NULL,
                    cards_json TEXT NOT NULL,
                    opened_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id INTEGER NOT NULL,
                    achievement_key TEXT NOT NULL,
                    unlocked_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, achievement_key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )

    def create_user(self, username, email, password):
        self.ensure_schema()
        username = normalize_username(username)
        email = normalize_email(email)
        password = str(password or "")
        if not USERNAME_RE.match(username):
            raise RebirthPersistenceError(
                "Username must be 3-24 characters and use letters, numbers or underscores.",
                "invalid_auth_payload",
            )
        if "@" not in email or "." not in email.split("@")[-1]:
            raise RebirthPersistenceError("A valid email is required.", "invalid_auth_payload")
        if len(password) < 8:
            raise RebirthPersistenceError("Password must be at least 8 characters.", "invalid_auth_payload")

        salt, digest = hash_password(password)
        now = utc_now()
        try:
            with self.connect() as db:
                cursor = db.execute(
                    """
                    INSERT INTO users (username, email, password_salt, password_hash, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (username, email, salt, digest, now),
                )
                user_id = int(cursor.lastrowid)
                self._seed_user_state(db, user_id, now)
        except sqlite3.IntegrityError as exc:
            raise RebirthPersistenceError(
                "A Rebirth account with this username or email already exists.",
                "auth_conflict",
                status=409,
            ) from exc
        return self.get_user(user_id)

    def authenticate(self, email, password):
        self.ensure_schema()
        email = normalize_email(email)
        with self.connect() as db:
            row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row or not verify_password(password, row["password_salt"], row["password_hash"]):
            raise RebirthPersistenceError("Invalid email or password.", "invalid_credentials", status=401)
        return self.get_user(row["id"])

    def change_password(self, user_id, current_password, new_password):
        self.ensure_schema()
        new_password = str(new_password or "")
        if len(new_password) < 8:
            raise RebirthPersistenceError("Password must be at least 8 characters.", "invalid_auth_payload")
        with self.connect() as db:
            row = db.execute(
                "SELECT password_salt, password_hash FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if not row or not verify_password(current_password, row["password_salt"], row["password_hash"]):
                raise RebirthPersistenceError("Current password is invalid.", "invalid_credentials", status=401)
            salt, digest = hash_password(new_password)
            db.execute(
                "UPDATE users SET password_salt = ?, password_hash = ? WHERE id = ?",
                (salt, digest, user_id),
            )
        return self.get_user(user_id)

    def get_user(self, user_id):
        if not user_id:
            return None
        self.ensure_schema()
        with self.connect() as db:
            row = db.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def _seed_user_state(self, db, user_id, now):
        for card_id, copies in starter_collection_counts().items():
            db.execute(
                """
                INSERT INTO user_collection (user_id, card_id, copies, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, card_id, int(copies), now),
            )
        for slot, card_id in enumerate(DEFAULT_LOADOUT, start=1):
            db.execute(
                """
                INSERT INTO user_loadout (user_id, slot, card_id, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, slot, card_id, now),
            )
        db.execute(
            """
            INSERT INTO user_progress (user_id, xp, wins, losses, clashes, boosters_opened, tutorial_step, tutorial_complete, updated_at)
            VALUES (?, 0, 0, 0, 0, 0, 0, 0, ?)
            """,
            (user_id, now),
        )
        self._unlock_achievements(db, user_id, ["founder"], now)

    def _unlock_achievements(self, db, user_id, keys, now=None):
        now = now or utc_now()
        valid_keys = {achievement["key"] for achievement in ACHIEVEMENTS}
        for key in keys:
            if key not in valid_keys:
                continue
            db.execute(
                """
                INSERT OR IGNORE INTO user_achievements (user_id, achievement_key, unlocked_at)
                VALUES (?, ?, ?)
                """,
                (user_id, key, now),
            )

    def _sync_achievements(self, db, user_id, now=None):
        now = now or utc_now()
        user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return

        keys = ["founder"]
        progress = db.execute("SELECT * FROM user_progress WHERE user_id = ?", (user_id,)).fetchone()
        if progress:
            if int(progress["clashes"]) > 0:
                keys.append("first_clash")
            if int(progress["wins"]) > 0:
                keys.append("first_win")
            if int(progress["boosters_opened"]) > 0:
                keys.append("first_booster")
            if bool(progress["tutorial_complete"]):
                keys.append("tutorial_complete")
        daily = db.execute(
            "SELECT 1 FROM reward_claims WHERE user_id = ? AND reward_key = ?",
            (user_id, "daily_first_clash"),
        ).fetchone()
        if daily:
            keys.append("daily_claimed")
        self._unlock_achievements(db, user_id, keys, now)

    def collection_counts(self, user_id):
        self.ensure_schema()
        with self.connect() as db:
            rows = db.execute(
                "SELECT card_id, copies FROM user_collection WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        return Counter({row["card_id"]: int(row["copies"]) for row in rows})

    def loadout_card_ids(self, user_id):
        self.ensure_schema()
        with self.connect() as db:
            rows = db.execute(
                "SELECT card_id FROM user_loadout WHERE user_id = ? ORDER BY slot ASC",
                (user_id,),
            ).fetchall()
        card_ids = [row["card_id"] for row in rows]
        return card_ids or list(DEFAULT_LOADOUT)

    def validate_and_save_loadout(self, user_id, card_ids):
        selected = self._validate_owned_cards(user_id, card_ids)
        now = utc_now()
        with self.connect() as db:
            db.execute("DELETE FROM user_loadout WHERE user_id = ?", (user_id,))
            for slot, card_id in enumerate(selected, start=1):
                db.execute(
                    """
                    INSERT INTO user_loadout (user_id, slot, card_id, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, slot, card_id, now),
                )
        return selected

    def _validate_owned_cards(self, user_id, card_ids):
        if not isinstance(card_ids, list):
            raise RebirthPersistenceError("card_ids must be a list.", "invalid_loadout")
        selected = [str(card_id) for card_id in card_ids if str(card_id or "").strip()]
        if len(selected) != 8:
            raise RebirthPersistenceError("Rebirth loadout requires exactly 8 cards.", "invalid_loadout")
        owned = self.collection_counts(user_id)
        selected_counts = Counter(selected)
        for card_id, amount in selected_counts.items():
            try:
                get_card(card_id)
            except ValueError as exc:
                raise RebirthPersistenceError(f"{card_id} is not a Rebirth card.", "invalid_loadout") from exc
            if owned.get(card_id, 0) < amount:
                raise RebirthPersistenceError(f"{card_id} exceeds owned copies.", "invalid_loadout")
        return selected

    def add_cards(self, user_id, cards):
        now = utc_now()
        with self.connect() as db:
            for card in cards:
                db.execute(
                    """
                    INSERT INTO user_collection (user_id, card_id, copies, updated_at)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(user_id, card_id) DO UPDATE SET
                        copies = copies + 1,
                        updated_at = excluded.updated_at
                    """,
                    (user_id, card["id"], now),
                )

    def record_booster(self, user_id, booster, seed):
        self.ensure_schema()
        cards = booster.get("cards", [])
        now = utc_now()
        self.add_cards(user_id, cards)
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO booster_history (user_id, booster_id, seed, cards_json, opened_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    booster.get("booster_id", "starter_booster_demo"),
                    str(seed or ""),
                    json.dumps([card["id"] for card in cards]),
                    now,
                ),
            )
            db.execute(
                """
                UPDATE user_progress
                SET boosters_opened = boosters_opened + 1,
                    xp = xp + 40,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (now, user_id),
            )
            self._unlock_achievements(db, user_id, ["first_booster"], now)

    def booster_history(self, user_id, limit=5):
        self.ensure_schema()
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT booster_id, cards_json, opened_at
                FROM booster_history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        history = []
        for row in rows:
            card_ids = json.loads(row["cards_json"])
            history.append(
                {
                    "booster_id": row["booster_id"],
                    "opened_at": row["opened_at"],
                    "cards": [get_card(card_id) for card_id in card_ids],
                }
            )
        return history

    def progression(self, user_id):
        self.ensure_schema()
        with self.connect() as db:
            row = db.execute("SELECT * FROM user_progress WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return None
        xp = int(row["xp"])
        level = calculate_level(xp)
        return {
            "level": level,
            "xp": xp,
            "next_level_xp": next_level_xp(level),
            "wins": int(row["wins"]),
            "losses": int(row["losses"]),
            "clashes": int(row["clashes"]),
            "boosters_opened": int(row["boosters_opened"]),
            "tutorial_step": int(row["tutorial_step"]),
            "tutorial_complete": bool(row["tutorial_complete"]),
        }

    def record_clash_result(self, user_id, public_match_state):
        if not user_id:
            return None
        now = utc_now()
        is_finished = bool(public_match_state.get("is_finished"))
        winner = public_match_state.get("winner")
        win_delta = 1 if is_finished and winner == "player" else 0
        loss_delta = 1 if is_finished and winner == "bot" else 0
        xp_delta = 25 + (75 if win_delta else 0) + (25 if loss_delta else 0)
        with self.connect() as db:
            db.execute(
                """
                UPDATE user_progress
                SET clashes = clashes + 1,
                    wins = wins + ?,
                    losses = losses + ?,
                    xp = xp + ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (win_delta, loss_delta, xp_delta, now, user_id),
            )
            unlocked = ["first_clash"]
            if win_delta:
                unlocked.append("first_win")
            self._unlock_achievements(db, user_id, unlocked, now)
        return self.progression(user_id)

    def claim_daily_reward(self, user_id):
        progress = self.progression(user_id)
        if not progress or progress["clashes"] < 1:
            raise RebirthPersistenceError("Play at least one clash before claiming the daily reward.", "reward_locked", 409)
        reward_key = "daily_first_clash"
        now = utc_now()
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO reward_claims (user_id, reward_key, claimed_at) VALUES (?, ?, ?)",
                    (user_id, reward_key, now),
                )
                db.execute(
                    "UPDATE user_progress SET xp = xp + 25, updated_at = ? WHERE user_id = ?",
                    (now, user_id),
                )
                self._unlock_achievements(db, user_id, ["daily_claimed"], now)
        except sqlite3.IntegrityError as exc:
            raise RebirthPersistenceError("Daily reward already claimed.", "reward_already_claimed", 409) from exc
        return {"reward_key": reward_key, "xp": 25, "progression": self.progression(user_id)}

    def complete_tutorial_step(self, user_id, step):
        step = max(1, min(4, int(step or 1)))
        now = utc_now()
        current = self.progression(user_id)
        if not current:
            raise RebirthPersistenceError("Account progress is missing.", "missing_progress", 404)
        xp_delta = 60 if not current["tutorial_complete"] and step >= 4 else 10
        with self.connect() as db:
            db.execute(
                """
                UPDATE user_progress
                SET tutorial_step = MAX(tutorial_step, ?),
                    tutorial_complete = CASE WHEN ? >= 4 THEN 1 ELSE tutorial_complete END,
                    xp = xp + ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (step, step, xp_delta, now, user_id),
            )
            if step >= 4:
                self._unlock_achievements(db, user_id, ["tutorial_complete"], now)
        return {"step": step, "xp": xp_delta, "progression": self.progression(user_id)}

    def achievements(self, user_id):
        self.ensure_schema()
        with self.connect() as db:
            self._sync_achievements(db, user_id)
            rows = db.execute(
                """
                SELECT achievement_key, unlocked_at
                FROM user_achievements
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchall()
        unlocked = {row["achievement_key"]: row["unlocked_at"] for row in rows}
        payload = []
        for achievement in ACHIEVEMENTS:
            key = achievement["key"]
            payload.append(
                {
                    "key": key,
                    "name": achievement["name"],
                    "copy": achievement["copy"],
                    "unlocked": key in unlocked,
                    "unlocked_at": unlocked.get(key),
                }
            )
        return payload

    def profile(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return None
        collection = self.collection_counts(user_id)
        loadout = self.loadout_card_ids(user_id)
        history = self.booster_history(user_id, limit=3)
        achievements = self.achievements(user_id)
        unlocked = [achievement for achievement in achievements if achievement["unlocked"]]
        return {
            "user": user,
            "progression": self.progression(user_id),
            "collection": {
                "owned_cards": sum(collection.values()),
                "unique_owned": len([card_id for card_id, copies in collection.items() if copies > 0]),
                "loadout_size": len(loadout),
            },
            "achievements": achievements,
            "unlocked_achievements": len(unlocked),
            "recent_boosters": history,
        }
