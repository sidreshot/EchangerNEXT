"""WTForms definitions for the web interface."""
from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.fields import EmailField, DecimalField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Log in")


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8)],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )
    submit = SubmitField("Register")


class OrderForm(FlaskForm):
    instrument = SelectField("Trading pair", validators=[DataRequired()])
    side = SelectField(
        "Side",
        choices=[("buy", "Buy"), ("sell", "Sell")],
        validators=[DataRequired()],
    )
    price = DecimalField("Price", places=8, validators=[DataRequired(), NumberRange(min=0)])
    amount = DecimalField("Amount", places=8, validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField("Place order")
