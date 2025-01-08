def test_sign_up_success(client, valid_email, valid_password):
    response = client.post(
        "/sign-up", json={"email": valid_email, "password": valid_password}
    )
    assert response.status_code == 200


def test_sign_up_invalid_email(client, valid_password):
    response = client.post(
        "/sign-up", json={"email": "user", "password": valid_password}
    )
    assert response.status_code == 422


def test_sign_up_invalid_password(client, valid_email):
    response = client.post("/sign-up", json={"email": valid_email, "password": "weak"})
    assert response.status_code == 422


def test_sign_in_success(client, valid_email, valid_password):
    sign_up_or_in_request = {"email": valid_email, "password": valid_password}
    sign_up_response = client.post("/sign-up", json=sign_up_or_in_request)
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/sign-in", json=sign_up_or_in_request)
    assert sign_in_response.status_code == 200


def test_sign_in_invalid_email(client, valid_password):
    response = client.post(
        "/sign-in/", json={"email": "user", "password": valid_password}
    )
    assert response.status_code == 422


def test_sign_in_user_not_found(client, valid_email, valid_password):
    response = client.post(
        "/sign-in/", json={"email": valid_email, "password": valid_password}
    )
    assert response.status_code == 404


def test_sign_in_incorrect_password(client, valid_email, valid_password):
    sign_up_response = client.post(
        "/sign-up", json={"email": valid_email, "password": valid_password}
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/sign-in", json={"email": valid_email, "password": "Wxyz@1234"}
    )
    assert sign_in_response.status_code == 401


def test_get_user(client, valid_email, valid_password):
    sign_up_or_in_request = {"email": valid_email, "password": valid_password}
    sign_up_response = client.post("/sign-up", json=sign_up_or_in_request)
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/sign-in", json=sign_up_or_in_request)
    assert sign_in_response.status_code == 200
    sign_in_response = sign_in_response.json()
    get_user_response = client.get(
        "/user",
        headers={
            "X-Sherwood-Authorization": (
                sign_in_response["token_type"] + " " + sign_in_response["access_token"]
            )
        },
    )
    assert get_user_response.status_code == 200
    assert get_user_response.json() == {
        "id": 1,
        "email": valid_email,
        "display_name": None,
        "is_verified": False,
        "portfolio": {
            "id": 1,
            "cash": 0.0,
            "holdings": [],
            "ownership": [],
        },
    }


def test_get_user_missing_authorization_header(client):
    get_user_response = client.get("/user")
    assert get_user_response.status_code == 401


def test_deposit_cash_success(client, valid_email, valid_password):
    sign_up_or_in_request = {"email": valid_email, "password": valid_password}
    sign_up_response = client.post("/sign-up", json=sign_up_or_in_request)
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/sign-in", json=sign_up_or_in_request)
    assert sign_in_response.status_code == 200
    sign_in_response = sign_in_response.json()
    headers = {
        "X-Sherwood-Authorization": (
            sign_in_response["token_type"] + " " + sign_in_response["access_token"]
        )
    }
    deposit_response = client.post("/deposit", headers=headers, json={"dollars": 1})
    assert deposit_response.status_code == 200
    get_user_response = client.get("/user", headers=headers)
    assert get_user_response.status_code == 200
    assert get_user_response.json()["portfolio"]["cash"] == 1


def test_deposit_cash_missing_authorization_header(client):
    deposit_response = client.post("/deposit", json={"dollars": 1})
    assert deposit_response.status_code == 401


def test_deposit_cash_missing_user(client, fake_access_token):
    deposit_response = client.post(
        "/deposit",
        headers={"X-Sherwood-Authorization": f"Bearer {fake_access_token}"},
        json={"dollars": 1},
    )
    assert deposit_response.status_code == 404


def test_withdraw_cash_success(db, client, valid_email, valid_password):
    sign_up_or_in_request = {"email": valid_email, "password": valid_password}
    sign_up_response = client.post("/sign-up", json=sign_up_or_in_request)
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/sign-in", json=sign_up_or_in_request)
    assert sign_in_response.status_code == 200
    sign_in_response = sign_in_response.json()
    headers = {
        "X-Sherwood-Authorization": (
            sign_in_response["token_type"] + " " + sign_in_response["access_token"]
        )
    }
    deposit_response = client.post("/deposit", headers=headers, json={"dollars": 100})
    assert deposit_response.status_code == 200
    deposit_response = client.post("/withdraw", headers=headers, json={"dollars": 1})
    assert deposit_response.status_code == 200
    get_user_response = client.get("/user", headers=headers)
    assert get_user_response.status_code == 200
    assert get_user_response.json()["portfolio"]["cash"] == 99


def test_withdraw_insufficient_cash(client, valid_email, valid_password):
    sign_up_or_in_request = {"email": valid_email, "password": valid_password}
    sign_up_response = client.post("/sign-up", json=sign_up_or_in_request)
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/sign-in", json=sign_up_or_in_request)
    assert sign_in_response.status_code == 200
    sign_in_response = sign_in_response.json()
    headers = {
        "X-Sherwood-Authorization": (
            sign_in_response["token_type"] + " " + sign_in_response["access_token"]
        )
    }
    withdraw_response = client.post("/withdraw", headers=headers, json={"dollars": 1})
    assert withdraw_response.status_code == 400
    get_user_response = client.get("/user", headers=headers)
    assert get_user_response.status_code == 200
    assert get_user_response.json()["portfolio"]["cash"] == 0


def test_withdraw_cash_missing_authorization_header(client):
    withdraw_response = client.post("/withdraw", json={"dollars": 1})
    assert withdraw_response.status_code == 401


def test_withdraw_cash_missing_user(client, fake_access_token):
    withdraw_response = client.post(
        "/withdraw",
        headers={"X-Sherwood-Authorization": f"Bearer {fake_access_token}"},
        json={"dollars": 1},
    )
    assert withdraw_response.status_code == 404


def test_buy_portfolio_holding_success(client, valid_email, valid_password):
    sign_up_or_in_request = {"email": valid_email, "password": valid_password}
    sign_up_response = client.post("/sign-up", json=sign_up_or_in_request)
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/sign-in", json=sign_up_or_in_request)
    assert sign_in_response.status_code == 200
    sign_in_response = sign_in_response.json()
    headers = {
        "X-Sherwood-Authorization": (
            sign_in_response["token_type"] + " " + sign_in_response["access_token"]
        )
    }
    deposit_response = client.post("/deposit", headers=headers, json={"dollars": 100})
    assert deposit_response.status_code == 200
    buy_response = client.post(
        "/buy", headers=headers, json={"symbol": "AAA", "dollars": 50}
    )
    assert buy_response.status_code == 200
    get_user_response = client.get("/user", headers=headers)
    assert get_user_response.status_code == 200
    user = get_user_response.json()
    assert user["portfolio"]["cash"] == 50
    assert user["portfolio"]["holdings"] == [
        {"portfolio_id": 1, "symbol": "AAA", "cost": 50.0, "units": 50.0}
    ]
    assert user["portfolio"]["ownership"] == [
        {"portfolio_id": 1, "owner_id": 1, "cost": 50.0, "percent": 1.0}
    ]


def test_buy_portfolio_holding_insufficient_cash(client, valid_email, valid_password):
    sign_up_or_in_request = {"email": valid_email, "password": valid_password}
    sign_up_response = client.post("/sign-up", json=sign_up_or_in_request)
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/sign-in", json=sign_up_or_in_request)
    assert sign_in_response.status_code == 200
    sign_in_response = sign_in_response.json()
    buy_response = client.post(
        "/buy",
        headers={
            "X-Sherwood-Authorization": (
                sign_in_response["token_type"] + " " + sign_in_response["access_token"]
            )
        },
        json={"symbol": "AAA", "dollars": 1},
    )
    assert buy_response.status_code == 400
