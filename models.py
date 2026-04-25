from flask_sqlalchemy import SQLAlchemy
from passlib.hash import pbkdf2_sha256

from game.deck import create_new_player_card_data

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    password_hash = db.Column(db.String(256), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)

    coins = db.Column(db.Integer, default=1000)

    deck_json = db.Column(db.Text, nullable=False)
    collection_json = db.Column(db.Text, nullable=False)

    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)

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