from sherwood.broker import STARTING_BALANCE


def test_sign_up_success(client, valid_email, valid_display_name, valid_password):
    response = client.post(
        "/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert response.status_code == 200
    assert response.json()["redirect_url"] == "/sherwood/sign-in.html"


def test_sign_up_invalid_email(client, valid_password):
    response = client.post(
        "/sign-up", json={"email": "user", "password": valid_password}
    )
    assert response.status_code == 422


def test_sign_up_invalid_password(client, valid_email):
    response = client.post("/sign-up", json={"email": valid_email, "password": "weak"})
    assert response.status_code == 422


def test_sign_in_success(client, valid_email, valid_display_name, valid_password):
    sign_up_response = client.post(
        "/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/sign-in", json={"email": valid_email, "password": valid_password}
    )
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


def test_sign_in_incorrect_password(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/sign-in", json={"email": valid_email, "password": "Wxyz@1234"}
    )
    assert sign_in_response.status_code == 401


def test_get_user(client, valid_email, valid_display_name, valid_password):
    sign_up_response = client.post(
        "/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/sign-in", json={"email": valid_email, "password": valid_password}
    )
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
        "display_name": valid_display_name,
        "is_verified": False,
        "portfolio": {
            "id": 1,
            "cash": STARTING_BALANCE,
            "holdings": [],
            "ownership": [],
        },
    }


def test_get_user_missing_authorization_header(client):
    get_user_response = client.get("/user")
    assert get_user_response.status_code == 401


def test_buy_portfolio_holding_success(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200
    sign_in_response = sign_in_response.json()
    headers = {
        "X-Sherwood-Authorization": (
            sign_in_response["token_type"] + " " + sign_in_response["access_token"]
        )
    }
    buy_response = client.post(
        "/buy", headers=headers, json={"symbol": "AAA", "dollars": 50}
    )
    assert buy_response.status_code == 200
    get_user_response = client.get("/user", headers=headers)
    assert get_user_response.status_code == 200
    user = get_user_response.json()
    assert user["portfolio"]["cash"] == STARTING_BALANCE - 50
    assert user["portfolio"]["holdings"] == [
        {"portfolio_id": 1, "symbol": "AAA", "cost": 50, "units": 50}
    ]
    assert user["portfolio"]["ownership"] == [
        {"portfolio_id": 1, "owner_id": 1, "cost": 50, "percent": 1}
    ]


def test_buy_portfolio_holding_insufficient_cash(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200
    sign_in_response = sign_in_response.json()
    buy_response = client.post(
        "/buy",
        headers={
            "X-Sherwood-Authorization": (
                sign_in_response["token_type"] + " " + sign_in_response["access_token"]
            )
        },
        json={"symbol": "AAA", "dollars": STARTING_BALANCE + 1},
    )
    assert buy_response.status_code == 400


def test_sell_portfolio_holding_success(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200
    sign_in_response = sign_in_response.json()
    headers = {
        "X-Sherwood-Authorization": (
            sign_in_response["token_type"] + " " + sign_in_response["access_token"]
        )
    }
    buy_response = client.post(
        "/buy", headers=headers, json={"symbol": "AAA", "dollars": 50}
    )
    assert buy_response.status_code == 200
    sell_response = client.post(
        "/sell", headers=headers, json={"symbol": "AAA", "dollars": 25}
    )
    assert sell_response.status_code == 200
    get_user_response = client.get("/user", headers=headers)
    assert get_user_response.status_code == 200
    user = get_user_response.json()
    assert user["portfolio"]["cash"] == STARTING_BALANCE - 25
    assert user["portfolio"]["holdings"] == [
        {"portfolio_id": 1, "symbol": "AAA", "cost": 25, "units": 25}
    ]
    assert user["portfolio"]["ownership"] == [
        {"portfolio_id": 1, "owner_id": 1, "cost": 25, "percent": 1}
    ]


def test_sell_portfolio_holding_insufficient_holdings(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200
    sign_in_response = sign_in_response.json()
    headers = {
        "X-Sherwood-Authorization": (
            sign_in_response["token_type"] + " " + sign_in_response["access_token"]
        )
    }
    buy_response = client.post(
        "/buy", headers=headers, json={"symbol": "AAA", "dollars": 50}
    )
    assert buy_response.status_code == 200
    sell_response = client.post(
        "/sell", headers=headers, json={"symbol": "AAA", "dollars": 100}
    )
    assert sell_response.status_code == 400


def test_invest_in_portfolio_success(
    client, valid_emails, valid_display_name, valid_password
):
    sign_up_requests = [
        {
            "email": valid_emails[0],
            "display_name": valid_display_name + "1",
            "password": valid_password,
        },
        {
            "email": valid_emails[1],
            "display_name": valid_display_name + "2",
            "password": valid_password,
        },
    ]
    sign_in_requests = [
        {"email": valid_emails[0], "password": valid_password},
        {"email": valid_emails[1], "password": valid_password},
    ]
    sign_up_response = client.post("/sign-up", json=sign_up_requests[0])
    assert sign_up_response.status_code == 200
    sign_up_response = client.post("/sign-up", json=sign_up_requests[1])
    assert sign_up_response.status_code == 200
    _header = lambda t: {"X-Sherwood-Authorization": f"Bearer {t}"}
    headers = []
    sign_in_response = client.post("/sign-in", json=sign_in_requests[0])
    assert sign_in_response.status_code == 200
    headers.append(_header(sign_in_response.json()["access_token"]))
    sign_in_response = client.post("/sign-in", json=sign_in_requests[1])
    assert sign_in_response.status_code == 200
    headers.append(_header(sign_in_response.json()["access_token"]))
    buy_response = client.post(
        "/buy", headers=headers[0], json={"symbol": "AAA", "dollars": 100}
    )
    assert buy_response.status_code == 200
    buy_response = client.post(
        "/buy", headers=headers[0], json={"symbol": "BBB", "dollars": 100}
    )
    assert buy_response.status_code == 200
    invest_response = client.post(
        "/invest", headers=headers[1], json={"investee_portfolio_id": 1, "dollars": 50}
    )
    assert invest_response.status_code == 200

    users = []
    get_user_response = client.get("/user", headers=headers[0])
    assert get_user_response.status_code == 200
    users.append(get_user_response.json())
    get_user_response = client.get("/user", headers=headers[1])
    assert get_user_response.status_code == 200
    users.append(get_user_response.json())

    assert users[0] == {
        "id": 1,
        "email": "user0@web.com",
        "display_name": valid_display_name + "1",
        "is_verified": False,
        "portfolio": {
            "id": 1,
            "cash": STARTING_BALANCE - 200,
            "holdings": [
                {"portfolio_id": 1, "symbol": "AAA", "cost": 100.0, "units": 125.0},
                {"portfolio_id": 1, "symbol": "BBB", "cost": 100.0, "units": 62.5},
            ],
            "ownership": [
                {"portfolio_id": 1, "owner_id": 1, "cost": 200.0, "percent": 0.8},
                {"portfolio_id": 1, "owner_id": 2, "cost": 50.0, "percent": 0.2},
            ],
        },
    }

    assert users[1] == {
        "id": 2,
        "email": "user1@web.com",
        "display_name": valid_display_name + "2",
        "is_verified": False,
        "portfolio": {
            "id": 2,
            "cash": STARTING_BALANCE - 50,
            "holdings": [],
            "ownership": [],
        },
    }


def test_self_invest_in_portfolio(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200
    headers = {
        "X-Sherwood-Authorization": f"Bearer {sign_in_response.json()['access_token']}"
    }
    invest_response = client.post(
        "/invest", headers=headers, json={"investee_portfolio_id": 1, "dollars": 1}
    )
    assert invest_response.status_code == 422


def test_invest_in_portfolio_insufficient_cash(
    client, valid_emails, valid_display_name, valid_password
):
    sign_up_requests = [
        {
            "email": valid_emails[0],
            "display_name": valid_display_name + "1",
            "password": valid_password,
        },
        {
            "email": valid_emails[1],
            "display_name": valid_display_name + "2",
            "password": valid_password,
        },
    ]
    sign_in_requests = [
        {"email": valid_emails[0], "password": valid_password},
        {"email": valid_emails[1], "password": valid_password},
    ]

    sign_up_response = client.post("/sign-up", json=sign_up_requests[0])
    assert sign_up_response.status_code == 200
    sign_up_response = client.post("/sign-up", json=sign_up_requests[1])
    assert sign_up_response.status_code == 200
    _header = lambda t: {"X-Sherwood-Authorization": f"Bearer {t}"}
    headers = []
    sign_in_response = client.post("/sign-in", json=sign_in_requests[0])
    assert sign_in_response.status_code == 200
    headers.append(_header(sign_in_response.json()["access_token"]))
    sign_in_response = client.post("/sign-in", json=sign_in_requests[1])
    assert sign_in_response.status_code == 200
    headers.append(_header(sign_in_response.json()["access_token"]))
    buy_response = client.post(
        "/buy", headers=headers[0], json={"symbol": "AAA", "dollars": 1}
    )
    assert buy_response.status_code == 200
    invest_response = client.post(
        "/invest",
        headers=headers[1],
        json={"investee_portfolio_id": 1, "dollars": STARTING_BALANCE + 1},
    )
    assert invest_response.status_code == 400


def test_invest_in_portfolio_insufficient_investee_holdings(
    client, valid_emails, valid_display_name, valid_password
):
    sign_up_requests = [
        {
            "email": valid_emails[0],
            "display_name": valid_display_name + "1",
            "password": valid_password,
        },
        {
            "email": valid_emails[1],
            "display_name": valid_display_name + "2",
            "password": valid_password,
        },
    ]
    sign_in_requests = [
        {"email": valid_emails[0], "password": valid_password},
        {"email": valid_emails[1], "password": valid_password},
    ]
    sign_up_response = client.post("/sign-up", json=sign_up_requests[0])
    assert sign_up_response.status_code == 200
    sign_up_response = client.post("/sign-up", json=sign_up_requests[1])
    assert sign_up_response.status_code == 200
    _header = lambda t: {"X-Sherwood-Authorization": f"Bearer {t}"}
    headers = []
    sign_in_response = client.post("/sign-in", json=sign_in_requests[0])
    assert sign_in_response.status_code == 200
    headers.append(_header(sign_in_response.json()["access_token"]))
    sign_in_response = client.post("/sign-in", json=sign_in_requests[1])
    assert sign_in_response.status_code == 200
    headers.append(_header(sign_in_response.json()["access_token"]))
    buy_response = client.post(
        "/buy", headers=headers[0], json={"symbol": "AAA", "dollars": 0.009}
    )
    assert buy_response.status_code == 200
    invest_response = client.post(
        "/invest", headers=headers[1], json={"investee_portfolio_id": 1, "dollars": 1}
    )
    print(invest_response.json())
    assert invest_response.status_code == 400


def test_invest_in_portfolio_missing_investee_ownership(
    client, valid_emails, valid_display_name, valid_password
):
    sign_up_requests = [
        {
            "email": valid_emails[0],
            "display_name": valid_display_name + "1",
            "password": valid_password,
        },
        {
            "email": valid_emails[1],
            "display_name": valid_display_name + "2",
            "password": valid_password,
        },
    ]
    sign_in_requests = [
        {"email": valid_emails[0], "password": valid_password},
        {"email": valid_emails[1], "password": valid_password},
    ]
    sign_up_response = client.post("/sign-up", json=sign_up_requests[0])
    assert sign_up_response.status_code == 200
    sign_up_response = client.post("/sign-up", json=sign_up_requests[1])
    assert sign_up_response.status_code == 200
    _header = lambda t: {"X-Sherwood-Authorization": f"Bearer {t}"}
    headers = []
    sign_in_response = client.post("/sign-in", json=sign_in_requests[0])
    assert sign_in_response.status_code == 200
    headers.append(_header(sign_in_response.json()["access_token"]))
    sign_in_response = client.post("/sign-in", json=sign_in_requests[1])
    assert sign_in_response.status_code == 200
    headers.append(_header(sign_in_response.json()["access_token"]))
    invest_response = client.post(
        "/invest", headers=headers[1], json={"investee_portfolio_id": 1, "dollars": 1}
    )
    print(invest_response.json())
    assert invest_response.status_code == 500


def test_divest_from_portfolio_success(
    client, valid_emails, valid_display_name, valid_password
):
    sign_up_requests = [
        {
            "email": valid_emails[0],
            "display_name": valid_display_name + "1",
            "password": valid_password,
        },
        {
            "email": valid_emails[1],
            "display_name": valid_display_name + "2",
            "password": valid_password,
        },
    ]
    sign_in_requests = [
        {"email": valid_emails[0], "password": valid_password},
        {"email": valid_emails[1], "password": valid_password},
    ]
    sign_up_response = client.post("/sign-up", json=sign_up_requests[0])
    assert sign_up_response.status_code == 200
    sign_up_response = client.post("/sign-up", json=sign_up_requests[1])
    assert sign_up_response.status_code == 200
    _header = lambda t: {"X-Sherwood-Authorization": f"Bearer {t}"}
    headers = []
    sign_in_response = client.post("/sign-in", json=sign_in_requests[0])
    assert sign_in_response.status_code == 200
    headers.append(_header(sign_in_response.json()["access_token"]))
    sign_in_response = client.post("/sign-in", json=sign_in_requests[1])
    assert sign_in_response.status_code == 200
    headers.append(_header(sign_in_response.json()["access_token"]))
    buy_response = client.post(
        "/buy", headers=headers[0], json={"symbol": "AAA", "dollars": 100}
    )
    assert buy_response.status_code == 200
    buy_response = client.post(
        "/buy", headers=headers[0], json={"symbol": "BBB", "dollars": 100}
    )
    assert buy_response.status_code == 200
    invest_response = client.post(
        "/invest", headers=headers[1], json={"investee_portfolio_id": 1, "dollars": 51}
    )
    assert invest_response.status_code == 200
    divest_response = client.post(
        "/divest", headers=headers[1], json={"investee_portfolio_id": 1, "dollars": 1}
    )
    assert divest_response.status_code == 200

    users = []
    get_user_response = client.get("/user", headers=headers[0])
    assert get_user_response.status_code == 200
    users.append(get_user_response.json())
    get_user_response = client.get("/user", headers=headers[1])
    assert get_user_response.status_code == 200
    users.append(get_user_response.json())

    assert users[0] == {
        "id": 1,
        "email": "user0@web.com",
        "display_name": valid_display_name + "1",
        "is_verified": False,
        "portfolio": {
            "id": 1,
            "cash": STARTING_BALANCE - 200,
            "holdings": [
                {"portfolio_id": 1, "symbol": "AAA", "cost": 100.0, "units": 125.0},
                {"portfolio_id": 1, "symbol": "BBB", "cost": 100.0, "units": 62.5},
            ],
            "ownership": [
                {"portfolio_id": 1, "owner_id": 1, "cost": 200.0, "percent": 0.8},
                {"portfolio_id": 1, "owner_id": 2, "cost": 50.0, "percent": 0.2},
            ],
        },
    }

    assert users[1] == {
        "id": 2,
        "email": "user1@web.com",
        "display_name": valid_display_name + "2",
        "is_verified": False,
        "portfolio": {
            "id": 2,
            "cash": STARTING_BALANCE - 50,
            "holdings": [],
            "ownership": [],
        },
    }
