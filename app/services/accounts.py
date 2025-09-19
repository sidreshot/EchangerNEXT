"""Account and balance related helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from ..database import db_session
from ..models import Address, CompletedOrder, User, WalletBalance
from ..settings import Settings


class AccountError(RuntimeError):
    """Raised when an account related operation fails."""


@dataclass(slots=True)
class BalanceView:
    currency: str
    balance: int

    def as_display(self, multiplier: int) -> str:
        return f"{self.balance / multiplier:.8f}"


def ensure_user_balances(user: User, currencies: Iterable[str]) -> None:
    existing = {balance.currency for balance in user.balances}
    for currency in currencies:
        if currency not in existing:
            user.balances.append(WalletBalance(currency=currency, balance=0))


def create_user(username: str, email: str, password: str, currencies: Iterable[str]) -> User:
    user = User(username=username, email=email, password_hash=generate_password_hash(password))
    ensure_user_balances(user, currencies)
    db_session.add(user)
    db_session.commit()
    return user


def authenticate_user(email: str, password: str) -> User | None:
    user = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user and check_password_hash(user.password_hash, password):
        return user
    return None


def change_balance(user: User, currency: str, delta: int) -> WalletBalance:
    for balance in user.balances:
        if balance.currency == currency:
            if balance.balance + delta < 0:
                raise AccountError(
                    f"Insufficient balance for {currency}: {balance.balance} + {delta}",
                )
            balance.balance += delta
            db_session.add(balance)
            db_session.commit()
            return balance
    raise AccountError(f"Unknown currency '{currency}' for user {user.id}")


def get_balance_view(user: User, settings: Settings) -> List[BalanceView]:
    balances: List[BalanceView] = []
    for balance in user.balances:
        try:
            multiplier = settings.currency(balance.currency).multiplier
        except KeyError:
            multiplier = 100_000_000
        balances.append(BalanceView(currency=balance.currency, balance=balance.balance))
    balances.sort(key=lambda item: item.currency)
    return balances


def get_deposit_address(user: User, currency: str) -> str | None:
    address = (
        db_session.execute(
            select(Address).where(Address.user_id == user.id, Address.currency == currency)
        ).scalar_one_or_none()
    )
    if address:
        return address.address
    return None


def set_deposit_address(user: User, currency: str, address: str, label: str | None = None) -> Address:
    entry = (
        db_session.execute(
            select(Address).where(Address.user_id == user.id, Address.currency == currency)
        ).scalar_one_or_none()
    )
    if entry:
        entry.address = address
        entry.label = label
    else:
        entry = Address(user_id=user.id, currency=currency, address=address, label=label)
    db_session.add(entry)
    db_session.commit()
    return entry


def get_trade_history(user: User, currency: str) -> List[CompletedOrder]:
    return list(
        db_session.execute(
            select(CompletedOrder)
            .where(CompletedOrder.user_id == user.id, CompletedOrder.base_currency == currency)
            .order_by(CompletedOrder.created_at.desc())
        ).scalars()
    )


def serialize_balances(user: User, settings: Settings) -> List[Dict[str, str]]:
    payload: List[Dict[str, str]] = []
    for balance in get_balance_view(user, settings):
        multiplier = settings.currency(balance.currency).multiplier
        payload.append(
            {
                "currency": balance.currency,
                "amount": balance.as_display(multiplier),
            }
        )
    return payload
