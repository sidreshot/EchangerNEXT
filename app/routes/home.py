"""Public landing pages."""
from __future__ import annotations

from flask import Blueprint, render_template, request

from ..database import get_redis_client
from ..forms import OrderForm
from ..services.orders import OrderBook
from .helpers import get_current_user, get_settings

blueprint = Blueprint("home", __name__)


def _instrument_from_request() -> str:
    settings = get_settings()
    if not settings.trading_pairs:
        return "ltc_btc"
    requested = request.args.get("pair")
    if requested and requested in settings.trading_pairs:
        return requested
    return settings.trading_pairs[0]


@blueprint.route("/")
def index():
    settings = get_settings()
    instrument = _instrument_from_request()
    order_book = OrderBook(get_redis_client(), settings)
    form = OrderForm()
    form.instrument.choices = [(pair, pair.upper()) for pair in settings.trading_pairs]
    form.instrument.data = instrument
    user = get_current_user()
    return render_template(
        "home/index.html",
        instrument=instrument,
        form=form,
        stats={
            "volume": order_book.get_volume(instrument),
            "high": order_book.get_high(instrument),
            "low": order_book.get_low(instrument),
        },
        bids=order_book.list_orders(instrument, "bid"),
        asks=order_book.list_orders(instrument, "ask"),
        trading_pairs=settings.trading_pairs,
        user=user,
    )
