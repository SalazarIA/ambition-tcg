import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache, wraps
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


_persistence_logger = logging.getLogger("rebirth.persistence")
# Detalhes SQL ficam nos logs. A resposta pública só os expõe por opt-in
# temporário em ambientes de diagnóstico.
_EXPOSE_DB_ERRORS = os.environ.get("REBIRTH_EXPOSE_DB_ERRORS", "false").strip().lower() in {"1", "true", "yes"}


def _db_error_message(default_msg, cause):
    """Mensagem do erro Postgres, com detalhe original opcional via env var.

    Sempre loga via stderr (capturado pelo Render). Em dev/staging, opt-in
    REBIRTH_EXPOSE_DB_ERRORS=true também devolve o detalhe no payload de
    resposta — útil pra debug remoto sem precisar SSH no DB.
    """
    cause_repr = ""
    if cause is not None:
        orig = getattr(cause, "orig", None)
        cause_repr = f"{type(cause).__name__}: {orig if orig is not None else cause}"
    _persistence_logger.exception("rebirth_persistence: %s | cause=%s", default_msg, cause_repr)
    if _EXPOSE_DB_ERRORS and cause_repr:
        return f"{default_msg} [{cause_repr}]"
    return default_msg

from services.rebirth_cards import (
    CARD_CATALOG,
    PLAYER_DECK,
    STARTER_DECK_SIZE,
    get_card,
    is_monster,
    is_spell,
    is_trap,
    validate_deck_distribution,
)
from services.rebirth_campaign import CAMPAIGN_VERSION
from services.rebirth_schema import SCHEMA_VERSION, normalize_database_url, validate_schema


DEFAULT_LOADOUT = list(PLAYER_DECK)

HASH_ITERATIONS = 180000
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,24}$")
POSTGRES_SERIALIZATION_MAX_ATTEMPTS = 3
POSTGRES_SERIALIZATION_BACKOFF_SECONDS = 0.02
ACHIEVEMENTS = [
    {
        "key": "founder",
        "name": "Fundador Rebirth",
        "copy": "Crie uma conta Rebirth.",
    },
    {
        "key": "first_clash",
        "name": "Primeiro Clash",
        "copy": "Resolva um clash Rebirth persistido.",
    },
    {
        "key": "first_win",
        "name": "Primeira Vitória",
        "copy": "Vença uma partida Rebirth persistida.",
    },
    {
        "key": "first_booster",
        "name": "Booster Aberto",
        "copy": "Abra um booster Rebirth sem pagamento.",
    },
    {
        "key": "daily_claimed",
        "name": "Centelha Diária",
        "copy": "Resgate a recompensa diária do primeiro clash.",
    },
    {
        "key": "tutorial_complete",
        "name": "Desperto",
        "copy": "Conclua a introdução do Rebirth.",
    },
    {
        "key": "first_campaign_clear",
        "name": "Coroa Cinzenta",
        "copy": "Derrote o Rei Cinzento e conclua a campanha.",
    },
    {
        "key": "no_damage_win",
        "name": "Intocavel",
        "copy": "Venca um encontro de campanha sem perder PV.",
    },
    {
        "key": "evolve_master",
        "name": "Mestre da Evolucao",
        "copy": "Venca um encontro apos evoluir uma unidade.",
    },
    {
        "key": "shadow_slayer",
        "name": "Cacador do Eclipse",
        "copy": "Derrote o Parasita do Eclipse.",
    },
    {
        "key": "3_win_streak",
        "name": "Marcha Imparavel",
        "copy": "Venca tres encontros de campanha em sequencia.",
    },
]


class RebirthPersistenceError(ValueError):
    def __init__(self, message, code="persistence_error", status=400):
        super().__init__(message)
        self.code = code
        self.status = status


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")



WALLET_CURRENCY_ALIASES = {
    "GOLD": "GOLD",
    "COIN": "COINZ",
    "COINS": "COINZ",
    "COINZ": "COINZ",
    "PREMIUM": "COINZ",
    "GEM": "COINZ",
    "GEMS": "COINZ",
}


def normalize_wallet_currency(currency):
    normalized = str(currency or "GOLD").strip().upper()
    normalized = WALLET_CURRENCY_ALIASES.get(normalized, normalized)
    if normalized not in {"GOLD", "COINZ"}:
        raise RebirthPersistenceError("A moeda deve ser GOLD ou COINZ.", "invalid_wallet_currency", status=400)
    return normalized


def normalize_market_currency(currency_type):
    currency = normalize_wallet_currency(currency_type or "GOLD")
    if currency != "GOLD":
        raise RebirthPersistenceError(
            "O mercado opera apenas com GOLD enquanto monetizacao estiver desativada.",
            "premium_market_disabled",
            status=409,
        )
    return currency


def _normalize_market_price(price):
    try:
        price = int(price)
    except (TypeError, ValueError) as exc:
        raise RebirthPersistenceError("O preço de mercado deve ser um número inteiro positivo.", "invalid_market_price", status=400) from exc
    if price <= 0:
        raise RebirthPersistenceError("O preço de mercado deve ser um número inteiro positivo.", "invalid_market_price", status=400)
    return price


def _market_fee(price):
    return max(1, int(price * 5 // 100)) if price >= 20 else 1


def _normalize_wallet_entry(entry_type, amount):
    entry_type = str(entry_type or "").strip().upper()
    if entry_type not in {"CREDIT", "DEBIT"}:
        raise RebirthPersistenceError("entry_type da carteira deve ser CREDIT ou DEBIT.", "invalid_wallet_entry", status=400)
    amount = int(amount or 0)
    if amount <= 0:
        raise RebirthPersistenceError("O valor do extrato da carteira deve ser positivo.", "invalid_wallet_amount", status=400)
    return entry_type, amount


def economy_idempotency_key(scope, *parts):
    payload = json.dumps(
        {
            "scope": str(scope or "economy").strip().lower(),
            "parts": [str(part or "") for part in parts],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{str(scope or 'economy').strip().lower()}:{digest[:48]}"



def _is_serialization_failure(error):
    """Return true only for PostgreSQL serialization aborts (SQLSTATE 40001)."""
    pending = [error]
    seen = set()
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        if str(getattr(current, "sqlstate", "") or getattr(current, "pgcode", "")) == "40001":
            return True
        pending.extend(
            nested
            for nested in (
                getattr(current, "orig", None),
                getattr(current, "__cause__", None),
                getattr(current, "__context__", None),
            )
            if nested is not None
        )
    return False


def _retry_postgres_serialization_write(method):
    """Retry an atomic PostgreSQL write after SQLSTATE 40001 aborts."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        attempts = self.serialization_retry_attempts if self.backend == "postgresql" else 1
        for attempt in range(attempts):
            try:
                return method(self, *args, **kwargs)
            except Exception as error:
                retryable = self.backend == "postgresql" and _is_serialization_failure(error)
                if not retryable:
                    raise
                if attempt + 1 >= attempts:
                    raise RebirthPersistenceError(
                        "A transacao PostgreSQL excedeu o limite de repeticoes por concorrencia.",
                        "serialization_retry_exhausted",
                        status=409,
                    ) from error
                time.sleep(self.serialization_retry_backoff_seconds * (2 ** attempt))
        raise RuntimeError("unreachable serialization retry state")

    return wrapped



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


def _stable_rank(seed, card_id, salt):
    payload = f"{seed}:{salt}:{card_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _ranked_ids(seed, card_ids, salt):
    return sorted(card_ids, key=lambda card_id: (_stable_rank(seed, card_id, salt), card_id))


def deterministic_starter_deck(seed_source):
    seed = str(seed_source or "rebirth-starter")
    monster_pool = [card["id"] for card in CARD_CATALOG if is_monster(card) and int(card.get("tier", 1) or 1) == 1]
    spell_pool = [card["id"] for card in CARD_CATALOG if is_spell(card)]
    trap_pool = [card["id"] for card in CARD_CATALOG if is_trap(card)]
    monster_count = 18 + (int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:2], 16) % 5)
    remaining = STARTER_DECK_SIZE - monster_count
    spell_count = remaining // 2
    trap_count = remaining - spell_count

    ranked_monsters = _ranked_ids(seed, monster_pool, "monster")
    # Anchor on the cheapest monster so opening hands always contain a turn-1
    # playable card, while preserving deterministic per-seed ordering.
    cheap_anchors = [
        card_id for card_id in ranked_monsters
        if int((get_card(card_id) or {}).get("cost", 1) or 1) <= 1
    ]
    duplicate_anchor = (cheap_anchors or ranked_monsters)[0]
    monsters = [duplicate_anchor, duplicate_anchor]
    monsters.extend([card_id for card_id in ranked_monsters[1:] if card_id != duplicate_anchor][: monster_count - 2])
    spells = _ranked_ids(seed, spell_pool, "spell")[:spell_count]
    traps = _ranked_ids(seed, trap_pool, "trap")[:trap_count]
    deck = monsters + spells + traps
    validate_deck_distribution(deck)
    return deck


def starter_collection_counts(seed_source=None):
    return Counter(deterministic_starter_deck(seed_source or "rebirth-starter"))


@lru_cache(maxsize=4)
def _sync_postgres_engine(database_url):
    return create_engine(
        normalize_database_url(database_url),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        future=True,
    )


class _MappingResult:
    def __init__(self, result):
        self.result = result

    @property
    def rowcount(self):
        return int(getattr(self.result, "rowcount", -1) or 0)

    @property
    def lastrowid(self):
        return getattr(self.result, "lastrowid", None)

    def fetchone(self):
        return self.result.mappings().first()

    def fetchall(self):
        return self.result.mappings().all()


class _PostgresConnection:
    """Transactional synchronous PostgreSQL executor for repository commands."""

    def __init__(self, engine):
        self.engine = engine
        self._scope = None
        self.connection = None

    def __enter__(self):
        self._scope = self.engine.begin()
        self.connection = self._scope.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            return self._scope.__exit__(exc_type, exc, traceback)
        except SQLAlchemyError as error:
            raise RebirthPersistenceError(
                _db_error_message("A transacao PostgreSQL nao pode ser concluida.", error),
                "database_write_failed",
                status=409,
            ) from error

    def execute(self, statement, params=()):
        sql = str(statement).strip()
        if sql.upper() == "BEGIN IMMEDIATE":
            return _MappingResult(self.connection.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")))
        sql = self._postgres_sql(sql)
        named_sql, named_params = self._bind(sql, params)
        try:
            return _MappingResult(self.connection.execute(text(named_sql), named_params))
        except IntegrityError:
            raise
        except SQLAlchemyError as error:
            raise RebirthPersistenceError(
                _db_error_message("A operacao PostgreSQL nao pode ser concluida.", error),
                "database_write_failed",
                status=409,
            ) from error

    def _postgres_sql(self, sql):
        if "INSERT OR IGNORE INTO" in sql:
            sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO")
            sql = f"{sql} ON CONFLICT DO NOTHING"
        sql = sql.replace("MAX(copies - 1, 0)", "GREATEST(copies - 1, 0)")
        sql = sql.replace("MAX(locked_copies - 1, 0)", "GREATEST(locked_copies - 1, 0)")
        sql = sql.replace("MAX(tutorial_step, ?)", "GREATEST(tutorial_step, ?)")
        normalized = " ".join(sql.split())
        if normalized.startswith("SELECT copies, locked_copies FROM user_collection WHERE user_id = ? AND card_id = ?"):
            sql = f"{sql} FOR UPDATE"
        if "FROM market_offers" in normalized and "market_offers.id = ? AND market_offers.status = 'ACTIVE'" in normalized:
            sql = f"{sql} FOR UPDATE OF market_offers"
        return sql

    def _bind(self, sql, params):
        if isinstance(params, dict):
            return sql, params
        values = list(params or ())
        fragments = sql.split("?")
        if len(fragments) == 1:
            return sql, {}
        bound = []
        names = {}
        for index, fragment in enumerate(fragments[:-1]):
            key = f"p{index}"
            bound.extend((fragment, f":{key}"))
            names[key] = values[index]
        bound.append(fragments[-1])
        return "".join(bound), names


class RebirthRepository:
    def __init__(
        self,
        db_path=None,
        *,
        database_url=None,
        serialization_retry_attempts=POSTGRES_SERIALIZATION_MAX_ATTEMPTS,
        serialization_retry_backoff_seconds=POSTGRES_SERIALIZATION_BACKOFF_SECONDS,
    ):
        self.database_url = normalize_database_url(database_url or "")
        self.db_path = db_path
        self.backend = "postgresql" if self.database_url else "sqlite_test"
        self.engine = _sync_postgres_engine(self.database_url) if self.database_url else None
        self.serialization_retry_attempts = max(
            1,
            min(POSTGRES_SERIALIZATION_MAX_ATTEMPTS, int(serialization_retry_attempts or 1)),
        )
        self.serialization_retry_backoff_seconds = max(0.0, float(serialization_retry_backoff_seconds or 0.0))
        if not self.database_url and not self.db_path:
            raise RebirthPersistenceError(
                "PostgreSQL nao esta configurado para o runtime Rebirth.",
                "database_not_configured",
                status=503,
            )

    def connect(self):
        if self.backend == "postgresql":
            return _PostgresConnection(self.engine)
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def ensure_schema(self):
        # Validar/criar schema custa round-trips; uma vez por instância basta
        # (o repositório é cacheado por destino em app.rebirth_repo).
        if getattr(self, "_schema_ready", False):
            return
        self._do_ensure_schema()
        self._schema_ready = True

    def _do_ensure_schema(self):
        if self.backend == "postgresql":
            status = validate_schema(self.engine)
            if not status.get("ok"):
                # Self-heal: tenta upgrade automático ANTES de falhar a request.
                # Resolve casos onde Render starter ignora preDeployCommand e o
                # auto-bootstrap do app.py falhou silenciosamente.
                try:
                    from services.rebirth_schema import upgrade_schema

                    _persistence_logger.warning(
                        "ensure_schema detectou schema atrasado (version=%s, missing=%s) — disparando upgrade",
                        status.get("version"),
                        status.get("missing_tables"),
                    )
                    upgrade_schema(self.database_url)
                    status = validate_schema(self.engine)
                    _persistence_logger.warning(
                        "ensure_schema self-heal concluído (version=%s)",
                        status.get("version"),
                    )
                except Exception:
                    _persistence_logger.exception("ensure_schema self-heal falhou")
                if not status.get("ok"):
                    raise RebirthPersistenceError(
                        "O schema PostgreSQL do Rebirth nao esta migrado.",
                        "database_schema_invalid",
                        status=503,
                    )
            return
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    email_verified INTEGER NOT NULL DEFAULT 0,
                    verification_token TEXT,
                    verification_sent_at TEXT,
                    email_verified_at TEXT
                );

                CREATE TABLE IF NOT EXISTS user_sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    revoked_at TEXT,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_collection (
                    user_id INTEGER NOT NULL,
                    card_id TEXT NOT NULL,
                    copies INTEGER NOT NULL DEFAULT 0,
                    locked_copies INTEGER NOT NULL DEFAULT 0,
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

                CREATE TABLE IF NOT EXISTS user_campaign_progress (
                    user_id INTEGER NOT NULL,
                    campaign_version TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    completed_at TEXT,
                    reward_claimed_at TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, campaign_version, node_id),
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

                CREATE TABLE IF NOT EXISTS match_history (
                    match_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    seed TEXT,
                    bot_profile_id TEXT,
                    status TEXT NOT NULL,
                    winner TEXT,
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    final_state_hash TEXT,
                    final_state_json TEXT NOT NULL,
                    runtime_state_json TEXT NOT NULL,
                    campaign_version TEXT,
                    campaign_node TEXT,
                    campaign_attempt INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS match_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    command_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    command_type TEXT NOT NULL,
                    command_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (match_id, command_id),
                    FOREIGN KEY (match_id) REFERENCES match_history(match_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS match_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    event_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (match_id, event_id),
                    FOREIGN KEY (match_id) REFERENCES match_history(match_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS economy_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    resource TEXT NOT NULL,
                    delta INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    reference_type TEXT,
                    reference_id TEXT,
                    balance_after INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS economy_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    reference_id TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS economy_idempotency_keys (
                    user_id INTEGER NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    reference_id TEXT,
                    settled_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    PRIMARY KEY (user_id, idempotency_key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS wallet_ledger (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    currency TEXT NOT NULL CHECK(currency IN ('GOLD', 'COINZ')),
                    entry_type TEXT NOT NULL CHECK(entry_type IN ('CREDIT', 'DEBIT')),
                    amount INTEGER NOT NULL CHECK(amount > 0),
                    source TEXT NOT NULL,
                    reference_id TEXT NOT NULL DEFAULT '',
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS admin_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    user_id INTEGER,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS market_offers (
                    id TEXT PRIMARY KEY,
                    seller_id INTEGER NOT NULL,
                    card_id TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    currency_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS telemetry_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_market_offers_status_created
                    ON market_offers(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_market_offers_seller_status
                    ON market_offers(seller_id, status);
                CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user_currency
                    ON wallet_ledger(user_id, currency, timestamp);
                CREATE INDEX IF NOT EXISTS idx_wallet_ledger_reference
                    ON wallet_ledger(reference_id);
                CREATE INDEX IF NOT EXISTS idx_user_sessions_active
                    ON user_sessions(token_hash, revoked_at);
                CREATE INDEX IF NOT EXISTS idx_telemetry_type_created
                    ON telemetry_events(event_type, created_at);
                CREATE INDEX IF NOT EXISTS idx_user_campaign_progress_nodes
                    ON user_campaign_progress(user_id, campaign_version, node_id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_purchase_reference_once
                    ON economy_transactions(user_id, transaction_type, reference_id)
                    WHERE transaction_type = 'IN_APP_PURCHASE' AND reference_id IS NOT NULL AND reference_id <> '';
                """
            )
            self._ensure_sqlite_column(db, "user_collection", "locked_copies", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_sqlite_column(db, "match_history", "campaign_version", "TEXT")
            self._ensure_sqlite_column(db, "match_history", "campaign_node", "TEXT")
            self._ensure_sqlite_column(db, "match_history", "campaign_attempt", "INTEGER")
            self._ensure_sqlite_column(db, "users", "email_verified", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_sqlite_column(db, "users", "verification_token", "TEXT")
            self._ensure_sqlite_column(db, "users", "verification_sent_at", "TEXT")
            self._ensure_sqlite_column(db, "users", "email_verified_at", "TEXT")
            # S3: ranking ELO por usuário
            self._ensure_sqlite_column(db, "users", "ranking_elo", "INTEGER NOT NULL DEFAULT 1500")
            self._ensure_sqlite_column(db, "users", "ranking_season", "INTEGER NOT NULL DEFAULT 1")
            # K3: decks salvos pelo user (schema v11)
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_decks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    cards_json TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_decks_user
                    ON user_decks(user_id, updated_at DESC);
                """
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_match_history_campaign
                ON match_history(user_id, campaign_version, campaign_node)
                WHERE campaign_node IS NOT NULL
                """
            )
            self._backfill_wallet_ledger(db)

    def _ensure_sqlite_column(self, db, table, column, definition):
        columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _sqlite_columns(self, db, table):
        return {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}

    def _backfill_wallet_ledger(self, db):
        columns = self._sqlite_columns(db, "user_progress")
        legacy_currencies = []
        if "gold" in columns:
            legacy_currencies.append(("gold", "GOLD"))
        if "premium" in columns:
            legacy_currencies.append(("premium", "COINZ"))
        if not legacy_currencies:
            return
        now = utc_now()
        select_columns = ", ".join(["user_id"] + [column for column, _currency in legacy_currencies])
        rows = db.execute(f"SELECT {select_columns} FROM user_progress").fetchall()
        for row in rows:
            user_id = int(row["user_id"])
            for column, currency in legacy_currencies:
                amount = int(row[column] or 0)
                if amount <= 0:
                    continue
                existing = db.execute(
                    "SELECT 1 FROM wallet_ledger WHERE user_id = ? AND currency = ? LIMIT 1",
                    (user_id, currency),
                ).fetchone()
                if existing:
                    continue
                self._record_wallet_entry(
                    db,
                    user_id,
                    currency=currency,
                    entry_type="CREDIT",
                    amount=amount,
                    source="MATCH_REWARD",
                    reference_id=f"legacy:{user_id}:{currency}",
                    now=now,
                )

    def _record_wallet_entry(self, db, user_id, *, currency, entry_type, amount, source, reference_id, now=None):
        entry_type, amount = _normalize_wallet_entry(entry_type, amount)
        db.execute(
            """
            INSERT INTO wallet_ledger (id, user_id, currency, entry_type, amount, source, reference_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                int(user_id),
                normalize_wallet_currency(currency),
                entry_type,
                amount,
                str(source or "MATCH_REWARD").strip().upper(),
                str(reference_id or ""),
                now or utc_now(),
            ),
        )

    def _record_audit_event(self, db, *, actor="system", action, user_id=None, metadata=None, now=None):
        db.execute(
            """
            INSERT INTO admin_audit_log (actor, action, user_id, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(actor or "system"),
                str(action),
                int(user_id) if user_id is not None else None,
                json.dumps(metadata or {}, sort_keys=True),
                now or utc_now(),
            ),
        )

    def record_telemetry_event(self, event_type, payload=None, *, user_id=None):
        self.ensure_schema()
        event_type = str(event_type or "").strip().lower()
        if not event_type or len(event_type) > 80:
            raise RebirthPersistenceError("O tipo do evento de telemetria é inválido.", "invalid_telemetry_event", 400)
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO telemetry_events (user_id, event_type, event_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    int(user_id) if user_id is not None else None,
                    event_type,
                    json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                    utc_now(),
                ),
            )
        return {"event_type": event_type, "recorded": True}

    def query_telemetry_events(self, event_types=None, *, limit=None, since=None):
        self.ensure_schema()
        clauses = []
        params = []
        if event_types:
            placeholders = ",".join("?" for _ in event_types)
            clauses.append(f"event_type IN ({placeholders})")
            params.extend(str(name).strip().lower() for name in event_types)
        if since:
            clauses.append("created_at >= ?")
            params.append(since)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        suffix = "ORDER BY id DESC"
        if limit is not None:
            suffix += " LIMIT ?"
            params.append(int(limit))
        with self.connect() as db:
            rows = db.execute(
                f"SELECT id, user_id, event_type, event_json, created_at FROM telemetry_events {where} {suffix}",
                params,
            ).fetchall()
        events = []
        for row in rows:
            try:
                payload = json.loads(row["event_json"]) if row["event_json"] else {}
            except (TypeError, ValueError):
                payload = {}
            events.append(
                {
                    "id": int(row["id"]),
                    "user_id": row["user_id"],
                    "event_type": row["event_type"],
                    "payload": payload,
                    "created_at": row["created_at"],
                }
            )
        return events

    def _claim_economy_idempotency(self, db, user_id, *, key, scope, reference_id=None, metadata=None, now=None):
        now = now or utc_now()
        metadata = dict(metadata or {})
        key = str(key or "").strip()
        if not key:
            raise RebirthPersistenceError("A chave idempotente da transação é obrigatória.", "missing_idempotency_key", 400)
        try:
            db.execute(
                """
                INSERT INTO economy_idempotency_keys
                    (user_id, idempotency_key, scope, reference_id, settled_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    int(user_id),
                    key,
                    str(scope or "economy").strip().upper(),
                    str(reference_id or ""),
                    now,
                    json.dumps(metadata, sort_keys=True),
                ),
            )
        except (sqlite3.IntegrityError, IntegrityError) as exc:
            raise RebirthPersistenceError(
                "Esta transação econômica já foi liquidada.",
                "transaction_replayed",
                409,
            ) from exc
        return True

    def get_user_balance(self, user_id, currency):
        self.ensure_schema()
        currency = normalize_wallet_currency(currency)
        with self.connect() as db:
            row = db.execute(
                """
                SELECT COALESCE(SUM(CASE WHEN entry_type = 'CREDIT' THEN amount ELSE -amount END), 0) AS balance
                FROM wallet_ledger
                WHERE user_id = ? AND currency = ?
                """,
                (int(user_id), currency),
            ).fetchone()
        return int(row["balance"] or 0)

    def wallet_payload(self, user_id):
        return {
            "GOLD": self.get_user_balance(user_id, "GOLD"),
            "COINZ": self.get_user_balance(user_id, "COINZ"),
            "ledger_source": "wallet_ledger",
        }

    def health_status(self):
        self.ensure_schema()
        with self.connect() as db:
            row = db.execute("SELECT 1 AS available").fetchone()
        return {
            "backend": self.backend,
            "available": bool(row and int(row["available"]) == 1),
            "schema_version": SCHEMA_VERSION if self.backend == "postgresql" else "test-only",
        }

    @_retry_postgres_serialization_write
    def create_user(self, username, email, password):
        self.ensure_schema()
        username = normalize_username(username)
        email = normalize_email(email)
        password = str(password or "")
        if not USERNAME_RE.match(username):
            raise RebirthPersistenceError(
                "O nome de jogador deve ter de 3 a 24 caracteres e usar letras, números ou sublinhados.",
                "invalid_auth_payload",
            )
        if "@" not in email or "." not in email.split("@")[-1]:
            raise RebirthPersistenceError("Informe um email válido.", "invalid_auth_payload")
        if len(password) < 8:
            raise RebirthPersistenceError("A senha deve ter pelo menos 8 caracteres.", "invalid_auth_payload")

        salt, digest = hash_password(password)
        now = utc_now()
        verification_token = secrets.token_urlsafe(32)
        try:
            with self.connect() as db:
                returning = " RETURNING id" if self.backend == "postgresql" else ""
                cursor = db.execute(
                    f"""
                    INSERT INTO users (username, email, password_salt, password_hash, created_at,
                                       email_verified, verification_token, verification_sent_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?){returning}
                    """,
                    (username, email, salt, digest, now, False, verification_token, now),
                )
                user_id = int(cursor.fetchone()["id"] if self.backend == "postgresql" else cursor.lastrowid)
                self._seed_user_state(db, user_id, now, seed_source=f"{user_id}:{username}:{email}")
        except (sqlite3.IntegrityError, IntegrityError) as exc:
            # Detecta se o IntegrityError veio do INSERT INTO users (unique violation
            # legítima) ou de uma seed table (constraint mismatch que estava sendo
            # mascarado como "username/email duplicado"). Mensagem honesta + cause.
            cause_text = ""
            orig = getattr(exc, "orig", None)
            if orig is not None:
                cause_text = f"{type(orig).__name__}: {orig}"
            else:
                cause_text = str(exc)
            _persistence_logger.exception("create_user IntegrityError: %s", cause_text)
            # Postgres usa nomes de constraint (users_username_key, users_email_key, users_pkey).
            # SQLite usa "users.username" / "users.email" no texto do erro.
            user_unique_markers = (
                "users_username_key", "users_email_key", "users_pkey",
                "users.username", "users.email", "users.id",
            )
            is_user_unique = any(marker in cause_text for marker in user_unique_markers)
            if is_user_unique:
                raise RebirthPersistenceError(
                    "Já existe uma conta Rebirth com este nome de jogador ou email.",
                    "auth_conflict",
                    status=409,
                ) from exc
            # Seed table failure — schema mismatch ou bug em _seed_user_state.
            exposed = f"Falha ao provisionar conta. [{cause_text}]" if _EXPOSE_DB_ERRORS else "Falha ao provisionar conta."
            raise RebirthPersistenceError(exposed, "user_seed_failed", status=500) from exc
        user = self.get_user(user_id)
        # Token transiente devolvido só na criação para a rota disparar o email;
        # não é persistido no payload público nem relido por get_user.
        if user is not None:
            user["verification_token"] = verification_token
        return user

    @_retry_postgres_serialization_write
    def create_session(self, user_id, token, *, expires_at):
        self.ensure_schema()
        now = utc_now()
        token_hash = hashlib.sha256(str(token).encode("utf-8")).hexdigest()
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO user_sessions (id, user_id, token_hash, created_at, last_seen_at, revoked_at, expires_at)
                VALUES (?, ?, ?, ?, ?, NULL, ?)
                """,
                (str(uuid.uuid4()), int(user_id), token_hash, now, now, expires_at),
            )

    @_retry_postgres_serialization_write
    def user_for_session(self, token):
        if not token:
            return None
        self.ensure_schema()
        token_hash = hashlib.sha256(str(token).encode("utf-8")).hexdigest()
        now = utc_now()
        with self.connect() as db:
            row = db.execute(
                """
                SELECT users.id, users.username, users.email, users.created_at
                FROM user_sessions
                JOIN users ON users.id = user_sessions.user_id
                WHERE user_sessions.token_hash = ?
                  AND user_sessions.revoked_at IS NULL
                  AND user_sessions.expires_at > ?
                """,
                (token_hash, now),
            ).fetchone()
            if row:
                db.execute(
                    "UPDATE user_sessions SET last_seen_at = ? WHERE token_hash = ?",
                    (now, token_hash),
                )
        return dict(row) if row else None

    @_retry_postgres_serialization_write
    def revoke_session(self, token):
        if not token:
            return
        self.ensure_schema()
        token_hash = hashlib.sha256(str(token).encode("utf-8")).hexdigest()
        with self.connect() as db:
            db.execute(
                "UPDATE user_sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
                (utc_now(), token_hash),
            )

    def authenticate(self, email, password):
        self.ensure_schema()
        email = normalize_email(email)
        with self.connect() as db:
            row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row or not verify_password(password, row["password_salt"], row["password_hash"]):
            raise RebirthPersistenceError("Email ou senha inválidos.", "invalid_credentials", status=401)
        return self.get_user(row["id"])

    @_retry_postgres_serialization_write
    def change_password(self, user_id, current_password, new_password):
        self.ensure_schema()
        new_password = str(new_password or "")
        if len(new_password) < 8:
            raise RebirthPersistenceError("A senha deve ter pelo menos 8 caracteres.", "invalid_auth_payload")
        with self.connect() as db:
            row = db.execute(
                "SELECT password_salt, password_hash FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if not row or not verify_password(current_password, row["password_salt"], row["password_hash"]):
                raise RebirthPersistenceError("A senha atual é inválida.", "invalid_credentials", status=401)
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
            row = db.execute(
                "SELECT id, username, email, created_at, email_verified, email_verified_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        user = dict(row)
        user["email_verified"] = bool(user.get("email_verified"))
        return user

    @_retry_postgres_serialization_write
    def verify_email_token(self, token):
        """Mark a user's email verified from a verification token.

        Idempotent on the token: once consumed the token is cleared, so a
        replayed link returns None (already used / invalid) rather than
        re-verifying. Returns the user dict on success, None otherwise.
        """
        token = str(token or "").strip()
        if not token:
            return None
        self.ensure_schema()
        now = utc_now()
        with self.connect() as db:
            row = db.execute(
                "SELECT id FROM users WHERE verification_token = ?",
                (token,),
            ).fetchone()
            if not row:
                return None
            user_id = int(row["id"])
            db.execute(
                """
                UPDATE users
                SET email_verified = ?, email_verified_at = ?, verification_token = NULL
                WHERE id = ?
                """,
                (True, now, user_id),
            )
        return self.get_user(user_id)

    @_retry_postgres_serialization_write
    def regenerate_verification_token(self, user_id):
        """Issue a fresh verification token for an unverified account.

        Returns the new token, or None if the account is already verified or
        missing. Callers use the token to re-send the verification email.
        """
        if not user_id:
            return None
        self.ensure_schema()
        now = utc_now()
        token = secrets.token_urlsafe(32)
        with self.connect() as db:
            row = db.execute(
                "SELECT email_verified FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if not row or bool(row["email_verified"]):
                return None
            db.execute(
                "UPDATE users SET verification_token = ?, verification_sent_at = ? WHERE id = ?",
                (token, now, user_id),
            )
        return token

    def _seed_user_state(self, db, user_id, now, seed_source=None):
        starter_deck = deterministic_starter_deck(seed_source or f"{user_id}:starter")
        for card_id, copies in Counter(starter_deck).items():
            db.execute(
                """
                INSERT INTO user_collection (user_id, card_id, copies, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, card_id, int(copies), now),
            )
            self._record_ledger_entry(
                db,
                user_id,
                resource=f"card:{card_id}",
                delta=int(copies),
                reason="starter_collection",
                reference_type="account",
                reference_id=str(user_id),
                metadata={"card_id": card_id, "copies": int(copies), "starter_deck_size": len(starter_deck)},
                now=now,
            )
        for slot, card_id in enumerate(starter_deck, start=1):
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
        self._record_wallet_entry(
            db,
            user_id,
            currency="GOLD",
            entry_type="CREDIT",
            amount=1000,
            source="MATCH_REWARD",
            reference_id=f"starter:{user_id}",
            now=now,
        )
        self._record_ledger_entry(
            db,
            user_id,
            resource="gold",
            delta=1000,
            reason="starter_wallet",
            reference_type="account",
            reference_id=str(user_id),
            metadata={"currency_type": "GOLD"},
            now=now,
        )
        self._record_economy_transaction(db, user_id, "STARTER_WALLET", 1000, "GOLD", f"starter:{user_id}", now)
        self._unlock_achievements(db, user_id, ["founder"], now)

    def _record_ledger_entry(
        self,
        db,
        user_id,
        *,
        resource,
        delta,
        reason,
        reference_type=None,
        reference_id=None,
        metadata=None,
        now=None,
    ):
        now = now or utc_now()
        delta = int(delta or 0)
        row = db.execute(
            "SELECT COALESCE(SUM(delta), 0) AS balance FROM economy_ledger WHERE user_id = ? AND resource = ?",
            (user_id, resource),
        ).fetchone()
        balance_after = int(row["balance"] or 0) + delta
        db.execute(
            """
            INSERT INTO economy_ledger
                (user_id, resource, delta, reason, reference_type, reference_id, balance_after, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                resource,
                delta,
                reason,
                reference_type,
                reference_id,
                balance_after,
                json.dumps(metadata or {}, sort_keys=True),
                now,
            ),
        )
        return balance_after

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
                "SELECT card_id, copies, locked_copies FROM user_collection WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        return Counter(
            {
                row["card_id"]: max(0, int(row["copies"] or 0) - int(row["locked_copies"] or 0))
                for row in rows
                if max(0, int(row["copies"] or 0) - int(row["locked_copies"] or 0)) > 0
            }
        )

    def locked_collection_counts(self, user_id):
        self.ensure_schema()
        with self.connect() as db:
            rows = db.execute(
                "SELECT card_id, locked_copies FROM user_collection WHERE user_id = ? AND locked_copies > 0",
                (user_id,),
            ).fetchall()
        return Counter({row["card_id"]: int(row["locked_copies"] or 0) for row in rows})

    def loadout_card_ids(self, user_id):
        self.ensure_schema()
        with self.connect() as db:
            rows = db.execute(
                "SELECT card_id FROM user_loadout WHERE user_id = ? ORDER BY slot ASC",
                (user_id,),
            ).fetchall()
        card_ids = [row["card_id"] for row in rows]
        if card_ids:
            try:
                validate_deck_distribution(card_ids)
                return card_ids
            except ValueError:
                return list(DEFAULT_LOADOUT)
        return list(DEFAULT_LOADOUT)

    @_retry_postgres_serialization_write
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
            raise RebirthPersistenceError("card_ids deve ser uma lista.", "invalid_loadout")
        selected = [str(card_id) for card_id in card_ids if str(card_id or "").strip()]
        try:
            validate_deck_distribution(selected)
        except ValueError as exc:
            raise RebirthPersistenceError(str(exc), "invalid_loadout") from exc
        owned = self.collection_counts(user_id)
        selected_counts = Counter(selected)
        for card_id, amount in selected_counts.items():
            try:
                get_card(card_id)
            except ValueError as exc:
                raise RebirthPersistenceError(f"{card_id} não é uma carta Rebirth.", "invalid_loadout") from exc
            if owned.get(card_id, 0) < amount:
                raise RebirthPersistenceError(f"{card_id} excede as cópias possuídas.", "invalid_loadout")
        return selected

    def _currency_balance(self, db, user_id, currency_type):
        user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise RebirthPersistenceError("A carteira da conta não foi encontrada.", "missing_wallet", status=409)
        currency_type = normalize_wallet_currency(currency_type)
        row = db.execute(
            """
            SELECT COALESCE(SUM(CASE WHEN entry_type = 'CREDIT' THEN amount ELSE -amount END), 0) AS balance
            FROM wallet_ledger
            WHERE user_id = ? AND currency = ?
            """,
            (int(user_id), currency_type),
        ).fetchone()
        return int(row["balance"] or 0)

    def _record_economy_transaction(self, db, user_id, transaction_type, amount, currency, reference_id, now=None):
        db.execute(
            """
            INSERT INTO economy_transactions (user_id, transaction_type, amount, currency, reference_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (int(user_id), str(transaction_type), int(amount), str(currency), str(reference_id or ""), now or utc_now()),
        )

    def _sqlite_offer_payload(self, row):
        if not row:
            return None
        return {
            "id": row["id"],
            "seller_id": int(row["seller_id"]),
            "seller_name": row["seller_name"] if "seller_name" in row.keys() else None,
            "card_id": row["card_id"],
            "card": get_card(row["card_id"]),
            "price": int(row["price"]),
            "currency_type": normalize_market_currency(row["currency_type"]),
            "status": row["status"],
            "created_at": row["created_at"],
        }

    def market_offers(self, exclude_user_id=None, limit=40):
        self.ensure_schema()
        limit = max(1, min(int(limit or 40), 100))
        params = []
        where = ["market_offers.status = 'ACTIVE'"]
        if exclude_user_id:
            where.append("market_offers.seller_id != ?")
            params.append(int(exclude_user_id))
        params.append(limit)
        with self.connect() as db:
            rows = db.execute(
                f"""
                SELECT market_offers.*, users.username AS seller_name
                FROM market_offers
                JOIN users ON users.id = market_offers.seller_id
                WHERE {' AND '.join(where)}
                ORDER BY market_offers.created_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._sqlite_offer_payload(row) for row in rows]

    @_retry_postgres_serialization_write
    def create_market_offer(self, user_id, card_id, price, currency_type):
        self.ensure_schema()
        card = get_card(card_id)
        price = _normalize_market_price(price)
        currency_type = normalize_market_currency(currency_type)
        offer_id = str(uuid.uuid4())
        now = utc_now()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                raise RebirthPersistenceError("A conta do vendedor não foi encontrada.", "missing_user", status=404)
            row = db.execute(
                "SELECT copies, locked_copies FROM user_collection WHERE user_id = ? AND card_id = ?",
                (user_id, card["id"]),
            ).fetchone()
            copies = int(row["copies"] or 0) if row else 0
            locked = int(row["locked_copies"] or 0) if row else 0
            available = max(0, copies - locked)
            if available <= 0:
                raise RebirthPersistenceError("A carta não está disponível para anúncio no mercado.", "card_not_available", status=409)
            loadout_count = db.execute(
                "SELECT COUNT(*) AS amount FROM user_loadout WHERE user_id = ? AND card_id = ?",
                (user_id, card["id"]),
            ).fetchone()["amount"]
            if int(loadout_count or 0) > available - 1:
                raise RebirthPersistenceError(
                    "Esta carta ainda é necessária no baralho ativo de 30 cartas.",
                    "card_locked_by_loadout",
                    status=409,
                )
            db.execute(
                "UPDATE user_collection SET locked_copies = locked_copies + 1, updated_at = ? WHERE user_id = ? AND card_id = ?",
                (now, user_id, card["id"]),
            )
            db.execute(
                """
                INSERT INTO market_offers (id, seller_id, card_id, price, currency_type, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?)
                """,
                (offer_id, user_id, card["id"], price, currency_type, now),
            )
            offer = db.execute(
                """
                SELECT market_offers.*, users.username AS seller_name
                FROM market_offers
                JOIN users ON users.id = market_offers.seller_id
                WHERE market_offers.id = ?
                """,
                (offer_id,),
            ).fetchone()
        return self._sqlite_offer_payload(offer)

    @_retry_postgres_serialization_write
    def buy_market_offer(self, buyer_id, offer_id):
        self.ensure_schema()
        if not offer_id:
            raise RebirthPersistenceError("Informe offer_id.", "missing_market_offer", status=400)
        now = utc_now()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            buyer = db.execute("SELECT id FROM users WHERE id = ?", (buyer_id,)).fetchone()
            if not buyer:
                raise RebirthPersistenceError("A conta do comprador não foi encontrada.", "missing_user", status=404)
            offer = db.execute(
                """
                SELECT market_offers.*, users.username AS seller_name
                FROM market_offers
                JOIN users ON users.id = market_offers.seller_id
                WHERE market_offers.id = ? AND market_offers.status = 'ACTIVE'
                """,
                (str(offer_id),),
            ).fetchone()
            if not offer:
                raise RebirthPersistenceError("A oferta do mercado não está mais ativa.", "market_offer_unavailable", status=409)
            seller_id = int(offer["seller_id"])
            if seller_id == int(buyer_id):
                raise RebirthPersistenceError("Jogadores não podem comprar a própria oferta.", "market_self_buy", status=409)

            currency_type = normalize_market_currency(offer["currency_type"])
            price = int(offer["price"])
            buyer_balance = self._currency_balance(db, buyer_id, currency_type)
            if buyer_balance < price:
                raise RebirthPersistenceError("Saldo insuficiente para a compra no mercado.", "insufficient_balance", status=409)
            seller_balance = self._currency_balance(db, seller_id, currency_type)
            fee = _market_fee(price)
            seller_net = price - fee
            self._record_wallet_entry(
                db,
                buyer_id,
                currency=currency_type,
                entry_type="DEBIT",
                amount=price,
                source="MARKET_SALE",
                reference_id=offer["id"],
                now=now,
            )
            self._record_wallet_entry(
                db,
                seller_id,
                currency=currency_type,
                entry_type="CREDIT",
                amount=price,
                source="MARKET_SALE",
                reference_id=offer["id"],
                now=now,
            )
            self._record_wallet_entry(
                db,
                seller_id,
                currency=currency_type,
                entry_type="DEBIT",
                amount=fee,
                source="MARKET_SALE",
                reference_id=offer["id"],
                now=now,
            )

            collection = db.execute(
                """
                SELECT copies, locked_copies
                FROM user_collection
                WHERE user_id = ? AND card_id = ? AND locked_copies > 0
                """,
                (seller_id, offer["card_id"]),
            ).fetchone()
            if not collection:
                raise RebirthPersistenceError("O item reservado no mercado não foi encontrado.", "market_item_lock_missing", status=409)
            db.execute(
                """
                UPDATE user_collection
                SET copies = MAX(copies - 1, 0),
                    locked_copies = MAX(locked_copies - 1, 0),
                    updated_at = ?
                WHERE user_id = ? AND card_id = ?
                """,
                (now, seller_id, offer["card_id"]),
            )
            db.execute(
                """
                INSERT INTO user_collection (user_id, card_id, copies, locked_copies, updated_at)
                VALUES (?, ?, 1, 0, ?)
                ON CONFLICT(user_id, card_id) DO UPDATE SET
                    copies = user_collection.copies + 1,
                    updated_at = excluded.updated_at
                """,
                (buyer_id, offer["card_id"], now),
            )
            db.execute("UPDATE market_offers SET status = 'SOLD' WHERE id = ?", (offer["id"],))
            self._record_economy_transaction(db, buyer_id, "MARKET_BUY", -price, currency_type, offer["id"], now)
            self._record_economy_transaction(db, seller_id, "MARKET_SALE", seller_net, currency_type, offer["id"], now)
            self._record_economy_transaction(db, seller_id, "MARKET_FEE", -fee, currency_type, offer["id"], now)
            self._record_ledger_entry(
                db,
                buyer_id,
                resource=currency_type.lower(),
                delta=-price,
                reason="market_buy",
                reference_type="market_offer",
                reference_id=offer["id"],
                metadata={"card_id": offer["card_id"], "seller_id": seller_id, "fee": fee},
                now=now,
            )
            self._record_ledger_entry(
                db,
                seller_id,
                resource=currency_type.lower(),
                delta=price,
                reason="market_sale_gross",
                reference_type="market_offer",
                reference_id=offer["id"],
                metadata={"card_id": offer["card_id"], "buyer_id": buyer_id},
                now=now,
            )
            self._record_ledger_entry(
                db,
                seller_id,
                resource=currency_type.lower(),
                delta=-fee,
                reason="market_fee_sink",
                reference_type="market_offer",
                reference_id=offer["id"],
                metadata={"card_id": offer["card_id"], "buyer_id": buyer_id, "fee_rate": "5%"},
                now=now,
            )
            self._record_ledger_entry(
                db,
                seller_id,
                resource=f"card:{offer['card_id']}",
                delta=-1,
                reason="market_card_sold",
                reference_type="market_offer",
                reference_id=offer["id"],
                metadata={"buyer_id": buyer_id},
                now=now,
            )
            self._record_ledger_entry(
                db,
                buyer_id,
                resource=f"card:{offer['card_id']}",
                delta=1,
                reason="market_card_bought",
                reference_type="market_offer",
                reference_id=offer["id"],
                metadata={"seller_id": seller_id},
                now=now,
            )
            sold_offer = db.execute(
                """
                SELECT market_offers.*, users.username AS seller_name
                FROM market_offers
                JOIN users ON users.id = market_offers.seller_id
                WHERE market_offers.id = ?
                """,
                (offer["id"],),
            ).fetchone()
            buyer_wallet = {
                "GOLD": self._currency_balance(db, buyer_id, "GOLD"),
                "COINZ": self._currency_balance(db, buyer_id, "COINZ"),
                "ledger_source": "wallet_ledger",
            }
            seller_wallet = {
                "GOLD": self._currency_balance(db, seller_id, "GOLD"),
                "COINZ": self._currency_balance(db, seller_id, "COINZ"),
                "ledger_source": "wallet_ledger",
            }
        return {
            "offer": self._sqlite_offer_payload(sold_offer),
            "buyer_id": int(buyer_id),
            "seller_id": seller_id,
            "price": price,
            "fee": fee,
            "seller_net": seller_net,
            "currency_type": currency_type,
            "buyer_balance": buyer_wallet[currency_type],
            "seller_balance": seller_wallet[currency_type],
            "buyer_wallet": buyer_wallet,
            "seller_wallet": seller_wallet,
        }

    @_retry_postgres_serialization_write
    def add_cards(self, user_id, cards):
        self.ensure_schema()
        now = utc_now()
        with self.connect() as db:
            for card in cards:
                db.execute(
                    """
                    INSERT INTO user_collection (user_id, card_id, copies, updated_at)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(user_id, card_id) DO UPDATE SET
                        copies = user_collection.copies + 1,
                        updated_at = excluded.updated_at
                    """,
                    (user_id, card["id"], now),
                )
                self._record_ledger_entry(
                    db,
                    user_id,
                    resource=f"card:{card['id']}",
                    delta=1,
                    reason="card_granted",
                    reference_type="collection",
                    reference_id=card["id"],
                    metadata={"card_id": card["id"], "name": card.get("name")},
                    now=now,
                )

    @_retry_postgres_serialization_write
    def record_booster(self, user_id, booster, seed):
        self.ensure_schema()
        cards = booster.get("cards", [])
        now = utc_now()
        booster_id = booster.get("booster_id", "starter_booster_demo")
        seed_key = str(seed or "")
        idempotency_key = economy_idempotency_key("xp", user_id, "booster_opened", booster_id, seed_key)
        replayed = False
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if not self._claim_economy_idempotency(
                db,
                user_id,
                key=idempotency_key,
                scope="XP",
                reference_id=booster_id,
                metadata={"transaction_type": "BOOSTER_OPENED", "seed": seed_key, "booster_id": booster_id},
                now=now,
            ):
                replayed = True
            if replayed:
                pass
            else:
                for card in cards:
                    db.execute(
                        """
                        INSERT INTO user_collection (user_id, card_id, copies, updated_at)
                        VALUES (?, ?, 1, ?)
                        ON CONFLICT(user_id, card_id) DO UPDATE SET
                            copies = user_collection.copies + 1,
                            updated_at = excluded.updated_at
                        """,
                        (user_id, card["id"], now),
                    )
                    self._record_ledger_entry(
                        db,
                        user_id,
                        resource=f"card:{card['id']}",
                        delta=1,
                        reason="booster_card",
                        reference_type="booster",
                        reference_id=booster_id,
                        metadata={"card_id": card["id"], "name": card.get("name"), "seed": str(seed or "")},
                        now=now,
                    )
                db.execute(
                    """
                    INSERT INTO booster_history (user_id, booster_id, seed, cards_json, opened_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        booster_id,
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
                self._record_ledger_entry(
                    db,
                    user_id,
                    resource="xp",
                    delta=40,
                    reason="booster_opened",
                    reference_type="booster",
                    reference_id=booster_id,
                    metadata={"seed": str(seed or ""), "cards": [card["id"] for card in cards], "idempotency_key": idempotency_key},
                    now=now,
                )
                self._record_economy_transaction(
                    db,
                    user_id,
                    "BOOSTER_OPENED",
                    40,
                    "XP",
                    booster_id,
                    now,
                )
                self._unlock_achievements(db, user_id, ["first_booster"], now)
        if replayed:
            raise RebirthPersistenceError("Esta transação de booster já foi liquidada.", "transaction_replayed", 409)

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
            try:
                card_ids = json.loads(row["cards_json"])
            except (TypeError, json.JSONDecodeError):
                card_ids = []
            cards = []
            invalid_card_ids = []
            for card_id in card_ids:
                try:
                    cards.append(get_card(card_id))
                except ValueError:
                    invalid_card_ids.append(str(card_id))
            history.append(
                {
                    "booster_id": row["booster_id"],
                    "opened_at": row["opened_at"],
                    "cards": cards,
                    "invalid_card_ids": invalid_card_ids,
                }
            )
        return history

    def progression(self, user_id):
        self.ensure_schema()
        with self.connect() as db:
            row = db.execute("SELECT * FROM user_progress WHERE user_id = ?", (user_id,)).fetchone()
            daily_claimed = bool(
                db.execute(
                    "SELECT 1 FROM reward_claims WHERE user_id = ? AND reward_key = ?",
                    (user_id, "daily_first_clash"),
                ).fetchone()
            )
        if not row:
            return None
        xp = int(row["xp"])
        level = calculate_level(xp)
        wallet = self.wallet_payload(user_id)
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
            "daily_claimed": daily_claimed,
            "gold": wallet["GOLD"],
            "coinz": wallet["COINZ"],
            "premium": wallet["COINZ"],
            "wallet": wallet,
        }

    def get_campaign_progress(self, user_id, campaign_version=CAMPAIGN_VERSION):
        self.ensure_schema()
        campaign_version = str(campaign_version or CAMPAIGN_VERSION)
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT node_id, attempts, completed_at, reward_claimed_at, updated_at
                FROM user_campaign_progress
                WHERE user_id = ? AND campaign_version = ?
                ORDER BY node_id ASC
                """,
                (int(user_id), campaign_version),
            ).fetchall()
        return {
            "campaign_version": campaign_version,
            "nodes": {
                row["node_id"]: {
                    "attempts": int(row["attempts"] or 0),
                    "completed_at": row["completed_at"],
                    "reward_claimed_at": row["reward_claimed_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            },
        }

    @_retry_postgres_serialization_write
    def start_campaign_attempt(self, user_id, node_id, campaign_version=CAMPAIGN_VERSION):
        self.ensure_schema()
        campaign_version = str(campaign_version or CAMPAIGN_VERSION)
        node_id = str(node_id or "").strip()
        now = utc_now()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                """
                INSERT OR IGNORE INTO user_campaign_progress
                    (user_id, campaign_version, node_id, attempts, completed_at, reward_claimed_at, updated_at)
                VALUES (?, ?, ?, 0, NULL, NULL, ?)
                """,
                (int(user_id), campaign_version, node_id, now),
            )
            lock = " FOR UPDATE" if self.backend == "postgresql" else ""
            row = db.execute(
                """
                SELECT attempts
                FROM user_campaign_progress
                WHERE user_id = ? AND campaign_version = ? AND node_id = ?
                """ + lock,
                (int(user_id), campaign_version, node_id),
            ).fetchone()
            attempt = int(row["attempts"] or 0) + 1
            db.execute(
                """
                UPDATE user_campaign_progress
                SET attempts = ?, updated_at = ?
                WHERE user_id = ? AND campaign_version = ? AND node_id = ?
                """,
                (attempt, now, int(user_id), campaign_version, node_id),
            )
        return attempt

    @_retry_postgres_serialization_write
    def record_campaign_victory(self, user_id, node_id, reward, campaign_version=CAMPAIGN_VERSION, match_state=None):
        self.ensure_schema()
        campaign_version = str(campaign_version or CAMPAIGN_VERSION)
        node_id = str(node_id or "").strip()
        xp_delta = max(0, int((reward or {}).get("xp", 0) or 0))
        idempotency_key = f"campaign_reward:{int(user_id)}:{node_id}:{campaign_version}"
        now = utc_now()
        applied = False
        unlocked = []
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            lock = " FOR UPDATE" if self.backend == "postgresql" else ""
            row = db.execute(
                """
                SELECT attempts, completed_at, reward_claimed_at
                FROM user_campaign_progress
                WHERE user_id = ? AND campaign_version = ? AND node_id = ?
                """ + lock,
                (int(user_id), campaign_version, node_id),
            ).fetchone()
            if not row:
                raise RebirthPersistenceError("A tentativa de campanha nao foi encontrada.", "missing_campaign_attempt", 409)
            if not row["reward_claimed_at"]:
                cursor = db.execute(
                    """
                    INSERT OR IGNORE INTO economy_idempotency_keys
                        (user_id, idempotency_key, scope, reference_id, settled_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(user_id),
                        idempotency_key,
                        "CAMPAIGN",
                        node_id,
                        now,
                        json.dumps({"campaign_version": campaign_version, "node_id": node_id, "xp": xp_delta}, sort_keys=True),
                    ),
                )
                applied = bool(cursor.rowcount)
                db.execute(
                    """
                    UPDATE user_campaign_progress
                    SET completed_at = COALESCE(completed_at, ?),
                        reward_claimed_at = CASE WHEN ? THEN COALESCE(reward_claimed_at, ?) ELSE reward_claimed_at END,
                        updated_at = ?
                    WHERE user_id = ? AND campaign_version = ? AND node_id = ?
                    """,
                    (now, applied, now, now, int(user_id), campaign_version, node_id),
                )
                if applied and xp_delta:
                    db.execute(
                        "UPDATE user_progress SET xp = xp + ?, updated_at = ? WHERE user_id = ?",
                        (xp_delta, now, int(user_id)),
                    )
                    self._record_ledger_entry(
                        db,
                        user_id,
                        resource="xp",
                        delta=xp_delta,
                        reason="campaign_reward",
                        reference_type="campaign_node",
                        reference_id=node_id,
                        metadata={"campaign_version": campaign_version, "idempotency_key": idempotency_key},
                        now=now,
                    )
                    self._record_economy_transaction(db, user_id, "CAMPAIGN_REWARD", xp_delta, "XP", node_id, now)
            state = match_state or {}
            is_campaign_win = bool(state.get("is_finished")) and state.get("winner") == "player"
            if is_campaign_win:
                if node_id == "node_10_gray_king":
                    unlocked.append("first_campaign_clear")
                if int((state.get("player") or {}).get("hp", -1) or -1) == int((state.get("player") or {}).get("max_hp", -2) or -2):
                    unlocked.append("no_damage_win")
                if node_id == "node_07_eclipse_parasite":
                    unlocked.append("shadow_slayer")
                if any(command.get("type") == "EVOLVE_DUPLICATE" for command in state.get("commands", [])):
                    unlocked.append("evolve_master")
                recent_campaign = db.execute(
                    """
                    SELECT winner, status
                    FROM match_history
                    WHERE user_id = ? AND campaign_node IS NOT NULL
                    ORDER BY updated_at DESC
                    LIMIT 3
                    """,
                    (int(user_id),),
                ).fetchall()
                if len(recent_campaign) == 3 and all(row["winner"] == "player" and row["status"] == "finished" for row in recent_campaign):
                    unlocked.append("3_win_streak")
                self._unlock_achievements(db, user_id, unlocked, now)
        return {
            "node_id": node_id,
            "campaign_version": campaign_version,
            "xp": xp_delta if applied else 0,
            "applied": applied,
            "idempotency_key": idempotency_key,
            "progress": self.get_campaign_progress(user_id, campaign_version),
            "achievements": self.achievements(user_id),
        }

    @_retry_postgres_serialization_write
    def record_clash_result(self, user_id, public_match_state):
        if not user_id:
            return None
        now = utc_now()
        is_finished = bool(public_match_state.get("is_finished"))
        winner = public_match_state.get("winner")
        win_delta = 1 if is_finished and winner == "player" else 0
        loss_delta = 1 if is_finished and winner == "bot" else 0
        # audit #7: o claim_key é único por clash (inclui state_hash+turn), então
        # 25 XP por clash × ~20 clashes/partida inflava a economia (nível 32 em
        # 10 partidas). O drip mid-clash cai pra 3; o grosso fica na conclusão.
        if is_finished:
            xp_delta = 25 + (75 if win_delta else 0) + (25 if loss_delta else 0)
        else:
            xp_delta = 3
        outcome = (public_match_state.get("result") or {}).get("outcome")
        claim_seed = ":".join(
            str(value or "")
            for value in (
                public_match_state.get("match_id"),
                public_match_state.get("state_hash"),
                public_match_state.get("turn"),
                outcome,
            )
        )
        claim_key = f"clash_{hashlib.sha256(claim_seed.encode('utf-8')).hexdigest()[:40]}"
        applied = False
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            claimed = self._claim_economy_idempotency(
                db,
                user_id,
                key=economy_idempotency_key("xp", user_id, "match_clash", claim_key),
                scope="XP",
                reference_id=public_match_state.get("match_id"),
                metadata={
                    "transaction_type": "MATCH_CLASH",
                    "reward_key": claim_key,
                    "state_hash": public_match_state.get("state_hash"),
                    "turn": public_match_state.get("turn"),
                    "outcome": outcome,
                },
                now=now,
            )
            reward_claimed = False
            if claimed:
                cursor = db.execute(
                    "INSERT OR IGNORE INTO reward_claims (user_id, reward_key, claimed_at) VALUES (?, ?, ?)",
                    (user_id, claim_key, now),
                )
                reward_claimed = bool(cursor.rowcount)
                if not reward_claimed:
                    self._record_audit_event(
                        db,
                        action="reward_claim_replay_rejected",
                        user_id=user_id,
                        metadata={"reward_key": claim_key, "reference_id": public_match_state.get("match_id")},
                        now=now,
                    )
            if claimed and reward_claimed:
                applied = True
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
                self._record_ledger_entry(
                    db,
                    user_id,
                    resource="xp",
                    delta=xp_delta,
                    reason="match_clash",
                    reference_type="match",
                    reference_id=public_match_state.get("match_id"),
                    metadata={
                        "winner": winner,
                        "is_finished": is_finished,
                        "turn": public_match_state.get("turn"),
                        "outcome": outcome,
                        "claim_key": claim_key,
                        "idempotency_key": economy_idempotency_key("xp", user_id, "match_clash", claim_key),
                    },
                    now=now,
                )
                self._record_economy_transaction(db, user_id, "MATCH_CLASH", xp_delta, "XP", public_match_state.get("match_id"), now)
                unlocked = ["first_clash"]
                if win_delta:
                    unlocked.append("first_win")
                self._unlock_achievements(db, user_id, unlocked, now)
        progress = self.progression(user_id)
        if progress is not None:
            progress["last_reward_applied"] = applied
            progress["last_reward_key"] = claim_key
        return progress

    @_retry_postgres_serialization_write
    def claim_daily_reward(self, user_id):
        progress = self.progression(user_id)
        if not progress or progress["clashes"] < 1:
            raise RebirthPersistenceError("Jogue pelo menos um clash antes de resgatar a recompensa diária.", "reward_locked", 409)
        reward_key = "daily_first_clash"
        now = utc_now()
        already_claimed = False
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            claimed = self._claim_economy_idempotency(
                db,
                user_id,
                key=economy_idempotency_key("xp", user_id, "daily_first_clash", reward_key),
                scope="XP",
                reference_id=reward_key,
                metadata={"transaction_type": "DAILY_FIRST_CLASH", "reward_key": reward_key},
                now=now,
            )
            reward_claimed = False
            if claimed:
                cursor = db.execute(
                    "INSERT OR IGNORE INTO reward_claims (user_id, reward_key, claimed_at) VALUES (?, ?, ?)",
                    (user_id, reward_key, now),
                )
                reward_claimed = bool(cursor.rowcount)
                if not reward_claimed:
                    self._record_audit_event(
                        db,
                        action="reward_claim_replay_rejected",
                        user_id=user_id,
                        metadata={"reward_key": reward_key, "reference_id": reward_key},
                        now=now,
                    )
            if not claimed or not reward_claimed:
                already_claimed = True
            else:
                db.execute(
                    "UPDATE user_progress SET xp = xp + 25, updated_at = ? WHERE user_id = ?",
                    (now, user_id),
                )
                self._record_ledger_entry(
                    db,
                    user_id,
                    resource="xp",
                    delta=25,
                    reason="daily_first_clash",
                    reference_type="reward",
                    reference_id=reward_key,
                    metadata={"reward_key": reward_key, "idempotency_key": economy_idempotency_key("xp", user_id, "daily_first_clash", reward_key)},
                    now=now,
                )
                self._unlock_achievements(db, user_id, ["daily_claimed"], now)
        if already_claimed:
            raise RebirthPersistenceError("A recompensa diária já foi resgatada.", "reward_already_claimed", 409)
        return {"reward_key": reward_key, "xp": 25, "progression": self.progression(user_id)}

    @_retry_postgres_serialization_write
    def complete_tutorial_step(self, user_id, step):
        step = max(1, min(4, int(step or 1)))
        now = utc_now()
        reward_key = f"tutorial_step_{step}"
        idempotency_key = economy_idempotency_key("xp", user_id, "tutorial_step", step)
        xp_delta = 60 if step >= 4 else 10
        applied = False
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT * FROM user_progress WHERE user_id = ?", (user_id,)).fetchone()
            if not current:
                raise RebirthPersistenceError("O progresso da conta não foi encontrado.", "missing_progress", 404)
            if bool(current["tutorial_complete"]) or int(current["tutorial_step"] or 0) >= step:
                self._record_audit_event(
                    db,
                    action="tutorial_reward_replay_rejected",
                    user_id=user_id,
                    metadata={
                        "reward_key": reward_key,
                        "requested_step": step,
                        "current_step": int(current["tutorial_step"] or 0),
                        "tutorial_complete": bool(current["tutorial_complete"]),
                    },
                    now=now,
                )
            elif self._claim_economy_idempotency(
                db,
                user_id,
                key=idempotency_key,
                scope="XP",
                reference_id=reward_key,
                metadata={"transaction_type": "TUTORIAL_REWARD", "reward_key": reward_key, "step": step},
                now=now,
            ):
                reward_cursor = db.execute(
                    "INSERT OR IGNORE INTO reward_claims (user_id, reward_key, claimed_at) VALUES (?, ?, ?)",
                    (user_id, reward_key, now),
                )
                if not reward_cursor.rowcount:
                    self._record_audit_event(
                        db,
                        action="reward_claim_replay_rejected",
                        user_id=user_id,
                        metadata={"reward_key": reward_key, "reference_id": reward_key},
                        now=now,
                    )
                else:
                    cursor = db.execute(
                        """
                        UPDATE user_progress
                        SET tutorial_step = MAX(tutorial_step, ?),
                            tutorial_complete = CASE WHEN ? >= 4 THEN 1 ELSE tutorial_complete END,
                            xp = xp + ?,
                            updated_at = ?
                        WHERE user_id = ?
                          AND tutorial_complete = 0
                          AND tutorial_step < ?
                        """,
                        (step, step, xp_delta, now, user_id, step),
                    )
                    if cursor.rowcount:
                        applied = True
                        self._record_ledger_entry(
                            db,
                            user_id,
                            resource="xp",
                            delta=xp_delta,
                            reason="tutorial_step",
                            reference_type="tutorial",
                            reference_id=str(step),
                            metadata={"step": step, "idempotency_key": idempotency_key},
                            now=now,
                        )
                        self._record_economy_transaction(
                            db,
                            user_id,
                            "TUTORIAL_REWARD",
                            xp_delta,
                            "XP",
                            reward_key,
                            now,
                        )
                        if step >= 4:
                            self._unlock_achievements(db, user_id, ["tutorial_complete"], now)
                    else:
                        self._record_audit_event(
                            db,
                            action="tutorial_reward_replay_rejected",
                            user_id=user_id,
                            metadata={"reward_key": reward_key, "requested_step": step, "lost_atomic_update": True},
                            now=now,
                        )
        return {"step": step, "xp": xp_delta if applied else 0, "progression": self.progression(user_id), "already_claimed": not applied}

    @_retry_postgres_serialization_write
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

    # Watermark de persistência por partida: eventos/comandos são append-only,
    # então cada upsert só precisa inserir o delta — antes, TODA ação reenviava
    # o histórico completo com INSERT OR IGNORE (O(n²) por partida).
    _MATCH_PERSIST_WATERMARKS = {}
    _MATCH_PERSIST_WATERMARK_LIMIT = 512

    @classmethod
    def _persist_watermark(cls, match_id):
        return cls._MATCH_PERSIST_WATERMARKS.get(str(match_id)) or {"events": 0, "commands": 0}

    @classmethod
    def _set_persist_watermark(cls, match_id, events_count, commands_count):
        marks = cls._MATCH_PERSIST_WATERMARKS
        if len(marks) >= cls._MATCH_PERSIST_WATERMARK_LIMIT:
            marks.pop(next(iter(marks)), None)
        marks[str(match_id)] = {"events": int(events_count), "commands": int(commands_count)}

    @_retry_postgres_serialization_write
    def upsert_match_history(self, user_id, match):
        if not user_id or not match:
            return None
        self.ensure_schema()
        from services.rebirth_domain import canonical_state_hash
        from services.rebirth_serializers import public_state

        now = utc_now()
        public = public_state(match)
        status = "finished" if match.get("is_finished") else "active"
        bot_profile = match.get("bot_profile") or {}
        watermark = self._persist_watermark(match.get("match_id"))
        all_commands = match.get("commands", [])
        all_events = match.get("events", [])
        new_commands = all_commands[watermark["commands"]:]
        new_events = all_events[watermark["events"]:]
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO match_history
                    (match_id, user_id, seed, bot_profile_id, status, winner, started_at, updated_at, final_state_hash, final_state_json, runtime_state_json, campaign_version, campaign_node, campaign_attempt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    status = excluded.status,
                    winner = excluded.winner,
                    updated_at = excluded.updated_at,
                    final_state_hash = excluded.final_state_hash,
                    final_state_json = excluded.final_state_json,
                    runtime_state_json = excluded.runtime_state_json,
                    campaign_version = excluded.campaign_version,
                    campaign_node = excluded.campaign_node,
                    campaign_attempt = excluded.campaign_attempt
                """,
                (
                    match["match_id"],
                    user_id,
                    match.get("seed"),
                    bot_profile.get("id"),
                    status,
                    match.get("winner"),
                    now,
                    now,
                    canonical_state_hash(match),
                    json.dumps(public, sort_keys=True),
                    json.dumps(match, sort_keys=True),
                    match.get("campaign_version"),
                    match.get("campaign_node"),
                    match.get("campaign_attempt"),
                ),
            )
            for command in new_commands:
                db.execute(
                    """
                    INSERT OR IGNORE INTO match_commands
                        (match_id, user_id, command_id, version, command_type, command_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        match["match_id"],
                        user_id,
                        int(command.get("id", 0) or 0),
                        int(command.get("version", 0) or 0),
                        command.get("type"),
                        json.dumps(command, sort_keys=True),
                        now,
                    ),
                )
            for event in new_events:
                db.execute(
                    """
                    INSERT OR IGNORE INTO match_events
                        (match_id, user_id, event_id, version, event_type, event_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        match["match_id"],
                        user_id,
                        int(event.get("id", 0) or 0),
                        int(event.get("version", 0) or 0),
                        event.get("type"),
                        json.dumps(event, sort_keys=True),
                        now,
                    ),
                )
        self._set_persist_watermark(match.get("match_id"), len(all_events), len(all_commands))
        # S3: aplica ELO se match terminou
        if match.get("is_finished"):
            try:
                self.apply_match_elo(user_id, match)
            except Exception:
                # ELO não pode quebrar o flow do match. Falha silenciosamente.
                pass
        return self.match_history(user_id, limit=1)[0]

    # === S3: ranking ELO ===
    BOT_ELO_BY_PROFILE = {
        "aggressive": 1450,
        "opportunist": 1500,
        "defensive": 1550,
    }
    ELO_K_FACTOR = 32

    def apply_match_elo(self, user_id, match):
        """Aplica delta de ELO ao usuário pós-match. Idempotente via match_id
        (tabela ledger). Retorna o novo ELO."""
        if not user_id or not match or not match.get("is_finished"):
            return None
        winner = match.get("winner")
        if winner not in ("player", "bot"):
            return None
        self.ensure_schema()
        match_id = match.get("match_id")
        bot_profile = match.get("bot_profile") or {}
        bot_profile_id = bot_profile.get("id") or "opportunist"
        bot_elo = self.BOT_ELO_BY_PROFILE.get(bot_profile_id, 1500)
        # Campaign bosses ganham ELO bumped (1500 + 50*node_order)
        node_id = match.get("campaign_node")
        if node_id:
            try:
                node_order = int(str(node_id).split("_")[-1])
                bot_elo = max(bot_elo, 1500 + 50 * node_order)
            except (ValueError, IndexError):
                pass
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT ranking_elo, ranking_season FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not current:
                db.execute("ROLLBACK")
                return None
            # Idempotência via reference_type+reference_id (economy_ledger
            # já tem essas colunas; evita aplicar ELO duas vezes pro mesmo match).
            already = db.execute(
                """
                SELECT 1 FROM economy_ledger
                WHERE user_id = ? AND resource = 'elo'
                  AND reference_type = 'match' AND reference_id = ?
                """,
                (user_id, match_id or ""),
            ).fetchone()
            if already:
                db.execute("ROLLBACK")
                return int(current["ranking_elo"] or 1500)
            current_elo = int(current["ranking_elo"] or 1500)
            score = 1.0 if winner == "player" else 0.0
            expected = 1.0 / (1.0 + 10 ** ((bot_elo - current_elo) / 400.0))
            delta = int(round(self.ELO_K_FACTOR * (score - expected)))
            new_elo = max(0, current_elo + delta)
            now = utc_now()
            db.execute(
                "UPDATE users SET ranking_elo = ? WHERE id = ?", (new_elo, user_id)
            )
            db.execute(
                """
                INSERT INTO economy_ledger
                    (user_id, resource, delta, balance_after, reason, reference_type, reference_id, metadata_json, created_at)
                VALUES (?, 'elo', ?, ?, ?, 'match', ?, ?, ?)
                """,
                (
                    user_id,
                    delta,
                    new_elo,
                    f"match_{winner}",
                    match_id or "",
                    json.dumps({"bot_elo": bot_elo, "expected": round(expected, 3), "score": score}),
                    now,
                ),
            )
            db.execute("COMMIT")
            return new_elo

    def get_user_ranking(self, user_id):
        """Retorna ELO atual + posição no leaderboard."""
        self.ensure_schema()
        with self.connect() as db:
            me = db.execute(
                "SELECT ranking_elo, ranking_season FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if not me:
                return {"elo": 1500, "season": 1, "position": None, "total": 0}
            my_elo = int(me["ranking_elo"] or 1500)
            higher = db.execute(
                "SELECT COUNT(*) AS n FROM users WHERE ranking_elo > ?",
                (my_elo,),
            ).fetchone()
            total = db.execute("SELECT COUNT(*) AS n FROM users").fetchone()
            return {
                "elo": my_elo,
                "season": int(me["ranking_season"] or 1),
                "position": int(higher["n"]) + 1,
                "total": int(total["n"]),
            }

    # === K3: Deck Builder — persistência de decks customizados ===
    DECK_SIZE_MIN = 30
    DECK_SIZE_MAX = 30
    DECK_MAX_COPIES = 3
    DECK_MAX_PER_USER = 10

    def _validate_deck_cards(self, cards):
        """Valida formato e regras: 30 cartas, max 3 cópias por card_id.

        Aceita cards como lista de strings (id) OU lista de {id, copies}.
        Normaliza pra dict {card_id: copies}."""
        if not isinstance(cards, (list, dict)):
            raise RebirthPersistenceError("Formato de deck inválido.", "deck_invalid_format", 400)
        # Normaliza pra dict {card_id: copies}
        counts = {}
        if isinstance(cards, dict):
            for cid, c in cards.items():
                counts[str(cid)] = int(c or 0)
        else:
            for entry in cards:
                if isinstance(entry, str):
                    counts[entry] = counts.get(entry, 0) + 1
                elif isinstance(entry, dict) and entry.get("id"):
                    counts[str(entry["id"])] = counts.get(str(entry["id"]), 0) + int(entry.get("copies", 1) or 1)
        # Regras
        total = sum(counts.values())
        if total != self.DECK_SIZE_MIN:
            raise RebirthPersistenceError(
                f"Deck precisa ter exatamente {self.DECK_SIZE_MIN} cartas (atual: {total}).",
                "deck_invalid_size", 400,
            )
        for cid, c in counts.items():
            if c < 1 or c > self.DECK_MAX_COPIES:
                raise RebirthPersistenceError(
                    f"Cada carta admite no máximo {self.DECK_MAX_COPIES} cópias ({cid}: {c}).",
                    "deck_invalid_copies", 400,
                )
        # Valida que IDs existem no catálogo
        from services.rebirth_cards import CARD_CATALOG
        valid_ids = {c.get("id") for c in CARD_CATALOG}
        for cid in counts:
            if cid not in valid_ids:
                raise RebirthPersistenceError(f"Carta inválida: {cid}", "deck_invalid_card", 400)
        return counts

    def list_decks(self, user_id):
        """Retorna todos os decks salvos do user."""
        self.ensure_schema()
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT id, name, cards_json, is_active, created_at, updated_at
                FROM user_decks
                WHERE user_id = ?
                ORDER BY is_active DESC, updated_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [
                {
                    "id": int(r["id"]),
                    "name": r["name"],
                    "cards": json.loads(r["cards_json"]),
                    "is_active": bool(r["is_active"]),
                    "created_at": str(r["created_at"]),
                    "updated_at": str(r["updated_at"]),
                }
                for r in rows
            ]

    def save_deck(self, user_id, name, cards, deck_id=None):
        """Cria ou atualiza um deck. Se deck_id passado, atualiza; senão cria."""
        name = (name or "").strip()
        if not name:
            raise RebirthPersistenceError("Nome do deck obrigatório.", "deck_invalid_name", 400)
        if len(name) > 80:
            name = name[:80]
        counts = self._validate_deck_cards(cards)
        cards_json = json.dumps(counts, sort_keys=True)
        now = utc_now()
        self.ensure_schema()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if deck_id is not None:
                exists = db.execute(
                    "SELECT 1 FROM user_decks WHERE id = ? AND user_id = ?",
                    (deck_id, user_id),
                ).fetchone()
                if not exists:
                    db.execute("ROLLBACK")
                    raise RebirthPersistenceError("Deck não encontrado.", "deck_not_found", 404)
                db.execute(
                    """
                    UPDATE user_decks SET name = ?, cards_json = ?, updated_at = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (name, cards_json, now, deck_id, user_id),
                )
                new_id = deck_id
            else:
                # Limite de decks por user
                count = db.execute(
                    "SELECT COUNT(*) AS n FROM user_decks WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                if int(count["n"]) >= self.DECK_MAX_PER_USER:
                    db.execute("ROLLBACK")
                    raise RebirthPersistenceError(
                        f"Limite de {self.DECK_MAX_PER_USER} decks por conta atingido.",
                        "deck_limit_reached", 409,
                    )
                cur = db.execute(
                    """
                    INSERT INTO user_decks (user_id, name, cards_json, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 0, ?, ?)
                    """,
                    (user_id, name, cards_json, now, now),
                )
                new_id = int(cur.lastrowid)
            db.execute("COMMIT")
        return {"id": new_id, "name": name, "cards": counts}

    def delete_deck(self, user_id, deck_id):
        self.ensure_schema()
        with self.connect() as db:
            cur = db.execute(
                "DELETE FROM user_decks WHERE id = ? AND user_id = ?",
                (deck_id, user_id),
            )
            if cur.rowcount == 0:
                raise RebirthPersistenceError("Deck não encontrado.", "deck_not_found", 404)
        return {"deleted": True, "id": deck_id}

    def set_active_deck(self, user_id, deck_id):
        """Marca um deck como ativo (desativa os demais do user)."""
        self.ensure_schema()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            target = db.execute(
                "SELECT 1 FROM user_decks WHERE id = ? AND user_id = ?",
                (deck_id, user_id),
            ).fetchone()
            if not target:
                db.execute("ROLLBACK")
                raise RebirthPersistenceError("Deck não encontrado.", "deck_not_found", 404)
            db.execute(
                "UPDATE user_decks SET is_active = 0 WHERE user_id = ? AND is_active = 1",
                (user_id,),
            )
            db.execute(
                "UPDATE user_decks SET is_active = 1, updated_at = ? WHERE id = ? AND user_id = ?",
                (utc_now(), deck_id, user_id),
            )
            db.execute("COMMIT")
        return {"active_deck_id": deck_id}

    # === S4: Stripe billing — crédito de gems via checkout ===
    BILLING_PACKAGES = {
        "gems_100": {"gems": 100, "price_cents": 990, "label": "100 Gemas"},
        "gems_550": {"gems": 550, "price_cents": 4990, "label": "550 Gemas"},
        "gems_1300": {"gems": 1300, "price_cents": 9990, "label": "1300 Gemas"},
    }

    def credit_billing_gems(self, user_id, package_id, stripe_session_id):
        """Credita gems do pacote Stripe ao usuário. Idempotente via stripe
        session_id (uma sessão = um crédito). Chamado pelo webhook."""
        if not user_id or not stripe_session_id:
            return None
        pkg = self.BILLING_PACKAGES.get(package_id)
        if not pkg:
            raise RebirthPersistenceError(
                f"Pacote desconhecido: {package_id}", "billing_invalid_package", 400
            )
        self.ensure_schema()
        amount = int(pkg["gems"])
        now = utc_now()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            already = db.execute(
                """
                SELECT 1 FROM economy_ledger
                WHERE user_id = ? AND resource = 'coinz'
                  AND reference_type = 'stripe' AND reference_id = ?
                """,
                (user_id, stripe_session_id),
            ).fetchone()
            if already:
                db.execute("ROLLBACK")
                return {"credited": False, "reason": "already_processed"}
            self._record_wallet_entry(
                db,
                user_id,
                currency="COINZ",
                entry_type="CREDIT",
                amount=amount,
                source="BILLING",
                reference_id=stripe_session_id,
                now=now,
            )
            self._record_ledger_entry(
                db,
                user_id,
                resource="coinz",
                delta=amount,
                reason=f"stripe_purchase_{package_id}",
                reference_type="stripe",
                reference_id=stripe_session_id,
                metadata={"package_id": package_id, "gems": amount, "price_cents": pkg["price_cents"]},
                now=now,
            )
            db.execute("COMMIT")
            return {"credited": True, "gems": amount, "package_id": package_id}

    def get_ranking_top(self, limit=20):
        """Top N jogadores por ELO."""
        self.ensure_schema()
        limit = max(1, min(int(limit or 20), 100))
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT username, ranking_elo, ranking_season
                FROM users
                ORDER BY ranking_elo DESC, username ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                {
                    "rank": i + 1,
                    "username": r["username"],
                    "elo": int(r["ranking_elo"] or 1500),
                    "season": int(r["ranking_season"] or 1),
                }
                for i, r in enumerate(rows)
            ]

    def match_history(self, user_id, limit=10):
        self.ensure_schema()
        limit = max(1, min(int(limit or 10), 50))
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT match_id, seed, bot_profile_id, status, winner, started_at, updated_at, final_state_hash, final_state_json,
                       campaign_version, campaign_node, campaign_attempt
                FROM match_history
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            history = []
            for row in rows:
                command_count = db.execute(
                    "SELECT COUNT(*) AS amount FROM match_commands WHERE match_id = ?",
                    (row["match_id"],),
                ).fetchone()["amount"]
                event_count = db.execute(
                    "SELECT COUNT(*) AS amount FROM match_events WHERE match_id = ?",
                    (row["match_id"],),
                ).fetchone()["amount"]
                history.append(
                    {
                        "match_id": row["match_id"],
                        "seed": row["seed"],
                        "bot_profile_id": row["bot_profile_id"],
                        "status": row["status"],
                        "winner": row["winner"],
                        "started_at": row["started_at"],
                        "updated_at": row["updated_at"],
                        "state_hash": row["final_state_hash"],
                        "campaign_version": row["campaign_version"],
                        "campaign_node": row["campaign_node"],
                        "campaign_attempt": row["campaign_attempt"],
                        "command_count": int(command_count),
                        "event_count": int(event_count),
                        "state": json.loads(row["final_state_json"]),
                    }
                )
        return history

    def match_events(self, user_id, match_id, limit=50):
        self.ensure_schema()
        limit = max(1, min(int(limit or 50), 200))
        with self.connect() as db:
            owner = db.execute(
                "SELECT 1 FROM match_history WHERE user_id = ? AND match_id = ?",
                (user_id, match_id),
            ).fetchone()
            if not owner:
                raise RebirthPersistenceError("Histórico da partida não encontrado.", "missing_match", status=404)
            rows = db.execute(
                """
                SELECT event_json
                FROM match_events
                WHERE match_id = ?
                ORDER BY event_id ASC
                LIMIT ?
                """,
                (match_id, limit),
            ).fetchall()
        return [json.loads(row["event_json"]) for row in rows]

    def match_state(self, user_id, match_id):
        self.ensure_schema()
        with self.connect() as db:
            row = db.execute(
                "SELECT final_state_json FROM match_history WHERE user_id = ? AND match_id = ?",
                (user_id, match_id),
            ).fetchone()
        if not row:
            raise RebirthPersistenceError("Historico da partida nao encontrado.", "missing_match", status=404)
        return json.loads(row["final_state_json"])

    def runtime_match_state(self, user_id, match_id):
        self.ensure_schema()
        with self.connect() as db:
            row = db.execute(
                "SELECT runtime_state_json FROM match_history WHERE user_id = ? AND match_id = ?",
                (user_id, match_id),
            ).fetchone()
        if not row:
            raise RebirthPersistenceError("Historico da partida nao encontrado.", "missing_match", status=404)
        return json.loads(row["runtime_state_json"])

    def economy_ledger(self, user_id, limit=30):
        self.ensure_schema()
        limit = max(1, min(int(limit or 30), 100))
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT resource, delta, reason, reference_type, reference_id, balance_after, metadata_json, created_at
                FROM economy_ledger
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [
            {
                "resource": row["resource"],
                "delta": int(row["delta"]),
                "reason": row["reason"],
                "reference_type": row["reference_type"],
                "reference_id": row["reference_id"],
                "balance_after": int(row["balance_after"]),
                "metadata": json.loads(row["metadata_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def support_export(self, user_id):
        return {
            "user": self.get_user(user_id),
            "progression": self.progression(user_id),
            "wallet": self.wallet_payload(user_id),
            "collection": dict(self.collection_counts(user_id)),
            "loadout": self.loadout_card_ids(user_id),
            "achievements": self.achievements(user_id),
            "boosters": self.booster_history(user_id, limit=20),
            "matches": self.match_history(user_id, limit=20),
            "ledger": self.economy_ledger(user_id, limit=50),
            "campaign": self.get_campaign_progress(user_id),
        }

    @_retry_postgres_serialization_write
    def delete_account(self, user_id):
        self.ensure_schema()
        user_id = int(user_id)
        now = utc_now()
        with self.connect() as db:
            user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                raise RebirthPersistenceError("A conta Rebirth nao foi encontrada.", "missing_user", 404)
            counts = {
                "matches": int(db.execute("SELECT COUNT(*) AS count FROM match_history WHERE user_id = ?", (user_id,)).fetchone()["count"] or 0),
                "ledger_entries": int(db.execute("SELECT COUNT(*) AS count FROM economy_ledger WHERE user_id = ?", (user_id,)).fetchone()["count"] or 0),
                "collection_rows": int(db.execute("SELECT COUNT(*) AS count FROM user_collection WHERE user_id = ?", (user_id,)).fetchone()["count"] or 0),
                "boosters": int(db.execute("SELECT COUNT(*) AS count FROM booster_history WHERE user_id = ?", (user_id,)).fetchone()["count"] or 0),
                "decks": int(db.execute("SELECT COUNT(*) AS count FROM user_decks WHERE user_id = ?", (user_id,)).fetchone()["count"] or 0),
            }
            db.execute(
                """
                INSERT INTO admin_audit_log (actor, action, user_id, metadata_json, created_at)
                VALUES (?, ?, NULL, ?, ?)
                """,
                (
                    "self-service",
                    "account_deleted",
                    json.dumps({"deleted_user_id": user_id, "counts": counts}, sort_keys=True),
                    now,
                ),
            )
            db.execute("UPDATE telemetry_events SET user_id = NULL WHERE user_id = ?", (user_id,))
            db.execute("UPDATE admin_audit_log SET user_id = NULL WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM market_offers WHERE seller_id = ?", (user_id,))
            db.execute("DELETE FROM match_events WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM match_commands WHERE user_id = ?", (user_id,))
            for table in (
                "user_decks",
                "user_campaign_progress",
                "reward_claims",
                "booster_history",
                "user_achievements",
                "economy_ledger",
                "economy_transactions",
                "economy_idempotency_keys",
                "wallet_ledger",
                "user_collection",
                "user_loadout",
                "user_progress",
                "user_sessions",
                "match_history",
            ):
                db.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return {"deleted": True, "deleted_user_id": user_id, "deleted_at": now, "counts": counts}

    @_retry_postgres_serialization_write
    def reset_account(self, user_id):
        self.ensure_schema()
        now = utc_now()
        with self.connect() as db:
            progress = db.execute("SELECT xp FROM user_progress WHERE user_id = ?", (user_id,)).fetchone()
            xp = int(progress["xp"] or 0) if progress else 0
            if xp:
                self._record_ledger_entry(
                    db,
                    user_id,
                    resource="xp",
                    delta=-xp,
                    reason="account_reset_compensation",
                    reference_type="account_reset",
                    reference_id=str(user_id),
                    metadata={"previous_balance": xp},
                    now=now,
                )
                self._record_economy_transaction(db, user_id, "ACCOUNT_RESET", -xp, "XP", f"reset:{user_id}:{now}", now)
            for currency in ("GOLD", "COINZ"):
                balance = self._currency_balance(db, user_id, currency)
                if balance > 0:
                    self._record_wallet_entry(
                        db,
                        user_id,
                        currency=currency,
                        entry_type="DEBIT",
                        amount=balance,
                        source="ACCOUNT_RESET",
                        reference_id=f"reset:{user_id}:{now}",
                        now=now,
                    )
                    self._record_ledger_entry(
                        db,
                        user_id,
                        resource=currency.lower(),
                        delta=-balance,
                        reason="account_reset_compensation",
                        reference_type="account_reset",
                        reference_id=str(user_id),
                        metadata={"currency": currency, "previous_balance": balance},
                        now=now,
                    )
                    self._record_economy_transaction(db, user_id, "ACCOUNT_RESET", -balance, currency, f"reset:{user_id}:{now}", now)
            cards = db.execute("SELECT card_id, copies FROM user_collection WHERE user_id = ?", (user_id,)).fetchall()
            for card in cards:
                copies = int(card["copies"] or 0)
                if copies:
                    self._record_ledger_entry(
                        db,
                        user_id,
                        resource=f"card:{card['card_id']}",
                        delta=-copies,
                        reason="account_reset_compensation",
                        reference_type="account_reset",
                        reference_id=str(user_id),
                        metadata={"card_id": card["card_id"], "copies": copies},
                        now=now,
                    )
            db.execute("UPDATE market_offers SET status = 'CANCELLED' WHERE seller_id = ? AND status = 'ACTIVE'", (user_id,))
            db.execute("DELETE FROM user_collection WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM user_loadout WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))
            self._seed_user_state(db, user_id, now)
        return self.support_export(user_id)

    @_retry_postgres_serialization_write
    def admin_grant(self, actor, user_id, *, resource, amount=1, card_id=None, reason="admin_grant", idempotency_key=None):
        self.ensure_schema()
        now = utc_now()
        amount = int(amount or 1)
        resource = str(resource or "").strip()
        supplied_idempotency_key = str(idempotency_key or "").strip()
        admin_replay = False
        with self.connect() as db:
            user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                raise RebirthPersistenceError("O jogador Rebirth de destino não foi encontrado.", "missing_user", 404)
            if resource == "xp":
                if supplied_idempotency_key and not self._claim_economy_idempotency(
                    db,
                    user_id,
                    key=economy_idempotency_key("xp", user_id, "admin_grant", supplied_idempotency_key),
                    scope="XP",
                    reference_id=str(actor),
                    metadata={"actor": actor, "amount": amount, "reason": reason},
                    now=now,
                ):
                    admin_replay = True
                else:
                    db.execute(
                        "UPDATE user_progress SET xp = xp + ?, updated_at = ? WHERE user_id = ?",
                        (amount, now, user_id),
                    )
                    self._record_ledger_entry(
                        db,
                        user_id,
                        resource="xp",
                        delta=amount,
                        reason=reason,
                        reference_type="admin",
                        reference_id=str(actor),
                        metadata={"actor": actor, "idempotency_key": supplied_idempotency_key},
                        now=now,
                    )
            elif resource.upper() in {"GOLD", "COINZ", "COINS", "PREMIUM", "GEMS"}:
                currency = normalize_wallet_currency(resource)
                if currency == "COINZ" and supplied_idempotency_key and not self._claim_economy_idempotency(
                    db,
                    user_id,
                    key=economy_idempotency_key("coinz", user_id, "admin_grant", supplied_idempotency_key),
                    scope="COINZ",
                    reference_id=str(actor),
                    metadata={"actor": actor, "amount": amount, "reason": reason, "currency": currency},
                    now=now,
                ):
                    admin_replay = True
                else:
                    self._record_wallet_entry(
                        db,
                        user_id,
                        currency=currency,
                        entry_type="CREDIT" if amount >= 0 else "DEBIT",
                        amount=abs(amount),
                        source="MATCH_REWARD",
                        reference_id=str(actor),
                        now=now,
                    )
                    self._record_ledger_entry(
                        db,
                        user_id,
                        resource=currency.lower(),
                        delta=amount,
                        reason=reason,
                        reference_type="admin",
                        reference_id=str(actor),
                        metadata={"actor": actor, "currency": currency, "idempotency_key": supplied_idempotency_key},
                        now=now,
                    )
            elif resource == "card":
                card = get_card(card_id)
                db.execute(
                    """
                    INSERT INTO user_collection (user_id, card_id, copies, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, card_id) DO UPDATE SET
                        copies = user_collection.copies + excluded.copies,
                        updated_at = excluded.updated_at
                    """,
                    (user_id, card["id"], amount, now),
                )
                self._record_ledger_entry(
                    db,
                    user_id,
                    resource=f"card:{card['id']}",
                    delta=amount,
                    reason=reason,
                    reference_type="admin",
                    reference_id=str(actor),
                    metadata={"actor": actor, "card_id": card["id"], "name": card["name"]},
                    now=now,
                )
            else:
                raise RebirthPersistenceError("A concessão administrativa aceita xp, card, GOLD ou COINZ.", "invalid_admin_grant", 400)
            if not admin_replay:
                db.execute(
                    """
                    INSERT INTO admin_audit_log (actor, action, user_id, metadata_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(actor),
                        "grant",
                        user_id,
                        json.dumps(
                            {
                                "resource": resource,
                                "amount": amount,
                                "card_id": card_id,
                                "reason": reason,
                                "idempotency_key": supplied_idempotency_key,
                            },
                            sort_keys=True,
                        ),
                        now,
                    ),
                )
        if admin_replay:
            raise RebirthPersistenceError("Esta transação administrativa já foi liquidada.", "transaction_replayed", 409)
        return self.support_export(user_id)
