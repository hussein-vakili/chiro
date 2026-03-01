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
        REMINDER_EMAIL_MODE=os.environ.get("REMINDER_EMAIL_MODE", "outbox"),
        REMINDER_SMS_MODE=os.environ.get("REMINDER_SMS_MODE", "outbox"),
        REMINDER_EMAIL_FROM=os.environ.get("REMINDER_EMAIL_FROM", "appointments@lifechiro.local"),
        SMTP_HOST=os.environ.get("SMTP_HOST", ""),
        SMTP_PORT=int(os.environ.get("SMTP_PORT", "587")),
        SMTP_USERNAME=os.environ.get("SMTP_USERNAME", ""),
        SMTP_PASSWORD=os.environ.get("SMTP_PASSWORD", ""),
        SMTP_USE_TLS=os.environ.get("SMTP_USE_TLS", "1") not in {"0", "false", "False"},
        SMTP_USE_SSL=os.environ.get("SMTP_USE_SSL", "0") in {"1", "true", "True"},
    )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    init_db_app(app)
    app.register_blueprint(bp)

    return app
