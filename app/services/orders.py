"""Order-book helpers backed by Redis."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List

from redis import Redis
from redis.exceptions import RedisError

from ..settings import Settings


@dataclass(slots=True)
class Order:
    id: str
    instrument: str
    side: str
    price: Decimal
    amount: int
    user_id: int

    def serialize(self, multiplier: int) -> Dict[str, str]:
        amount_dec = Decimal(self.amount) / Decimal(multiplier)
        return {
            "id": self.id,
            "instrument": self.instrument,
            "side": self.side,
            "price": f"{self.price:.8f}",
            "amount": f"{amount_dec:.8f}",
        }


class OrderBook:
    def __init__(self, redis_client: Redis, settings: Settings) -> None:
        self.redis = redis_client
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def _bid_key(instrument: str) -> str:
        return f"{instrument}/bid"

    @staticmethod
    def _ask_key(instrument: str) -> str:
        return f"{instrument}/ask"

    @staticmethod
    def _completed_key(instrument: str) -> str:
        return f"{instrument}/completed"

    def _instrument_multiplier(self, instrument: str) -> int:
        base_currency = instrument.split("_")[0]
        return self.settings.currency(base_currency).multiplier

    def place_order(self, order: Order) -> None:
        key = self._bid_key(order.instrument) if order.side == "buy" else self._ask_key(order.instrument)
        self.redis.hset(order.id, mapping={
            "instrument": order.instrument,
            "ordertype": order.side,
            "amount": order.amount,
            "uid": order.user_id,
            "price": str(order.price),
        })
        self.redis.sadd(f"{order.user_id}/orders", order.id)
        self.redis.rpush("order_queue", order.id)
        self.redis.zadd(key, {order.id: float(order.price)})

    def cancel_order(self, order_id: str, user_id: int) -> bool:
        if not self.redis.sismember(f"{user_id}/orders", order_id):
            return False
        cancel_id = f"cancel:{order_id}"
        self.redis.hset(cancel_id, mapping={
            "ordertype": "cancel",
            "uid": user_id,
            "old_order_id": order_id,
        })
        self.redis.rpush("order_queue", cancel_id)
        return True

    def list_orders(self, instrument: str, side: str) -> List[Dict[str, str]]:
        key = self._bid_key(instrument) if side == "bid" else self._ask_key(instrument)
        multiplier = self._instrument_multiplier(instrument)
        orders: List[Dict[str, str]] = []
        try:
            for order_id, price in self.redis.zrange(key, 0, -1, withscores=True):
                payload = self.redis.hgetall(order_id)
                if not payload:
                    self.redis.zrem(key, order_id)
                    continue
                amount = int(payload.get("amount", 0))
                orders.append(
                    {
                        "price": price,
                        "amount": float(amount) / multiplier,
                    }
                )
        except RedisError as exc:
            self.logger.warning("Redis unavailable while listing orders: %s", exc)
        return orders

    def get_volume(self, instrument: str) -> Dict[str, float]:
        multiplier = self._instrument_multiplier(instrument)
        completed_key = self._completed_key(instrument)
        base_volume = 0.0
        quote_volume = 0.0
        try:
            for entry_id, price in self.redis.zrange(completed_key, 0, -1, withscores=True):
                payload = self.redis.hgetall(entry_id)
                if not payload:
                    self.redis.zrem(completed_key, entry_id)
                    continue
                quote_volume += float(payload.get("quote_currency_amount", 0))
                base_volume += float(payload.get("base_currency_amount", 0))
        except RedisError as exc:
            self.logger.warning("Redis unavailable while computing volume: %s", exc)
        return {
            "base_currency_volume": round(base_volume, 8),
            "quote_currency_volume": round(quote_volume, 8),
            "multiplier": multiplier,
        }

    def get_high(self, instrument: str) -> float:
        completed_key = self._completed_key(instrument)
        try:
            prices = self.redis.zrange(completed_key, -1, -1, withscores=True)
        except RedisError as exc:
            self.logger.warning("Redis unavailable while fetching high price: %s", exc)
            return 0.0
        if not prices:
            return 0.0
        return float(prices[0][1])

    def get_low(self, instrument: str) -> float:
        completed_key = self._completed_key(instrument)
        try:
            prices = self.redis.zrange(completed_key, 0, 0, withscores=True)
        except RedisError as exc:
            self.logger.warning("Redis unavailable while fetching low price: %s", exc)
            return 0.0
        if not prices:
            return 0.0
        return float(prices[0][1])
