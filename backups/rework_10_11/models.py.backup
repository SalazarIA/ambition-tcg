from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from passlib.hash import pbkdf2_sha256

from game.deck import create_new_player_card_data

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    password_hash = db.Column(db.String(256), nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    coins = db.Column(db.Integer, default=1000, nullable=False)

    deck_json = db.Column(db.Text, nullable=False)
    collection_json = db.Column(db.Text, nullable=False)

    wins = db.Column(db.Integer, default=0, nullable=False)
    losses = db.Column(db.Integer, default=0, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        card_data = create_new_player_card_data()

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
