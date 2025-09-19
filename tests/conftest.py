import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fakeredis
import pytest

import app.database as db
from app import create_app


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SECRET_KEY", "testing-secret")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("TRADING_PAIRS", "ltc_btc")

    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    monkeypatch.setattr(db.redis, "from_url", lambda *args, **kwargs: fake_redis)

    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    db._redis_client = fake_redis
    yield application

    db.db_session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()
