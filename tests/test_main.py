def test_sign_up_success(client, valid_email, valid_password):
    response = client.post(
        "/sign_up", json={"email": valid_email, "password": valid_password}
    )
    assert response.status_code == 200


def test_sign_up_invalid_email(client, valid_password):
    response = client.post(
        "/sign_up", json={"email": "user", "password": valid_password}
    )
    assert response.status_code == 422


def test_sign_up_invalid_password(client, valid_email):
    response = client.post("/sign_up", json={"email": valid_email, "password": "weak"})
    assert response.status_code == 400


def test_sign_in_success(client, valid_email, valid_password):
    json = {"email": valid_email, "password": valid_password}
    sign_up_response = client.post("/sign_up", json=json)
    assert sign_up_response.status_code == 200
    sign_in_response = client.post("/sign_in", json=json)
    assert sign_in_response.status_code == 200


def test_sign_in_invalid_email(client, valid_password):
    response = client.post(
        "/sign_in/", json={"email": "user", "password": valid_password}
    )
    assert response.status_code == 422


def test_sign_in_user_not_found(client, valid_email, valid_password):
    response = client.post(
        "/sign_in/", json={"email": valid_email, "password": valid_password}
    )
    assert response.status_code == 404


def test_sign_in_incorrect_password(client, valid_email, valid_password):
    sign_up_response = client.post(
        "/sign_up", json={"email": valid_email, "password": valid_password}
    )
    assert sign_up_response.status_code == 200
    sign_in_response = client.post(
        "/sign_in", json={"email": valid_email, "password": "Wxyz@1234"}
    )
    assert sign_in_response.status_code == 401


def test_get_authorized_user(client, valid_email, valid_password):
    expected = {
        "id": 1,
        "email": "user@web.com",
        "portfolio": {
            "id": 1,
            "cash": 0.0,
            "holdings": [],
            "ownership": [
                {"portfolio_id": 1, "owner_id": 1, "cost": 0.0, "percent": 1.0}
            ],
        },
    }

    sign_up_response = client.post(
        "/sign_up", json={"email": valid_email, "password": valid_password}
    )
    assert sign_up_response.status_code == 200

    get_authorized_user_response = client.get(
        "/user",
        headers={
            "User": valid_email,
            "Authorization": f"Bearer {sign_up_response.json()["jwt"]}",
        },
    )
    assert get_authorized_user_response.status_code == 200
    assert get_authorized_user_response.json() == expected
