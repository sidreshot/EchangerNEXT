"""Polling worker that credits deposits from RPC wallets."""
from __future__ import annotations

import logging
import time
from decimal import Decimal

import click
from sqlalchemy import select

from . import create_app
from .database import db_session
from .models import Address, CompletedOrder
from .rpc import WalletError
from .services import accounts

logger = logging.getLogger(__name__)


def _process_currency(registry, settings, currency_code: str) -> None:
    currency = settings.currency(currency_code)
    try:
        transactions = registry.get_transaction_list(currency_code)
    except WalletError as exc:
        logger.warning("Unable to fetch transactions for %s: %s", currency_code, exc)
        return
    known_txs = {
        tx_id
        for (tx_id,) in db_session.execute(
            select(CompletedOrder.transaction_id).where(CompletedOrder.transaction_id.isnot(None))
        )
    }
    for tx in transactions:
        if tx.get("category") != "receive":
            continue
        if tx.get("confirmations", 0) < currency.min_confirmations:
            continue
        txid = tx.get("txid")
        if not txid or txid in known_txs:
            continue
        address = tx.get("address")
        if not address:
            continue
        address_entry = db_session.execute(
            select(Address).where(Address.currency == currency_code, Address.address == address)
        ).scalar_one_or_none()
        if not address_entry:
            logger.info("Skipping deposit for unknown address %s", address)
            continue
        user = address_entry.user
        amount_units = int(Decimal(str(tx.get("amount", 0))) * currency.multiplier)
        if amount_units <= 0:
            continue
        accounts.change_balance(user, currency_code, amount_units)
        order = CompletedOrder(
            user_id=user.id,
            instrument=f"{currency_code}_{currency_code}",
            side="DEPOSIT",
            base_currency=currency_code,
            quote_currency=currency_code,
            amount=amount_units,
            price=Decimal("0"),
            is_deposit=True,
            transaction_id=txid,
        )
        db_session.add(order)
        db_session.commit()
        logger.info(
            "Credited %s %s to user %s", currency_code.upper(), Decimal(amount_units) / currency.multiplier, user.id
        )


@click.command()
@click.option("--interval", type=int, default=30, help="Polling interval in seconds")
@click.option("--once", is_flag=True, help="Process a single iteration and exit")
def main(interval: int, once: bool) -> None:
    app = create_app()
    with app.app_context():
        registry = app.extensions["wallet_registry"]
        settings = app.extensions["settings"]
        logger.info("Starting deposit processor")
        while True:
            for code in settings.currencies.keys():
                _process_currency(registry, settings, code)
            if once:
                break
            time.sleep(interval)


if __name__ == "__main__":  # pragma: no cover
    main()
