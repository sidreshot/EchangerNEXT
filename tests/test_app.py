from app.services import accounts


def register(client, username="alice", email="alice@example.com", password="supersecret"):
    return client.post(
        "/auth/register",
        data={
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def test_homepage_accessible(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Place order" in response.data


def test_registration_and_login_flow(client, app):
    register(client)

    client.get("/auth/logout", follow_redirects=True)

    login_response = client.post(
        "/auth/login",
        data={"email": "alice@example.com", "password": "supersecret"},
        follow_redirects=True,
    )
    assert b"Welcome back" in login_response.data
    account_response = client.get("/account/", follow_redirects=True)
    assert account_response.status_code == 200
    assert b"Balances" in account_response.data


def test_api_endpoints(client):
    assert client.get("/api/volume/ltc_btc").status_code == 200
    assert client.get("/api/high/ltc_btc").json == {"high": 0.0}
    assert client.get("/api/low/ltc_btc").json == {"low": 0.0}
    orders = client.get("/api/orders/ltc_btc/bid").json
    assert isinstance(orders, list)


def test_order_requires_authentication(client):
    response = client.post(
        "/orders/place",
        data={
            "instrument": "ltc_btc",
            "side": "buy",
            "price": "0.1",
            "amount": "1.0",
        },
        follow_redirects=True,
    )
    assert b"log in" in response.data.lower()


def test_balance_updates_on_order_submission(client, app):
    register(client, "bob", "bob@example.com")
    client.post(
        "/auth/login",
        data={"email": "bob@example.com", "password": "supersecret"},
        follow_redirects=True,
    )

    user = accounts.authenticate_user("bob@example.com", "supersecret")
    settings = app.extensions["settings"]
    accounts.change_balance(user, "ltc", settings.currency("ltc").multiplier * 5)
    accounts.change_balance(user, "btc", settings.currency("btc").multiplier * 5)

    response = client.post(
        "/orders/place",
        data={
            "instrument": "ltc_btc",
            "side": "sell",
            "price": "0.1",
            "amount": "1.5",
        },
        follow_redirects=True,
    )
    assert b"Order placed" in response.data
