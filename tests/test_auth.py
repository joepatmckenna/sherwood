from sherwood.auth import decode_jwt_for_user, generate_jwt_for_user, _JWT_ISSUER
from sherwood.models import create_user


def test_encode_and_decode_jwt_for_user(db, valid_email, valid_password):
    user = create_user(db, valid_email, valid_password)

    jwt = generate_jwt_for_user(user)
    payload = decode_jwt_for_user(jwt, user.email)

    assert payload["iss"] == _JWT_ISSUER
    assert payload["sub"] == str(user.id)
    assert payload["aud"] == user.email
