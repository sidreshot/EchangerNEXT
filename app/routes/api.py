"""JSON API endpoints."""
from __future__ import annotations

from flask import Blueprint, abort, jsonify

from ..database import get_redis_client
from ..services.orders import OrderBook
from .helpers import get_settings

blueprint = Blueprint("api", __name__, url_prefix="/api")


def _validate_instrument(instrument: str) -> str:
    settings = get_settings()
    if instrument not in settings.trading_pairs:
        abort(404, description="Unknown trading pair")
    return instrument


@blueprint.route("/volume/<instrument>")
def volume(instrument: str):
    instrument = _validate_instrument(instrument)
    order_book = OrderBook(get_redis_client(), get_settings())
    return jsonify(order_book.get_volume(instrument))


@blueprint.route("/high/<instrument>")
def high(instrument: str):
    instrument = _validate_instrument(instrument)
    order_book = OrderBook(get_redis_client(), get_settings())
    return jsonify({"high": order_book.get_high(instrument)})


@blueprint.route("/low/<instrument>")
def low(instrument: str):
    instrument = _validate_instrument(instrument)
    order_book = OrderBook(get_redis_client(), get_settings())
    return jsonify({"low": order_book.get_low(instrument)})


@blueprint.route("/orders/<instrument>/<side>")
def orders(instrument: str, side: str):
    instrument = _validate_instrument(instrument)
    if side not in {"bid", "ask"}:
        abort(400, description="Side must be 'bid' or 'ask'")
    order_book = OrderBook(get_redis_client(), get_settings())
    return jsonify(order_book.list_orders(instrument, side))
