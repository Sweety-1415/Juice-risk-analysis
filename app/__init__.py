from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

import mysql.connector
from flask import Flask

from app.extensions import db, login_manager
from app.models import User

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None


def _database_settings() -> dict[str, str]:
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": os.getenv("DB_PORT", "3306"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "Sweety@1415"),
        "database": os.getenv("DB_NAME", "nutrilens"),
    }


def _bootstrap_database(settings: dict[str, str]) -> None:
    connection = mysql.connector.connect(
        host=settings["host"],
        port=int(settings["port"]),
        user=settings["user"],
        password=settings["password"],
    )
    cursor = connection.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{settings['database']}`")
    connection.commit()
    cursor.close()
    connection.close()


def create_app() -> Flask:
    if load_dotenv:
        load_dotenv()

    app = Flask(__name__, template_folder="templates", static_folder="static")

    settings = _database_settings()
    quoted_password = quote_plus(settings["password"])
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "nutrilens-dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+mysqlconnector://{settings['user']}:{quoted_password}"
        f"@{settings['host']}:{settings['port']}/{settings['database']}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MODEL_PATH"] = str(Path("runs") / "detect" / "train" / "weights" / "best.pt")

    try:
        _bootstrap_database(settings)
        app.config["DATABASE_READY"] = True
        app.config["DATABASE_ERROR"] = ""
    except Exception as exc:  # pragma: no cover - graceful runtime guard
        app.config["DATABASE_READY"] = False
        app.config["DATABASE_ERROR"] = str(exc)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    with app.app_context():
        if app.config["DATABASE_READY"]:
            db.create_all()

    from app.routes import register_routes

    register_routes(app)
    return app
