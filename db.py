import os

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
migrate = Migrate()


def get_database_uri():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql://", 1)
        return database_url
    return "sqlite:///scoreboard.db"


def init_app(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    migrate.init_app(app, db)
