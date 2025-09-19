"""WSGI entry point and CLI helpers."""
from __future__ import annotations

import click

from app import create_app
from app.database import init_db

app = create_app()


@app.cli.command("db")
def init_database() -> None:
    """Initialise the SQL database tables."""
    init_db()
    click.echo("Database initialised")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
