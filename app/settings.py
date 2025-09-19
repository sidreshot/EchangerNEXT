"""Application configuration loading utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class MailSettings:
    """Outgoing mail configuration used for account notifications."""

    server: str = "localhost"
    port: int = 25
    use_tls: bool = False
    use_ssl: bool = False
    username: str | None = None
    password: str | None = None
    default_sender: str | None = None


@dataclass(slots=True)
class CurrencySettings:
    """Information required to interact with a coin daemon over JSON-RPC."""

    code: str
    name: str
    rpc_url: str
    multiplier: int = 100_000_000
    min_confirmations: int = 1


@dataclass(slots=True)
class Settings:
    """Container for runtime configuration derived from the environment."""

    secret_key: str
    database_url: str
    redis_url: str
    rpc_timeout: int
    currencies: Dict[str, CurrencySettings] = field(default_factory=dict)
    trading_pairs: List[str] = field(default_factory=list)
    mail: MailSettings = field(default_factory=MailSettings)

    def currency(self, code: str) -> CurrencySettings:
        try:
            return self.currencies[code]
        except KeyError as exc:  # pragma: no cover - defensive programming
            raise KeyError(f"Unknown currency '{code}'") from exc


_DEFAULT_RPC_ENDPOINTS: Dict[str, tuple[str, int]] = {
    "btc": ("Bitcoin", 8332),
    "ltc": ("Litecoin", 9332),
    "bch": ("Bitcoin Cash", 8332),
    "dash": ("Dash", 9998),
    "doge": ("Dogecoin", 22555),
}


def _build_currency_settings(timeout: int) -> Dict[str, CurrencySettings]:
    currencies: Dict[str, CurrencySettings] = {}
    for code, (name, default_port) in _DEFAULT_RPC_ENDPOINTS.items():
        env_var = f"RPC_{code.upper()}_URL"
        url = os.getenv(env_var)
        if not url:
            # Default to a local daemon with the conventional port.  The user
            # must provide authentication credentials through the environment.
            url = f"http://user:password@127.0.0.1:{default_port}"
        currencies[code] = CurrencySettings(
            code=code,
            name=name,
            rpc_url=url,
            multiplier=100_000_000,
            min_confirmations=max(int(os.getenv(f"RPC_{code.upper()}_CONFIRMATIONS", "1")), 1),
        )
    return currencies


def _load_mail_settings() -> MailSettings:
    mail = MailSettings()
    mail.server = os.getenv("MAIL_SERVER", mail.server)
    mail.port = int(os.getenv("MAIL_PORT", str(mail.port)))
    mail.use_tls = os.getenv("MAIL_USE_TLS", "false").lower() == "true"
    mail.use_ssl = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    mail.username = os.getenv("MAIL_USERNAME")
    mail.password = os.getenv("MAIL_PASSWORD")
    mail.default_sender = os.getenv("MAIL_DEFAULT_SENDER")
    return mail


def get_settings() -> Settings:
    """Return application settings derived from environment variables."""

    secret_key = os.getenv("SECRET_KEY", "change-me")
    database_url = os.getenv("DATABASE_URL", "sqlite:///instance/echanger.db")
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    rpc_timeout = int(os.getenv("RPC_TIMEOUT", "30"))
    currencies = _build_currency_settings(rpc_timeout)
    trading_pairs_env = os.getenv(
        "TRADING_PAIRS",
        "ltc_btc,bch_btc,dash_btc,doge_btc",
    )
    trading_pairs = [pair.strip().lower() for pair in trading_pairs_env.split(",") if pair.strip()]
    mail_settings = _load_mail_settings()
    return Settings(
        secret_key=secret_key,
        database_url=database_url,
        redis_url=redis_url,
        rpc_timeout=rpc_timeout,
        currencies=currencies,
        trading_pairs=trading_pairs,
        mail=mail_settings,
    )
