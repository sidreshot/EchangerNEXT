"""Database and cache helpers."""
from __future__ import annotations

from typing import Optional

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

_engine = None
_db_session_factory = sessionmaker(autocommit=False, autoflush=False, future=True)
db_session = scoped_session(_db_session_factory)
Base = declarative_base()
_redis_client: Optional[redis.Redis] = None


def init_engine(database_url: str):
    """Initialise the SQLAlchemy engine and bind it to the session."""
    global _engine
    if _engine is None:
        _engine = create_engine(database_url, future=True)
        db_session.configure(bind=_engine)
    return _engine


def get_engine():
    if _engine is None:
        raise RuntimeError("Database engine has not been initialised")
    return _engine


def init_db():
    from . import models  # noqa: F401  # ensure models are registered

    Base.metadata.create_all(bind=get_engine())


def close_session(exception: Exception | None = None):  # pragma: no cover - Flask hook signature
    db_session.remove()


def init_redis_client(redis_url: str):
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client


def get_redis_client() -> redis.Redis:
    if _redis_client is None:
        raise RuntimeError("Redis client has not been initialised")
    return _redis_client
