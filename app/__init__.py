"""Application factory."""
from __future__ import annotations

from pathlib import Path

from flask import Flask
from flask_mail import Mail
from flask_wtf import CSRFProtect

from .database import close_session, init_db, init_engine, init_redis_client
from .logging_config import configure_logging
from .routes import register_blueprints
from .rpc import WalletRegistry
from .settings import get_settings

mail = Mail()
csrf = CSRFProtect()


def create_app() -> Flask:
    settings = get_settings()
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        SECRET_KEY=settings.secret_key,
        MAIL_SERVER=settings.mail.server,
        MAIL_PORT=settings.mail.port,
        MAIL_USE_TLS=settings.mail.use_tls,
        MAIL_USE_SSL=settings.mail.use_ssl,
        MAIL_USERNAME=settings.mail.username,
        MAIL_PASSWORD=settings.mail.password,
        MAIL_DEFAULT_SENDER=settings.mail.default_sender,
    )

    configure_logging(debug=app.debug)

    mail.init_app(app)
    csrf.init_app(app)

    # Ensure the instance folder exists for SQLite databases.
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    init_engine(settings.database_url)
    init_db()
    init_redis_client(settings.redis_url)

    app.extensions["settings"] = settings
    app.extensions["wallet_registry"] = WalletRegistry(settings)

    register_blueprints(app)
    app.teardown_appcontext(close_session)

    return app


app = create_app()
