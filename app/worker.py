"""Order matching worker."""
from __future__ import annotations

import logging
import time
from decimal import Decimal

import click
from . import create_app
from .database import db_session, get_redis_client
from .models import CompletedOrder, User
from .services import accounts
from .settings import Settings

logger = logging.getLogger(__name__)


def _quote_units(settings: Settings, instrument: str, amount_units: int, price: Decimal) -> int:
    base_currency, quote_currency = instrument.split("_")
    base_multiplier = Decimal(settings.currency(base_currency).multiplier)
    quote_multiplier = Decimal(settings.currency(quote_currency).multiplier)
    return int((Decimal(amount_units) / base_multiplier * price * quote_multiplier).quantize(Decimal(1)))


def _record_trade(user_id: int, instrument: str, side: str, amount_units: int, price: Decimal) -> None:
    base_currency, quote_currency = instrument.split("_")
    order = CompletedOrder(
        user_id=user_id,
        instrument=instrument,
        side=side,
        base_currency=base_currency,
        quote_currency=quote_currency,
        amount=amount_units,
        price=price,
    )
    db_session.add(order)


def _handle_cancel(settings: Settings, redis, order: dict) -> None:
    old_order_id = order.get("old_order_id")
    if not old_order_id or not redis.exists(old_order_id):
        return
    existing = redis.hgetall(old_order_id)
    instrument = existing.get("instrument")
    if not instrument:
        redis.delete(old_order_id)
        return
    user_id = int(existing.get("uid", 0))
    user = db_session.get(User, user_id)
    if not user:
        redis.delete(old_order_id)
        return
    side = existing.get("ordertype")
    amount_units = int(existing.get("amount", 0))
    price = Decimal(existing.get("price", "0"))
    base_currency, quote_currency = instrument.split("_")
    if side == "buy":
        refund_units = _quote_units(settings, instrument, amount_units, price)
        accounts.change_balance(user, quote_currency, refund_units)
        redis.zrem(f"{instrument}/bid", old_order_id)
    else:
        accounts.change_balance(user, base_currency, amount_units)
        redis.zrem(f"{instrument}/ask", old_order_id)
    redis.delete(old_order_id)
    redis.srem(f"{user_id}/orders", old_order_id)


def _match_order(settings: Settings, redis, order_id: str, payload: dict) -> None:
    instrument = payload["instrument"]
    side = payload["ordertype"]
    price = Decimal(payload["price"])
    amount_remaining = int(payload["amount"])
    user_id = int(payload["uid"])
    user = db_session.get(User, user_id)
    if not user:
        logger.warning("Dropping order %s for unknown user %s", order_id, user_id)
        return
    base_currency, quote_currency = instrument.split("_")
    bid_key = f"{instrument}/bid"
    ask_key = f"{instrument}/ask"
    completed_key = f"{instrument}/completed"

    if side == "buy":
        while amount_remaining > 0:
            best_match = redis.zrange(ask_key, 0, 0)
            if not best_match:
                break
            match_id = best_match[0]
            best_price = Decimal(str(redis.zscore(ask_key, match_id)))
            if best_price > price:
                break
            match_payload = redis.hgetall(match_id)
            match_amount = int(match_payload.get("amount", 0))
            seller_id = int(match_payload.get("uid", 0))
            seller = db_session.get(User, seller_id)
            if not seller:
                redis.delete(match_id)
                redis.zrem(ask_key, match_id)
                continue
            trade_amount = min(amount_remaining, match_amount)
            quote_units = _quote_units(settings, instrument, trade_amount, price)
            accounts.change_balance(seller, quote_currency, quote_units)
            accounts.change_balance(user, base_currency, trade_amount)
            _record_trade(user.id, instrument, "buy", trade_amount, price)
            _record_trade(seller.id, instrument, "sell", trade_amount, price)
            completed_id = f"completed:{order_id}:{match_id}:{trade_amount}"
            redis.hset(
                completed_id,
                mapping={
                    "price": float(price),
                    "quote_currency_amount": float(quote_units) / settings.currency(quote_currency).multiplier,
                    "base_currency_amount": float(trade_amount) / settings.currency(base_currency).multiplier,
                },
            )
            redis.zadd(completed_key, {completed_id: float(price)})
            amount_remaining -= trade_amount
            if trade_amount == match_amount:
                redis.delete(match_id)
                redis.zrem(ask_key, match_id)
                redis.srem(f"{seller_id}/orders", match_id)
            else:
                redis.hset(match_id, mapping={"amount": match_amount - trade_amount})
            db_session.commit()
        if amount_remaining > 0:
            redis.hset(order_id, mapping={"amount": amount_remaining})
            redis.zadd(bid_key, {order_id: float(price)})
        else:
            redis.delete(order_id)
            redis.zrem(bid_key, order_id)
            redis.srem(f"{user_id}/orders", order_id)
    elif side == "sell":
        while amount_remaining > 0:
            best_match = redis.zrange(bid_key, -1, -1)
            if not best_match:
                break
            match_id = best_match[0]
            best_price = Decimal(str(redis.zscore(bid_key, match_id)))
            if best_price < price:
                break
            match_payload = redis.hgetall(match_id)
            match_amount = int(match_payload.get("amount", 0))
            buyer_id = int(match_payload.get("uid", 0))
            buyer = db_session.get(User, buyer_id)
            if not buyer:
                redis.delete(match_id)
                redis.zrem(bid_key, match_id)
                continue
            trade_amount = min(amount_remaining, match_amount)
            quote_units = _quote_units(settings, instrument, trade_amount, best_price)
            accounts.change_balance(buyer, base_currency, trade_amount)
            accounts.change_balance(user, quote_currency, quote_units)
            _record_trade(buyer.id, instrument, "buy", trade_amount, best_price)
            _record_trade(user.id, instrument, "sell", trade_amount, best_price)
            completed_id = f"completed:{order_id}:{match_id}:{trade_amount}"
            redis.hset(
                completed_id,
                mapping={
                    "price": float(best_price),
                    "quote_currency_amount": float(quote_units) / settings.currency(quote_currency).multiplier,
                    "base_currency_amount": float(trade_amount) / settings.currency(base_currency).multiplier,
                },
            )
            redis.zadd(completed_key, {completed_id: float(best_price)})
            amount_remaining -= trade_amount
            if trade_amount == match_amount:
                redis.delete(match_id)
                redis.zrem(bid_key, match_id)
                redis.srem(f"{buyer_id}/orders", match_id)
            else:
                redis.hset(match_id, mapping={"amount": match_amount - trade_amount})
            db_session.commit()
        if amount_remaining > 0:
            redis.hset(order_id, mapping={"amount": amount_remaining})
            redis.zadd(ask_key, {order_id: float(price)})
        else:
            redis.delete(order_id)
            redis.zrem(ask_key, order_id)
            redis.srem(f"{user_id}/orders", order_id)
    else:
        logger.warning("Unknown order type %s", side)


def _process_once(settings: Settings, redis) -> bool:
    item = redis.blpop("order_queue", timeout=1)
    if not item:
        return False
    order_id = item[1]
    payload = redis.hgetall(order_id)
    if not payload:
        return True
    if payload.get("ordertype") == "cancel":
        _handle_cancel(settings, redis, payload)
    else:
        _match_order(settings, redis, order_id, payload)
    return True


@click.command()
@click.option("--once", is_flag=True, help="Process only one queue item and exit")
@click.option("--sleep", "sleep_interval", type=int, default=1, help="Sleep between idle polling attempts")
def main(once: bool, sleep_interval: int) -> None:
    app = create_app()
    with app.app_context():
        redis = get_redis_client()
        settings = app.extensions["settings"]
        logger.info("Starting order matching worker")
        while True:
            processed = _process_once(settings, redis)
            if once:
                break
            if not processed:
                time.sleep(sleep_interval)


if __name__ == "__main__":  # pragma: no cover
    main()
