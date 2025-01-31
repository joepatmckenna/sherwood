from sherwood.registrar import STARTING_BALANCE


def test_sign_up_success(client, valid_email, valid_display_name, valid_password):
    response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert response.status_code == 200
    assert response.json()["redirect_url"] == "/sherwood/sign-in"


def test_sign_up_invalid_email(client, valid_password):
    response = client.post(
        "/api/sign-up", json={"email": "user", "password": valid_password}
    )
    assert response.status_code == 422


def test_sign_up_invalid_password(client, valid_display_name, valid_email):
    response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": "weak",
        },
    )
    assert response.status_code == 422


def test_sign_up_duplicate_email(
    client, valid_email, valid_display_names, valid_password
):
    response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_names[0],
            "password": valid_password,
        },
    )
    assert response.status_code == 200
    response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_names[1],
            "password": valid_password,
        },
    )
    assert response.status_code == 409


def test_sign_up_duplicate_display_name(
    client, valid_email, valid_display_name, valid_password
):
    response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name.lower(),
            "password": valid_password,
        },
    )
    assert response.status_code == 200
    response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name.upper(),
            "password": valid_password,
        },
    )
    assert response.status_code == 409


def test_sign_in_success(client, valid_email, valid_display_name, valid_password):
    sign_up_response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/api/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200


def test_sign_in_invalid_email(client, valid_password):
    response = client.post(
        "/api/sign-in", json={"email": "user", "password": valid_password}
    )
    assert response.status_code == 422


def test_sign_in_user_not_found(client, valid_email, valid_password):
    response = client.post(
        "/api/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert response.status_code == 404


def test_sign_in_incorrect_password(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/api/sign-in", json={"email": valid_email, "password": "Wxyz@1234"}
    )
    assert sign_in_response.status_code == 401


def test_get_user_success(client, valid_email, valid_display_name, valid_password):
    sign_up_response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/api/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200
    get_user_response = client.get("/api/user")
    print(get_user_response.json())
    assert get_user_response.status_code == 200


def test_get_user_missing_authorization_cookie(client):
    get_user_response = client.get("/api/user")
    assert get_user_response.status_code == 401


def test_get_user_by_id(client, valid_email, valid_display_name, valid_password):
    sign_up_response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    get_user_by_id_response = client.get("/api/user/1")
    assert get_user_by_id_response.status_code == 200


def test_buy_portfolio_holding_success(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/api/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200
    buy_response = client.post("/api/buy", json={"symbol": "AAA", "dollars": 50})
    assert buy_response.status_code == 200
    get_user_response = client.get("/api/user")
    assert get_user_response.status_code == 200
    user = get_user_response.json()
    assert user["portfolio"]["holdings"][0]["symbol"] == "AAA"
    assert user["portfolio"]["holdings"][0]["cost"] == 50.0
    assert user["portfolio"]["holdings"][0]["units"] == 50.0
    assert user["portfolio"]["holdings"][1]["symbol"] == "USD"
    assert user["portfolio"]["holdings"][1]["cost"] == 9950.0
    assert user["portfolio"]["holdings"][1]["units"] == 9950.0
    assert user["portfolio"]["ownership"][0]["portfolio_id"] == 1
    assert user["portfolio"]["ownership"][0]["owner_id"] == 1
    assert user["portfolio"]["ownership"][0]["cost"] == 10000.0
    assert user["portfolio"]["ownership"][0]["percent"] == 1.0


def test_buy_portfolio_holding_insufficient_cash(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/api/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200
    buy_response = client.post(
        "/api/buy", json={"symbol": "AAA", "dollars": STARTING_BALANCE + 1}
    )
    assert buy_response.status_code == 400


def test_sell_portfolio_holding_success(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/api/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200
    buy_response = client.post("/api/buy", json={"symbol": "AAA", "dollars": 50})
    assert buy_response.status_code == 200
    sell_response = client.post("/api/sell", json={"symbol": "AAA", "dollars": 25})
    print(sell_response.json())
    assert sell_response.status_code == 200
    get_user_response = client.get("/api/user")
    assert get_user_response.status_code == 200
    user = get_user_response.json()
    assert user["portfolio"]["holdings"][0]["symbol"] == "AAA"
    assert user["portfolio"]["holdings"][0]["cost"] == 25.0
    assert user["portfolio"]["holdings"][0]["units"] == 25.0
    assert user["portfolio"]["holdings"][1]["symbol"] == "USD"
    assert user["portfolio"]["holdings"][1]["cost"] == 9975.0
    assert user["portfolio"]["holdings"][1]["units"] == 9975.0
    assert user["portfolio"]["ownership"][0]["portfolio_id"] == 1
    assert user["portfolio"]["ownership"][0]["owner_id"] == 1
    assert user["portfolio"]["ownership"][0]["cost"] == 10000.0
    assert user["portfolio"]["ownership"][0]["percent"] == 1.0


def test_sell_portfolio_holding_insufficient_holdings(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/api/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200
    buy_response = client.post("/api/buy", json={"symbol": "AAA", "dollars": 50})
    assert buy_response.status_code == 200
    sell_response = client.post("/api/sell", json={"symbol": "AAA", "dollars": 100})
    assert sell_response.status_code == 400


def test_invest_in_portfolio_success(
    client, valid_emails, valid_display_names, valid_password
):
    sign_up_requests = [
        {
            "email": valid_emails[0],
            "display_name": valid_display_names[0],
            "password": valid_password,
        },
        {
            "email": valid_emails[1],
            "display_name": valid_display_names[1],
            "password": valid_password,
        },
    ]
    sign_in_requests = [
        {"email": valid_emails[0], "password": valid_password},
        {"email": valid_emails[1], "password": valid_password},
    ]
    sign_up_response = client.post("/api/sign-up", json=sign_up_requests[0])
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/api/sign-in", json=sign_in_requests[0])
    assert sign_in_response.status_code == 200
    buy_response = client.post("/api/buy", json={"symbol": "AAA", "dollars": 100})
    assert buy_response.status_code == 200
    buy_response = client.post("/api/buy", json={"symbol": "BBB", "dollars": 100})
    assert buy_response.status_code == 200
    get_user_response = client.get("/api/user")
    assert get_user_response.status_code == 200

    sign_up_response = client.post("/api/sign-up", json=sign_up_requests[1])
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/api/sign-in", json=sign_in_requests[1])
    assert sign_in_response.status_code == 200
    invest_response = client.post(
        "/api/invest", json={"investee_portfolio_id": 1, "dollars": 50}
    )
    assert invest_response.status_code == 200
    get_user_response = client.get("/api/user")
    assert get_user_response.status_code == 200


def test_self_invest_in_portfolio(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/api/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200
    invest_response = client.post(
        "/api/invest", json={"investee_portfolio_id": 1, "dollars": 1}
    )
    assert invest_response.status_code == 422


def test_invest_in_portfolio_insufficient_cash(
    client, valid_emails, valid_display_names, valid_password
):
    sign_up_requests = [
        {
            "email": valid_emails[0],
            "display_name": valid_display_names[0],
            "password": valid_password,
        },
        {
            "email": valid_emails[1],
            "display_name": valid_display_names[1],
            "password": valid_password,
        },
    ]
    sign_in_requests = [
        {"email": valid_emails[0], "password": valid_password},
        {"email": valid_emails[1], "password": valid_password},
    ]

    sign_up_response = client.post("/api/sign-up", json=sign_up_requests[0])
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/api/sign-in", json=sign_in_requests[0])
    assert sign_in_response.status_code == 200
    buy_response = client.post("/api/buy", json={"symbol": "AAA", "dollars": 1})
    assert buy_response.status_code == 200

    sign_up_response = client.post("/api/sign-up", json=sign_up_requests[1])
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/api/sign-in", json=sign_in_requests[1])
    assert sign_in_response.status_code == 200
    invest_response = client.post(
        "/api/invest",
        json={"investee_portfolio_id": 1, "dollars": STARTING_BALANCE + 1},
    )
    assert invest_response.status_code == 400


def test_divest_from_portfolio_success(
    client, valid_emails, valid_display_names, valid_password
):
    sign_up_requests = [
        {
            "email": valid_emails[0],
            "display_name": valid_display_names[0],
            "password": valid_password,
        },
        {
            "email": valid_emails[1],
            "display_name": valid_display_names[1],
            "password": valid_password,
        },
    ]
    sign_in_requests = [
        {"email": valid_emails[0], "password": valid_password},
        {"email": valid_emails[1], "password": valid_password},
    ]
    sign_up_response = client.post("/api/sign-up", json=sign_up_requests[0])
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/api/sign-in", json=sign_in_requests[0])
    assert sign_in_response.status_code == 200
    buy_response = client.post("/api/buy", json={"symbol": "AAA", "dollars": 100})
    assert buy_response.status_code == 200
    buy_response = client.post("/api/buy", json={"symbol": "BBB", "dollars": 100})
    assert buy_response.status_code == 200

    sign_up_response = client.post("/api/sign-up", json=sign_up_requests[1])
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/api/sign-in", json=sign_in_requests[1])
    assert sign_in_response.status_code == 200
    invest_response = client.post(
        "/api/invest", json={"investee_portfolio_id": 1, "dollars": 51}
    )
    assert invest_response.status_code == 200
    divest_response = client.post(
        "/api/divest", json={"investee_portfolio_id": 1, "dollars": 1}
    )
    assert divest_response.status_code == 200
    get_user_response = client.get("/api/user")
    assert get_user_response.status_code == 200


def test_get_leaderboard_success(
    client, valid_email, valid_display_name, valid_password
):
    sign_up_response = client.post(
        "/api/sign-up",
        json={
            "email": valid_email,
            "display_name": valid_display_name,
            "password": valid_password,
        },
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/api/sign-in", json={"email": valid_email, "password": valid_password}
    )
    assert sign_in_response.status_code == 200
    buy_response = client.post("/api/buy", json={"symbol": "AAA", "dollars": 50})
    assert buy_response.status_code == 200

    leaderboard_response = client.post(
        "/api/leaderboard",
        json={
            "columns": [
                "lifetime_return",
                "average_daily_return",
                "assets_under_management",
            ],
            "sort_by": "lifetime_return",
            "top_k": 10,
        },
    )
    assert leaderboard_response.status_code == 200
    assert leaderboard_response.json() == {
        "rows": [
            {
                "user_id": 1,
                "user_display_name": "user",
                "portfolio_id": 1,
                "columns": {
                    "lifetime_return": 0.0,
                    "average_daily_return": 0.0,
                    "assets_under_management": 10000.0,
                },
            }
        ]
    }


# TODO
def test_get_portfolio_holdings_success():
    pass


# TODO
def test_get_portfolio_investors_success():
    pass


# TODO
def test_get_user_investments_success():
    pass
