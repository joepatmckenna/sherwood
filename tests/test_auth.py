from sherwood.auth import (
    decode_access_token,
    generate_access_token,
    _JWT_ISSUER,
)
from sherwood.models import create_user


def test_encode_and_decode_jwt_for_user(db, valid_email, valid_password):
    user = create_user(db, valid_email, valid_password)

    access_token = generate_access_token(user)
    payload = decode_access_token(access_token)

    assert payload["iss"] == _JWT_ISSUER
    assert payload["sub"] == str(user.id)
