"""Shared helpers for blueprints."""
from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar

from flask import current_app, flash, redirect, session, url_for
from sqlalchemy import select

from ..database import db_session
from ..models import User
from ..rpc import WalletRegistry
from ..settings import Settings

F = TypeVar("F", bound=Callable[..., object])


def get_settings() -> Settings:
    return current_app.extensions["settings"]


def get_current_user() -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db_session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


def login_user(user: User) -> None:
    session["user_id"] = user.id


def logout_user() -> None:
    session.pop("user_id", None)


def login_required(func: F) -> F:
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not get_current_user():
            flash("Please log in to continue", "warning")
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def get_wallet_registry() -> WalletRegistry:
    return current_app.extensions["wallet_registry"]
