"""Versioned PostgreSQL schema management for the active Rebirth runtime."""

from __future__ import annotations

import argparse
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError


SCHEMA_VERSION = 12
SCHEMA_MIGRATION_LOCK_KEY = 735194302771
REQUIRED_TABLES = {
    "rebirth_schema_migrations",
    "users",
    "user_sessions",
    "user_collection",
    "crafting_dust",
    "user_loadout",
    "user_progress",
    "reward_claims",
    "booster_history",
    "user_achievements",
    "match_history",
    "match_commands",
    "match_events",
    "economy_ledger",
    "economy_transactions",
    "economy_idempotency_keys",
    "wallet_ledger",
    "admin_audit_log",
    "market_offers",
    "telemetry_events",
    "user_campaign_progress",
}
REQUIRED_COLUMNS = {
    "match_history": {"campaign_version", "campaign_node", "campaign_attempt"},
    "users": {
        "email_verified", "verification_token", "verification_sent_at", "email_verified_at",
        "ranking_elo", "ranking_season",
    },
}

# Executado antes da foundation migration: tabelas Ascension com nomes
# conflitantes precisam sair do caminho antes que novas FKs sejam declaradas.
LEGACY_SCHEMA_PREFLIGHT = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'users')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'users' AND column_name = 'password_salt')
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'users_legacy_ascension') THEN
        EXECUTE 'ALTER TABLE users RENAME TO users_legacy_ascension';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'match_history')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'match_history' AND column_name = 'match_id')
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'match_history_legacy_ascension') THEN
        EXECUTE 'ALTER TABLE match_history RENAME TO match_history_legacy_ascension';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'booster_history')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'booster_history' AND column_name = 'booster_id')
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'booster_history_legacy_ascension') THEN
        EXECUTE 'ALTER TABLE booster_history RENAME TO booster_history_legacy_ascension';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'economy_ledger')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'economy_ledger' AND column_name = 'resource')
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'economy_ledger_legacy_ascension') THEN
        EXECUTE 'ALTER TABLE economy_ledger RENAME TO economy_ledger_legacy_ascension';
    END IF;
END $$;
"""

MIGRATION_001 = """
CREATE TABLE IF NOT EXISTS rebirth_schema_migrations (
    version INTEGER PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_salt VARCHAR(64) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS user_collection (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    card_id VARCHAR(80) NOT NULL,
    copies INTEGER NOT NULL DEFAULT 0 CHECK (copies >= 0),
    locked_copies INTEGER NOT NULL DEFAULT 0 CHECK (locked_copies >= 0 AND locked_copies <= copies),
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, card_id)
);

CREATE TABLE IF NOT EXISTS user_loadout (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    slot INTEGER NOT NULL CHECK (slot BETWEEN 1 AND 30),
    card_id VARCHAR(80) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, slot)
);

CREATE TABLE IF NOT EXISTS user_progress (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    xp INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0),
    wins INTEGER NOT NULL DEFAULT 0 CHECK (wins >= 0),
    losses INTEGER NOT NULL DEFAULT 0 CHECK (losses >= 0),
    clashes INTEGER NOT NULL DEFAULT 0 CHECK (clashes >= 0),
    boosters_opened INTEGER NOT NULL DEFAULT 0 CHECK (boosters_opened >= 0),
    tutorial_step INTEGER NOT NULL DEFAULT 0 CHECK (tutorial_step BETWEEN 0 AND 4),
    tutorial_complete INTEGER NOT NULL DEFAULT 0 CHECK (tutorial_complete IN (0, 1)),
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_claims (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reward_key VARCHAR(100) NOT NULL,
    claimed_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, reward_key)
);

CREATE TABLE IF NOT EXISTS booster_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    booster_id VARCHAR(100) NOT NULL,
    seed VARCHAR(255) NOT NULL,
    cards_json TEXT NOT NULL,
    opened_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS user_achievements (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_key VARCHAR(100) NOT NULL,
    unlocked_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, achievement_key)
);

CREATE TABLE IF NOT EXISTS match_history (
    match_id VARCHAR(96) PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    seed VARCHAR(255),
    bot_profile_id VARCHAR(64),
    status VARCHAR(20) NOT NULL,
    winner VARCHAR(20),
    started_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    final_state_hash VARCHAR(128),
    final_state_json TEXT NOT NULL,
    runtime_state_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS match_commands (
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(96) NOT NULL REFERENCES match_history(match_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    command_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    command_type VARCHAR(60) NOT NULL,
    command_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (match_id, command_id)
);

CREATE TABLE IF NOT EXISTS match_events (
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(96) NOT NULL REFERENCES match_history(match_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    event_type VARCHAR(60) NOT NULL,
    event_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (match_id, event_id)
);

CREATE TABLE IF NOT EXISTS economy_ledger (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    resource VARCHAR(120) NOT NULL,
    delta INTEGER NOT NULL,
    reason VARCHAR(80) NOT NULL,
    reference_type VARCHAR(60),
    reference_id VARCHAR(128),
    balance_after INTEGER NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS economy_transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    transaction_type VARCHAR(60) NOT NULL,
    amount INTEGER NOT NULL,
    currency VARCHAR(24) NOT NULL,
    reference_id VARCHAR(128),
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS economy_idempotency_keys (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    idempotency_key VARCHAR(160) NOT NULL,
    scope VARCHAR(40) NOT NULL,
    reference_id VARCHAR(128),
    settled_at TIMESTAMPTZ NOT NULL,
    metadata_json TEXT NOT NULL,
    PRIMARY KEY (user_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS wallet_ledger (
    id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    currency VARCHAR(12) NOT NULL CHECK (currency IN ('GOLD', 'COINZ')),
    entry_type VARCHAR(8) NOT NULL CHECK (entry_type IN ('CREDIT', 'DEBIT')),
    amount INTEGER NOT NULL CHECK (amount > 0),
    source VARCHAR(40) NOT NULL,
    reference_id VARCHAR(128) NOT NULL DEFAULT '',
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_audit_log (
    id BIGSERIAL PRIMARY KEY,
    actor VARCHAR(100) NOT NULL,
    action VARCHAR(60) NOT NULL,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    metadata_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS market_offers (
    id UUID PRIMARY KEY,
    seller_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    card_id VARCHAR(80) NOT NULL,
    price INTEGER NOT NULL CHECK (price > 0),
    currency_type VARCHAR(16) NOT NULL CHECK (currency_type = 'GOLD'),
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS telemetry_events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(80) NOT NULL,
    event_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(token_hash, revoked_at);
CREATE INDEX IF NOT EXISTS idx_market_offers_status_created ON market_offers(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_market_offers_seller_status ON market_offers(seller_id, status);
CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user_currency ON wallet_ledger(user_id, currency, timestamp);
CREATE INDEX IF NOT EXISTS idx_wallet_ledger_reference ON wallet_ledger(reference_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_purchase_reference_once
    ON economy_transactions(user_id, transaction_type, reference_id)
    WHERE transaction_type = 'IN_APP_PURCHASE' AND reference_id IS NOT NULL AND reference_id <> '';

INSERT INTO rebirth_schema_migrations(version, name)
VALUES (1, 'single_source_postgresql_foundation')
ON CONFLICT (version) DO NOTHING;
"""

MIGRATION_002 = """
ALTER TABLE match_history ADD COLUMN IF NOT EXISTS runtime_state_json TEXT;
UPDATE match_history
SET runtime_state_json = final_state_json
WHERE runtime_state_json IS NULL;
ALTER TABLE match_history ALTER COLUMN runtime_state_json SET NOT NULL;

INSERT INTO rebirth_schema_migrations(version, name)
VALUES (2, 'persist_authoritative_runtime_match_state')
ON CONFLICT (version) DO NOTHING;
"""

MIGRATION_003 = """
CREATE TABLE IF NOT EXISTS economy_idempotency_keys (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    idempotency_key VARCHAR(160) NOT NULL,
    scope VARCHAR(40) NOT NULL,
    reference_id VARCHAR(128),
    settled_at TIMESTAMPTZ NOT NULL,
    metadata_json TEXT NOT NULL,
    PRIMARY KEY (user_id, idempotency_key)
);

INSERT INTO rebirth_schema_migrations(version, name)
VALUES (3, 'economy_idempotency_replay_audit')
ON CONFLICT (version) DO NOTHING;
"""

MIGRATION_004 = """
-- v70: auto-rename Ascension-legacy tables que estavam mascarando o schema
-- Rebirth (users sem password_salt, match_history com player1_id/player2_id,
-- booster_history sem booster_id, economy_ledger com currency/amount).
-- CREATE TABLE IF NOT EXISTS é no-op contra tabelas pré-existentes com
-- schema diferente, então signup quebrava em produção com IntegrityError
-- mascarado. Este DO block detecta o schema antigo via information_schema
-- e renomeia condicionalmente — idempotente em ambientes novos.

DO $$
BEGIN
    -- users: sem password_salt é o sinal canônico de schema Ascension legacy.
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'users')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'users' AND column_name = 'password_salt')
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'users_legacy_ascension') THEN
        EXECUTE 'ALTER TABLE users RENAME TO users_legacy_ascension';
    END IF;

    -- match_history: sem match_id (VARCHAR PRIMARY KEY) é Ascension PvP.
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'match_history')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'match_history' AND column_name = 'match_id')
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'match_history_legacy_ascension') THEN
        EXECUTE 'ALTER TABLE match_history RENAME TO match_history_legacy_ascension';
    END IF;

    -- booster_history: sem booster_id é Ascension shop.
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'booster_history')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'booster_history' AND column_name = 'booster_id')
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'booster_history_legacy_ascension') THEN
        EXECUTE 'ALTER TABLE booster_history RENAME TO booster_history_legacy_ascension';
    END IF;

    -- economy_ledger: sem resource (mas com currency/amount) é Ascension wallet.
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'economy_ledger')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'economy_ledger' AND column_name = 'resource')
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'economy_ledger_legacy_ascension') THEN
        EXECUTE 'ALTER TABLE economy_ledger RENAME TO economy_ledger_legacy_ascension';
    END IF;
END $$;

-- Recria as 4 tabelas com schema Rebirth (no-op se já existem corretas).
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_salt VARCHAR(64) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS match_history (
    match_id VARCHAR(96) PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    seed VARCHAR(255),
    bot_profile_id VARCHAR(64),
    status VARCHAR(20) NOT NULL,
    winner VARCHAR(20),
    started_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    final_state_hash VARCHAR(128),
    final_state_json TEXT NOT NULL,
    runtime_state_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS booster_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    booster_id VARCHAR(100) NOT NULL,
    seed VARCHAR(255) NOT NULL,
    cards_json TEXT NOT NULL,
    opened_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS economy_ledger (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    resource VARCHAR(120) NOT NULL,
    delta INTEGER NOT NULL,
    reason VARCHAR(80) NOT NULL,
    reference_type VARCHAR(60),
    reference_id VARCHAR(128),
    balance_after INTEGER NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

INSERT INTO rebirth_schema_migrations(version, name)
VALUES (4, 'auto_rename_ascension_legacy_tables')
ON CONFLICT (version) DO NOTHING;
"""

MIGRATION_005 = """
-- v70: reaponta FKs órfãs que seguiram o RENAME de parents legacy.
-- Quando ALTER TABLE users RENAME aconteceu (v69/v70 manual), Postgres atualizou
-- automaticamente TODAS as FKs apontando pra users — incluindo user_collection,
-- user_loadout, user_progress, match_commands, wallet_ledger etc. Logo o schema
-- novo de users existe mas é orphan, e qualquer INSERT em tabela filha referencia
-- a tabela legacy. match_commands/match_events também podem seguir um rename de
-- match_history. Mantemos linhas históricas legadas sem bloquearem novos writes
-- usando NOT VALID; inserts novos já são validados contra o parent Rebirth.

DO $$
DECLARE
    fk RECORD;
BEGIN
    -- Impede colisão entre IDs novos e registros antigos que permanecem nas
    -- tabelas compartilhadas até sua eventual arquivação.
    IF to_regclass(current_schema() || '.users_legacy_ascension') IS NOT NULL THEN
        PERFORM setval(
            pg_get_serial_sequence('users', 'id'),
            GREATEST(
                COALESCE((SELECT MAX(id) FROM users), 0),
                COALESCE((SELECT MAX(id) FROM users_legacy_ascension), 0)
            ) + 1,
            false
        );
    END IF;

    FOR fk IN
        SELECT
            con.conname AS constraint_name,
            cls_src.relname AS source_table,
            cls_tgt.relname AS target_table,
            pg_get_constraintdef(con.oid) AS constraint_def,
            CASE cls_tgt.relname
                WHEN 'users_legacy_ascension' THEN 'users'
                WHEN 'match_history_legacy_ascension' THEN 'match_history'
            END AS replacement_table
        FROM pg_constraint con
        JOIN pg_class cls_src ON con.conrelid = cls_src.oid
        JOIN pg_class cls_tgt ON con.confrelid = cls_tgt.oid
        WHERE con.contype = 'f'
          AND cls_tgt.relname IN ('users_legacy_ascension', 'match_history_legacy_ascension')
          AND cls_src.relname NOT LIKE '%%_legacy_ascension'
          AND cls_src.relname IN (
              'user_sessions', 'user_collection', 'user_loadout', 'user_progress',
              'reward_claims', 'booster_history', 'user_achievements', 'match_history',
              'match_commands', 'match_events', 'economy_ledger', 'economy_transactions',
              'economy_idempotency_keys', 'wallet_ledger', 'admin_audit_log',
              'market_offers', 'telemetry_events'
          )
    LOOP
        EXECUTE format(
            'ALTER TABLE %%I DROP CONSTRAINT %%I',
            fk.source_table, fk.constraint_name
        );
        EXECUTE format(
            'ALTER TABLE %%I ADD CONSTRAINT %%I %%s NOT VALID',
            fk.source_table,
            fk.constraint_name,
            replace(fk.constraint_def, fk.target_table, fk.replacement_table)
        );
        RAISE NOTICE 'Reaponted FK %% on %% from %% to %% without validating legacy rows',
            fk.constraint_name, fk.source_table, fk.target_table, fk.replacement_table;
    END LOOP;
END $$;

INSERT INTO rebirth_schema_migrations(version, name)
VALUES (5, 'repoint_orphan_fks_after_users_rename')
ON CONFLICT (version) DO NOTHING;
"""

MIGRATION_006 = """
INSERT INTO rebirth_schema_migrations(version, name)
VALUES (6, 'legacy_parent_fk_recovery_and_identity_fence')
ON CONFLICT (version) DO NOTHING;
"""

MIGRATION_007 = """
CREATE INDEX IF NOT EXISTS idx_telemetry_type_created
    ON telemetry_events(event_type, created_at DESC);

INSERT INTO rebirth_schema_migrations(version, name)
VALUES (7, 'product_telemetry_query_index')
ON CONFLICT (version) DO NOTHING;
"""

MIGRATION_008 = """
CREATE TABLE IF NOT EXISTS user_campaign_progress (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    campaign_version VARCHAR(64) NOT NULL,
    node_id VARCHAR(48) NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    completed_at TIMESTAMPTZ,
    reward_claimed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, campaign_version, node_id)
);

ALTER TABLE match_history ADD COLUMN IF NOT EXISTS campaign_version VARCHAR(64);
ALTER TABLE match_history ADD COLUMN IF NOT EXISTS campaign_node VARCHAR(48);
ALTER TABLE match_history ADD COLUMN IF NOT EXISTS campaign_attempt INTEGER;

CREATE INDEX IF NOT EXISTS idx_match_history_campaign
    ON match_history(user_id, campaign_version, campaign_node)
    WHERE campaign_node IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_user_campaign_progress_nodes
    ON user_campaign_progress(user_id, campaign_version, node_id);

INSERT INTO rebirth_schema_migrations(version, name)
VALUES (8, 'single_player_campaign_v1_progress')
ON CONFLICT (version) DO NOTHING;
"""

MIGRATION_009 = """
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_sent_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_users_verification_token
    ON users(verification_token)
    WHERE verification_token IS NOT NULL;

INSERT INTO rebirth_schema_migrations(version, name)
VALUES (9, 'email_verification')
ON CONFLICT (version) DO NOTHING;
"""

MIGRATION_010 = """
ALTER TABLE users ADD COLUMN IF NOT EXISTS ranking_elo INTEGER NOT NULL DEFAULT 1500;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ranking_season INTEGER NOT NULL DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_users_ranking_elo
    ON users(ranking_elo DESC);

INSERT INTO rebirth_schema_migrations(version, name)
VALUES (10, 'ranking_elo')
ON CONFLICT (version) DO NOTHING;
"""

MIGRATION_011 = """
CREATE TABLE IF NOT EXISTS user_decks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(80) NOT NULL,
    cards_json TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_decks_user
    ON user_decks(user_id, updated_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_decks_active
    ON user_decks(user_id)
    WHERE is_active = TRUE;

INSERT INTO rebirth_schema_migrations(version, name)
VALUES (11, 'user_decks')
ON CONFLICT (version) DO NOTHING;
"""

MIGRATION_012 = """
CREATE TABLE IF NOT EXISTS crafting_dust (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL DEFAULT 0 CHECK (amount >= 0),
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id)
);

INSERT INTO rebirth_schema_migrations(version, name)
VALUES (12, 'crafting_dust')
ON CONFLICT (version) DO NOTHING;
"""

MIGRATIONS = (
    MIGRATION_001,
    MIGRATION_002,
    MIGRATION_003,
    MIGRATION_004,
    MIGRATION_005,
    MIGRATION_006,
    MIGRATION_007,
    MIGRATION_008,
    MIGRATION_009,
    MIGRATION_010,
    MIGRATION_011,
    MIGRATION_012,
)


def normalize_database_url(database_url: str) -> str:
    value = str(database_url or "").strip()
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql+asyncpg://"):
        return value.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


def make_engine(database_url: str):
    normalized = normalize_database_url(database_url)
    if not normalized.startswith("postgresql+psycopg://"):
        raise RuntimeError("REBIRTH_DATABASE_URL deve apontar para PostgreSQL em producao.")
    return create_engine(normalized, pool_pre_ping=True, future=True)


def upgrade_schema(database_url: str) -> None:
    """Executa todas as migrations. Cada migration é um bloco multi-statement
    enviado diretamente ao driver (psycopg), preservando DO $$..$$ blocks e
    qualquer string literal com ';' interno — coisa que str.split(';') quebra.
    """
    engine = make_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": SCHEMA_MIGRATION_LOCK_KEY})
            connection.exec_driver_sql(LEGACY_SCHEMA_PREFLIGHT.strip())
            for migration in MIGRATIONS:
                migration_text = migration.strip()
                if not migration_text:
                    continue
                connection.exec_driver_sql(migration_text)
    finally:
        engine.dispose()


def validate_schema(engine) -> dict:
    try:
        tables = set(inspect(engine).get_table_names())
        missing = sorted(REQUIRED_TABLES - tables)
        if missing:
            return {"ok": False, "version": 0, "missing_tables": missing, "missing_columns": []}
        missing_columns = []
        for table_name, expected in REQUIRED_COLUMNS.items():
            columns = {column["name"] for column in inspect(engine).get_columns(table_name)}
            missing_columns.extend(
                f"{table_name}.{column_name}"
                for column_name in sorted(expected - columns)
            )
        with engine.connect() as connection:
            version = connection.execute(text("SELECT COALESCE(MAX(version), 0) FROM rebirth_schema_migrations")).scalar_one()
            connection.execute(text("SELECT 1"))
        return {
            "ok": int(version or 0) >= SCHEMA_VERSION and not missing_columns,
            "version": int(version or 0),
            "missing_tables": [],
            "missing_columns": missing_columns,
        }
    except SQLAlchemyError as exc:
        return {"ok": False, "version": 0, "missing_tables": [], "missing_columns": [], "error": str(exc)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ambitionz Rebirth PostgreSQL migrations")
    parser.add_argument("command", choices=("upgrade", "check"))
    args = parser.parse_args()
    database_url = os.environ.get("REBIRTH_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("REBIRTH_DATABASE_URL ou DATABASE_URL e obrigatoria.")
    if args.command == "upgrade":
        upgrade_schema(database_url)
        return
    status = validate_schema(make_engine(database_url))
    if not status["ok"]:
        raise SystemExit(f"Schema Rebirth invalido: {status}")


if __name__ == "__main__":
    main()
