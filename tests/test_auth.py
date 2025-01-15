import pytest
from sherwood.auth import (
    decode_access_token,
    generate_access_token,
    validate_password,
    ReasonPasswordInvalid,
    _JWT_ISSUER,
)
from sherwood.models import create_user


def test_encode_and_decode_jwt_for_user(
    db, valid_email, valid_display_name, valid_password
):
    user = create_user(db, valid_email, valid_display_name, valid_password)
    access_token = generate_access_token(user)
    payload = decode_access_token(access_token)
    assert payload["iss"] == _JWT_ISSUER
    assert payload["sub"] == str(user.id)


@pytest.mark.parametrize(
    ("password", "expected_reasons"),
    [
        pytest.param("A@a1A@a1", [], id="valid"),
        pytest.param("A@a1", [ReasonPasswordInvalid.TOO_SHORT.value], id="short"),
        pytest.param(
            30 * "A" + "a@1", [ReasonPasswordInvalid.TOO_LONG.value], id="long"
        ),
        pytest.param(
            "Aa@1 Aa@1", [ReasonPasswordInvalid.CONTAINS_SPACE.value], id="space"
        ),
        pytest.param(
            "AA@1AA@1", [ReasonPasswordInvalid.MISSING_LOWERCASE.value], id="lower"
        ),
        pytest.param(
            "aa@1aa@1", [ReasonPasswordInvalid.MISSING_UPPERCASE.value], id="upper"
        ),
        pytest.param(
            "Aa@@Aa@@", [ReasonPasswordInvalid.MISSING_DIGIT.value], id="digit"
        ),
        pytest.param(
            "Aa11Aa11", [ReasonPasswordInvalid.MISSING_SPECIAL.value], id="special"
        ),
        pytest.param(
            "a ",
            [
                ReasonPasswordInvalid.TOO_SHORT.value,
                ReasonPasswordInvalid.CONTAINS_SPACE.value,
                ReasonPasswordInvalid.MISSING_UPPERCASE.value,
                ReasonPasswordInvalid.MISSING_DIGIT.value,
                ReasonPasswordInvalid.MISSING_SPECIAL.value,
            ],
            id="weak",
        ),
        pytest.param(
            "password",
            [
                ReasonPasswordInvalid.MISSING_UPPERCASE.value,
                ReasonPasswordInvalid.MISSING_DIGIT.value,
                ReasonPasswordInvalid.MISSING_SPECIAL.value,
            ],
            id="common",
        ),
    ],
)
def test_validate_password(password, expected_reasons):
    reasons = validate_password(password)
    assert reasons == expected_reasons
