"""Simple JSON-RPC wallet helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

from .settings import CurrencySettings, Settings


class WalletError(RuntimeError):
    pass


@dataclass(slots=True)
class Wallet:
    code: str
    name: str
    rpc_url: str
    timeout: int

    def client(self) -> AuthServiceProxy:
        return AuthServiceProxy(self.rpc_url, timeout=self.timeout)


class WalletRegistry:
    """Provides access to configured JSON-RPC wallets."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._wallets: Dict[str, Wallet] = {}
        for code, currency in settings.currencies.items():
            self._wallets[code] = Wallet(
                code=currency.code,
                name=currency.name,
                rpc_url=currency.rpc_url,
                timeout=settings.rpc_timeout,
            )

    def wallet(self, currency: str) -> Wallet:
        try:
            return self._wallets[currency]
        except KeyError as exc:  # pragma: no cover - sanity check
            raise WalletError(f"Currency '{currency}' is not configured") from exc

    def get_new_address(self, currency: str, label: str | None = None) -> str:
        try:
            if label is None:
                label = f"echanger-{currency}"
            return self.wallet(currency).client().getnewaddress(label)
        except JSONRPCException as exc:  # pragma: no cover - network call
            raise WalletError(str(exc)) from exc

    def get_transaction_list(self, currency: str) -> list[dict]:
        try:
            return self.wallet(currency).client().listtransactions()
        except JSONRPCException as exc:  # pragma: no cover - network call
            raise WalletError(str(exc)) from exc

    def send_to_address(self, currency: str, address: str, amount: float) -> str:
        try:
            return self.wallet(currency).client().sendtoaddress(address, amount)
        except JSONRPCException as exc:  # pragma: no cover - network call
            raise WalletError(str(exc)) from exc
