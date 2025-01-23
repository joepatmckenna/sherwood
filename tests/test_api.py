from sherwood.broker import STARTING_BALANCE


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


def test_sign_up_invalid_password(client, valid_email):
    response = client.post(
        "/api/sign-up", json={"email": valid_email, "password": "weak"}
    )
    assert response.status_code == 422


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
    assert user["portfolio"]["cash"] == STARTING_BALANCE - 50
    assert user["portfolio"]["holdings"] == [
        {
            "portfolio_id": 1,
            "symbol": "AAA",
            "cost": 50,
            "units": 50,
        }
    ]
    assert user["portfolio"]["ownership"] == [
        {"portfolio_id": 1, "owner_id": 1, "cost": 50, "percent": 1}
    ]


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
    assert sell_response.status_code == 200
    get_user_response = client.get("/api/user")
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


def test_invest_in_portfolio_insufficient_investee_holdings(
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
    buy_response = client.post("/api/buy", json={"symbol": "AAA", "dollars": 0.009})
    assert buy_response.status_code == 200

    sign_up_response = client.post("/api/sign-up", json=sign_up_requests[1])
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/api/sign-in", json=sign_in_requests[1])
    assert sign_in_response.status_code == 200
    invest_response = client.post(
        "/api/invest", json={"investee_portfolio_id": 1, "dollars": 1}
    )
    assert invest_response.status_code == 400


def test_invest_in_portfolio_missing_investee_ownership(
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

    sign_up_response = client.post("/api/sign-up", json=sign_up_requests[1])
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/api/sign-in", json=sign_in_requests[1])
    assert sign_in_response.status_code == 200
    invest_response = client.post(
        "/api/invest", json={"investee_portfolio_id": 1, "dollars": 1}
    )
    assert invest_response.status_code == 500


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
        json={"top_k": 10, "sort_by": "lifetime_return"},
    )
    print(leaderboard_response.json())
    assert leaderboard_response.status_code == 200
