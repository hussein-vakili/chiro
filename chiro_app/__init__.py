from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask

from .db import init_app as init_db_app
from .routes import bp


def create_app() -> Flask:
    root_dir = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(root_dir / "templates"),
        static_folder=str(root_dir / "static"),
    )
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", secrets.token_hex(32)),
        DATABASE=str(Path(app.instance_path) / "chiro.sqlite3"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    init_db_app(app)
    app.register_blueprint(bp)

    return app
