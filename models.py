from datetime import datetime

from db import db


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    current_round_index = db.Column(db.Integer, nullable=False, default=1)
    finished = db.Column(db.Boolean, nullable=False, default=False)
    archived = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    players = db.relationship(
        "Player",
        back_populates="game",
        order_by="Player.sort_order",
        cascade="all, delete-orphan",
    )
    rounds = db.relationship(
        "Round",
        back_populates="game",
        order_by="Round.round_index",
        cascade="all, delete-orphan",
    )


class Person(db.Model):
    __tablename__ = "persons"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(80), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    players = db.relationship(
        "Player",
        back_populates="person",
    )


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=True)
    name = db.Column(db.String(80), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    game = db.relationship("Game", back_populates="players")
    person = db.relationship("Person", back_populates="players")
    round_scores = db.relationship(
        "RoundScore",
        back_populates="player",
        cascade="all, delete-orphan",
    )


class Round(db.Model):
    __tablename__ = "rounds"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    round_index = db.Column(db.Integer, nullable=False)
    round_name = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    game = db.relationship("Game", back_populates="rounds")
    scores = db.relationship(
        "RoundScore",
        back_populates="round",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint("game_id", "round_index", name="uq_round_game_index"),
    )


class RoundScore(db.Model):
    __tablename__ = "round_scores"

    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("rounds.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    went_out = db.Column(db.Boolean, nullable=False, default=False)

    round = db.relationship("Round", back_populates="scores")
    player = db.relationship("Player", back_populates="round_scores")

    __table_args__ = (
        db.UniqueConstraint("round_id", "player_id", name="uq_score_round_player"),
    )
