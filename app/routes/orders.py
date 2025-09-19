"""Endpoints for placing and cancelling orders."""
from __future__ import annotations

import secrets
from decimal import Decimal

from flask import Blueprint, flash, redirect, request, url_for

from ..database import get_redis_client
from ..forms import OrderForm
from ..services import accounts
from ..services.conversion import ConversionError, string_to_unit
from ..services.orders import Order, OrderBook
from .helpers import get_current_user, get_settings, login_required

blueprint = Blueprint("orders", __name__, url_prefix="/orders")


@blueprint.route("/place", methods=["POST"])
@login_required
def place_order():
    user = get_current_user()
    settings = get_settings()
    form = OrderForm()
    form.instrument.choices = [(pair, pair.upper()) for pair in settings.trading_pairs]
    if not form.validate_on_submit():
        flash("Please correct the errors in the form", "danger")
        return redirect(url_for("home.index", pair=form.instrument.data or settings.trading_pairs[0]))

    instrument = form.instrument.data
    side = form.side.data
    price = Decimal(str(form.price.data))
    base_currency, quote_currency = instrument.split("_")
    try:
        amount_units = string_to_unit(str(form.amount.data), settings.currency(base_currency).multiplier)
    except ConversionError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("home.index", pair=instrument))

    if amount_units <= 0:
        flash("Amount must be greater than zero", "danger")
        return redirect(url_for("home.index", pair=instrument))

    base_multiplier = Decimal(settings.currency(base_currency).multiplier)
    quote_multiplier = Decimal(settings.currency(quote_currency).multiplier)
    quote_total = int((Decimal(amount_units) / base_multiplier * price * quote_multiplier).quantize(Decimal(1)))
    if quote_total <= 0:
        flash("Order total is too small", "danger")
        return redirect(url_for("home.index", pair=instrument))

    try:
        if side == "buy":
            accounts.change_balance(user, quote_currency, -quote_total)
        elif side == "sell":
            accounts.change_balance(user, base_currency, -amount_units)
        else:
            flash("Unknown order side", "danger")
            return redirect(url_for("home.index", pair=instrument))
    except accounts.AccountError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("home.index", pair=instrument))

    order = Order(
        id=secrets.token_hex(16),
        instrument=instrument,
        side=side,
        price=price,
        amount=amount_units,
        user_id=user.id,
    )
    OrderBook(get_redis_client(), settings).place_order(order)
    flash("Order placed", "success")
    return redirect(url_for("home.index", pair=instrument))


@blueprint.route("/<order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id: str):
    user = get_current_user()
    settings = get_settings()
    order_book = OrderBook(get_redis_client(), settings)
    if order_book.cancel_order(order_id, user.id):
        flash("Cancel request submitted", "info")
    else:
        flash("Unable to cancel order", "warning")
    return redirect(url_for("home.index"))
