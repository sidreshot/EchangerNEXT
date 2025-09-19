"""Blueprint registration."""
from __future__ import annotations

from flask import Flask

from . import account, api, auth, home, orders


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(home.blueprint)
    app.register_blueprint(auth.blueprint)
    app.register_blueprint(account.blueprint)
    app.register_blueprint(orders.blueprint)
    app.register_blueprint(api.blueprint)
