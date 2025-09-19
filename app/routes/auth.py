"""Authentication endpoints."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, url_for
from sqlalchemy import select

from ..database import db_session
from ..forms import LoginForm, RegisterForm
from ..models import User
from ..services import accounts
from .helpers import get_current_user, get_settings, login_user, logout_user

blueprint = Blueprint("auth", __name__, url_prefix="/auth")


@blueprint.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for("home.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = accounts.authenticate_user(form.email.data, form.password.data)
        if not user:
            flash("Incorrect email or password", "danger")
        else:
            accounts.ensure_user_balances(user, get_settings().currencies.keys())
            db_session.commit()
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(url_for("home.index"))
    return render_template("auth/login.html", form=form)


@blueprint.route("/logout")
def logout():
    if get_current_user():
        logout_user()
        flash("You have been logged out", "info")
    return redirect(url_for("home.index"))


@blueprint.route("/register", methods=["GET", "POST"])
def register():
    if get_current_user():
        return redirect(url_for("home.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = db_session.execute(
            select(User).where((User.email == form.email.data) | (User.username == form.username.data))
        ).scalar_one_or_none()
        if existing_user:
            flash("An account with that email or username already exists", "warning")
        else:
            user = accounts.create_user(
                form.username.data,
                form.email.data,
                form.password.data,
                get_settings().currencies.keys(),
            )
            login_user(user)
            flash("Account created successfully", "success")
            return redirect(url_for("home.index"))
    return render_template("auth/register.html", form=form)
