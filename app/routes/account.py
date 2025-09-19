"""Account management endpoints."""
from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..database import db_session
from ..models import CompletedOrder
from ..rpc import WalletError
from ..services import accounts
from ..services.conversion import ConversionError, string_to_unit
from .helpers import get_current_user, get_settings, get_wallet_registry, login_required

blueprint = Blueprint("account", __name__, url_prefix="/account")


@blueprint.route("/")
@login_required
def index():
    user = get_current_user()
    settings = get_settings()
    balances = accounts.get_balance_view(user, settings)
    addresses = {address.currency: address.address for address in user.addresses}
    history_currency = request.args.get("history")
    history = []
    if history_currency and history_currency in settings.currencies:
        history = accounts.get_trade_history(user, history_currency)
    return render_template(
        "account/index.html",
        balances=balances,
        addresses=addresses,
        currencies=settings.currencies,
        history=history,
        history_currency=history_currency,
    )


@blueprint.route("/deposit/<currency>", methods=["POST"])
@login_required
def create_deposit_address(currency: str):
    settings = get_settings()
    if currency not in settings.currencies:
        flash("Unknown currency", "danger")
        return redirect(url_for("account.index"))
    user = get_current_user()
    registry = get_wallet_registry()
    try:
        address = registry.get_new_address(currency, label=f"user-{user.id}")
    except WalletError as exc:
        flash(f"Unable to request address: {exc}", "danger")
    else:
        accounts.set_deposit_address(user, currency, address)
        flash(f"New {currency.upper()} deposit address generated", "success")
    return redirect(url_for("account.index"))


@blueprint.route("/withdraw", methods=["POST"])
@login_required
def withdraw():
    settings = get_settings()
    user = get_current_user()
    currency = request.form.get("currency", "").lower()
    address = request.form.get("address", "").strip()
    amount_raw = request.form.get("amount", "0").strip()
    if currency not in settings.currencies:
        flash("Unknown currency", "danger")
        return redirect(url_for("account.index"))
    try:
        multiplier = settings.currency(currency).multiplier
        amount_units = string_to_unit(amount_raw, multiplier)
    except ConversionError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("account.index"))
    if amount_units <= 0:
        flash("Amount must be greater than zero", "danger")
        return redirect(url_for("account.index"))
    try:
        accounts.change_balance(user, currency, -amount_units)
    except accounts.AccountError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("account.index"))
    order = CompletedOrder(
        user_id=user.id,
        instrument=f"{currency}_{currency}",
        side="WITHDRAW",
        base_currency=currency,
        quote_currency=currency,
        amount=amount_units,
        price=Decimal("0"),
        is_withdrawal=True,
        withdrawal_address=address,
    )
    db_session.add(order)
    db_session.commit()
    flash("Withdrawal request queued", "info")
    return redirect(url_for("account.index"))
