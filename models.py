from datetime import datetime, timezone

from sqlalchemy import inspect, text
from flask_sqlalchemy import SQLAlchemy
from passlib.hash import pbkdf2_sha256

from game.deck import create_new_player_card_data

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    account_status = db.Column(db.String(40), nullable=False, default="active", index=True)
    is_tester = db.Column(db.Boolean, default=False, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    login_count = db.Column(db.Integer, default=0, nullable=False)
    has_completed_onboarding = db.Column(db.Boolean, default=False, nullable=False)
    first_training_completed = db.Column(db.Boolean, default=False, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_verified = db.Column(db.Boolean, default=True, nullable=False)

    coins = db.Column(db.Integer, default=1000, nullable=False)

    deck_json = db.Column(db.Text, nullable=False)
    collection_json = db.Column(db.Text, nullable=False)

    wins = db.Column(db.Integer, default=0, nullable=False)
    losses = db.Column(db.Integer, default=0, nullable=False)

    xp = db.Column(db.Integer, default=0, nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)

    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    reset_token = db.Column(db.String(256), nullable=True, index=True)
    reset_token_expires_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        card_data = create_new_player_card_data()

        if self.account_status in (None, "unverified", "pending_verification"):
            self.account_status = "active"

        if self.is_verified is None:
            self.is_verified = True

        if self.is_verified and not self.verified_at:
            self.verified_at = datetime.now(timezone.utc)

        if not self.deck_json:
            self.deck_json = card_data["deck_json"]

        if not self.collection_json:
            self.collection_json = card_data["collection_json"]

    def set_password(self, password):
        self.password_hash = pbkdf2_sha256.hash(password)

    def check_password(self, password):
        return pbkdf2_sha256.verify(password, self.password_hash)

    @property
    def total_matches(self):
        return int(self.wins or 0) + int(self.losses or 0)

    @property
    def win_rate(self):
        total = self.total_matches

        if total <= 0:
            return 0

        return round((self.wins / total) * 100, 1)

    @property
    def next_level_xp(self):
        return max(100, int(self.level or 1) * 100)

    @property
    def level_progress_percent(self):
        needed = self.next_level_xp

        if needed <= 0:
            return 0

        return min(100, round((int(self.xp or 0) / needed) * 100, 1))

    def __repr__(self):
        return f"<User {self.username}>"


class MatchHistory(db.Model):
    __tablename__ = "match_history"

    id = db.Column(db.Integer, primary_key=True)

    player1_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    player2_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    winner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    player1_name = db.Column(db.String(80), nullable=False)
    player2_name = db.Column(db.String(80), nullable=False)
    winner_name = db.Column(db.String(80), nullable=True)

    result = db.Column(db.String(20), nullable=False, default="UNKNOWN")

    player1_final_hp = db.Column(db.Integer, default=0, nullable=False)
    player2_final_hp = db.Column(db.Integer, default=0, nullable=False)

    total_rounds = db.Column(db.Integer, default=0, nullable=False)

    battle_log_json = db.Column(db.Text, nullable=False, default="[]")

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    player1 = db.relationship("User", foreign_keys=[player1_id])
    player2 = db.relationship("User", foreign_keys=[player2_id])
    winner = db.relationship("User", foreign_keys=[winner_id])

    def __repr__(self):
        return f"<MatchHistory {self.player1_name} vs {self.player2_name}>"


class CardStat(db.Model):
    __tablename__ = "card_stats"

    id = db.Column(db.Integer, primary_key=True)

    card_id = db.Column(db.String(80), unique=True, nullable=False, index=True)
    card_name = db.Column(db.String(120), nullable=False)
    card_type = db.Column(db.String(40), nullable=False)
    element = db.Column(db.String(40), nullable=False)
    rarity = db.Column(db.String(40), nullable=False)

    games_seen = db.Column(db.Integer, default=0, nullable=False)
    times_played = db.Column(db.Integer, default=0, nullable=False)
    wins_when_played = db.Column(db.Integer, default=0, nullable=False)
    losses_when_played = db.Column(db.Integer, default=0, nullable=False)
    draws_when_played = db.Column(db.Integer, default=0, nullable=False)

    total_damage_context = db.Column(db.Integer, default=0, nullable=False)

    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def win_rate_when_played(self):
        total = self.wins_when_played + self.losses_when_played + self.draws_when_played

        if total <= 0:
            return 0

        return round((self.wins_when_played / total) * 100, 1)

    def __repr__(self):
        return f"<CardStat {self.card_name}>"


class UserMission(db.Model):
    __tablename__ = "user_missions"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    mission_key = db.Column(db.String(80), nullable=False, index=True)

    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(255), nullable=False)

    progress = db.Column(db.Integer, default=0, nullable=False)
    target = db.Column(db.Integer, default=1, nullable=False)

    xp_reward = db.Column(db.Integer, default=0, nullable=False)
    coin_reward = db.Column(db.Integer, default=0, nullable=False)

    is_claimed = db.Column(db.Boolean, default=False, nullable=False)

    mission_date = db.Column(db.String(20), nullable=False, index=True)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship("User")

    @property
    def is_complete(self):
        return int(self.progress or 0) >= int(self.target or 1)

    @property
    def progress_percent(self):
        target = max(1, int(self.target or 1))
        return min(100, round((int(self.progress or 0) / target) * 100, 1))

    def __repr__(self):
        return f"<UserMission {self.user_id} {self.mission_key}>"


def ensure_database_schema():
    """
    Lightweight schema guard for this beta.
    db.create_all() creates new tables but does not add columns to existing tables.
    This function adds missing columns used by newer reworks.
    """
    engine = db.engine
    dialect = engine.dialect.name

    if dialect == "postgresql":
        statements = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS xp INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(256)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        ]
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
        return

    existing_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    sqlite_columns = {
        "xp": "xp INTEGER NOT NULL DEFAULT 0",
        "level": "level INTEGER NOT NULL DEFAULT 1",
        "is_admin": "is_admin BOOLEAN NOT NULL DEFAULT 0",
        "reset_token": "reset_token VARCHAR(256)",
        "reset_token_expires_at": "reset_token_expires_at DATETIME",
        "created_at": "created_at DATETIME",
    }

    with engine.begin() as connection:
        for column_name, ddl in sqlite_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {ddl}"))



class FeedbackReport(db.Model):
    __tablename__ = "feedback_reports"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    username = db.Column(db.String(80), nullable=True)

    category = db.Column(db.String(60), nullable=False, default="general")
    severity = db.Column(db.String(40), nullable=False, default="normal")

    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)

    page_url = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="open")

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user = db.relationship("User")

    def __repr__(self):
        return f"<FeedbackReport {self.category} {self.title}>"



class BoosterHistory(db.Model):
    __tablename__ = "booster_history"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    username = db.Column(db.String(80), nullable=False)

    cost = db.Column(db.Integer, default=0, nullable=False)
    cards_json = db.Column(db.Text, nullable=False, default="[]")

    common_count = db.Column(db.Integer, default=0, nullable=False)
    uncommon_count = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user = db.relationship("User")

    def __repr__(self):
        return f"<BoosterHistory {self.username} {self.created_at}>"



class BetaInvite(db.Model):
    __tablename__ = "beta_invites"

    id = db.Column(db.Integer, primary_key=True)

    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    max_uses = db.Column(db.Integer, default=1, nullable=False)
    used_count = db.Column(db.Integer, default=0, nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    created_by = db.relationship("User", foreign_keys=[created_by_user_id])

    def can_be_used(self):
        now = datetime.now(timezone.utc)

        if not self.is_active:
            return False

        if self.expires_at and self.expires_at < now:
            return False

        if self.used_count >= self.max_uses:
            return False

        return True

    def __repr__(self):
        return f"<BetaInvite {self.code} {self.used_count}/{self.max_uses}>"



class SystemLog(db.Model):
    __tablename__ = "system_logs"

    id = db.Column(db.Integer, primary_key=True)

    level = db.Column(db.String(40), nullable=False, default="info", index=True)
    category = db.Column(db.String(60), nullable=False, default="system", index=True)
    message = db.Column(db.String(255), nullable=False)
    details_json = db.Column(db.Text, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    is_resolved = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user = db.relationship("User")

    def __repr__(self):
        return f"<SystemLog {self.level} {self.category} {self.message}>"




def ensure_liveops_schema(app):
    """V1.02 lightweight production-safe schema updater."""
    from sqlalchemy import inspect, text as sql_text

    with app.app_context():
        db.create_all()

        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()

        if "users" not in table_names:
            return

        dialect = db.engine.dialect.name

        if dialect == "postgresql":
            commands = [
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS account_status VARCHAR(40) DEFAULT 'active' NOT NULL",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_tester BOOLEAN DEFAULT false NOT NULL",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS login_count INTEGER DEFAULT 0 NOT NULL",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS has_completed_onboarding BOOLEAN DEFAULT false NOT NULL",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS first_training_completed BOOLEAN DEFAULT false NOT NULL",
                "UPDATE users SET is_verified = true WHERE is_verified = false OR is_verified IS NULL",
                "UPDATE users SET account_status = 'active' WHERE account_status IS NULL OR account_status IN ('unverified', 'pending_verification')",
                "UPDATE users SET verified_at = NOW() WHERE verified_at IS NULL",
            ]

            with db.engine.begin() as connection:
                for command in commands:
                    connection.execute(sql_text(command))

            return

        existing_columns = [col["name"] for col in inspector.get_columns("users")]

        sqlite_columns = {
            "account_status": "account_status VARCHAR(40) DEFAULT 'active' NOT NULL",
            "is_tester": "is_tester BOOLEAN DEFAULT false NOT NULL",
            "last_login_at": "last_login_at DATETIME",
            "verified_at": "verified_at DATETIME",
            "login_count": "login_count INTEGER DEFAULT 0 NOT NULL",
            "has_completed_onboarding": "has_completed_onboarding BOOLEAN DEFAULT false NOT NULL",
            "first_training_completed": "first_training_completed BOOLEAN DEFAULT false NOT NULL",
        }

        with db.engine.begin() as connection:
            for column_name, ddl in sqlite_columns.items():
                if column_name not in existing_columns:
                    connection.execute(sql_text(f"ALTER TABLE users ADD COLUMN {ddl}"))

            connection.execute(sql_text("UPDATE users SET is_verified = 1 WHERE is_verified = 0 OR is_verified IS NULL"))
            connection.execute(sql_text("UPDATE users SET account_status = 'active' WHERE account_status IS NULL OR account_status IN ('unverified', 'pending_verification')"))
            connection.execute(sql_text("UPDATE users SET verified_at = CURRENT_TIMESTAMP WHERE verified_at IS NULL"))



class MatchTelemetry(db.Model):
    __tablename__ = "match_telemetry"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(180), nullable=True)
    mode = db.Column(db.String(40), nullable=False, default="pvp")
    winner_user_id = db.Column(db.Integer, nullable=True)
    loser_user_id = db.Column(db.Integer, nullable=True)
    winner_name = db.Column(db.String(120), nullable=True)
    loser_name = db.Column(db.String(120), nullable=True)
    rounds = db.Column(db.Integer, nullable=False, default=0)
    winner_hp = db.Column(db.Integer, nullable=False, default=0)
    loser_hp = db.Column(db.Integer, nullable=False, default=0)
    bot_difficulty = db.Column(db.String(40), nullable=True)
    ending_reason = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RetentionEvent(db.Model):
    __tablename__ = "retention_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    event_key = db.Column(db.String(120), nullable=False, index=True)
    page = db.Column(db.String(220), nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

