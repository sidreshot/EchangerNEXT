"""Database models for the exchange."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class TimestampMixin:
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    balances = relationship(
        "WalletBalance",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    addresses = relationship(
        "Address",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    orders = relationship(
        "CompletedOrder",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def balance_for(self, currency: str) -> int:
        """Return the balance in the currency's smallest unit."""
        for balance in self.balances:
            if balance.currency == currency:
                return balance.balance
        return 0


class WalletBalance(Base, TimestampMixin):
    __tablename__ = "wallet_balances"
    __table_args__ = (
        UniqueConstraint("user_id", "currency", name="uq_wallet_currency"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    currency = Column(String(10), nullable=False)
    balance = Column(BigInteger, default=0, nullable=False)

    user = relationship("User", back_populates="balances")


class Address(Base, TimestampMixin):
    __tablename__ = "wallet_addresses"
    __table_args__ = (
        UniqueConstraint("currency", "address", name="uq_currency_address"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    currency = Column(String(10), nullable=False)
    address = Column(String(128), nullable=False)
    label = Column(String(64))

    user = relationship("User", back_populates="addresses")


class CompletedOrder(Base, TimestampMixin):
    __tablename__ = "completed_orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instrument = Column(String(15), nullable=False)
    side = Column(String(4), nullable=False)
    base_currency = Column(String(10), nullable=False)
    quote_currency = Column(String(10), nullable=False)
    amount = Column(BigInteger, nullable=False)
    price = Column(Numeric(precision=18, scale=8), nullable=False)
    is_deposit = Column(Boolean, default=False, nullable=False)
    is_withdrawal = Column(Boolean, default=False, nullable=False)
    withdrawal_address = Column(String(128))
    transaction_id = Column(String(128))

    user = relationship("User", back_populates="orders")

    @property
    def price_decimal(self) -> Decimal:
        return Decimal(self.price)
