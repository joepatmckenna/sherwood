import pytest
from sherwood.auth import (
    decode_access_token,
    generate_access_token,
    validate_password,
    ReasonPasswordInvalid,
    _JWT_ISSUER,
)
from sherwood.models import create_user


def test_encode_and_decode_jwt_for_user(db, valid_email, valid_password):
    user = create_user(db, valid_email, valid_password)
    access_token = generate_access_token(user)
    payload = decode_access_token(access_token)
    assert payload["iss"] == _JWT_ISSUER
    assert payload["sub"] == str(user.id)


@pytest.mark.parametrize(
    ("password", "expected_is_valid", "expected_reasons"),
    [
        pytest.param("A@a1A@a1", True, [], id="valid"),
        pytest.param(
            "A@a1",
            False,
            [ReasonPasswordInvalid.TOO_SHORT.value],
            id="too_short",
        ),
        pytest.param(
            30 * "A" + "a@1",
            False,
            [ReasonPasswordInvalid.TOO_LONG.value],
            id="too_long",
        ),
        pytest.param(
            "Aa@1 Aa@1",
            False,
            [ReasonPasswordInvalid.CONTAINS_SPACE.value],
            id="contains_space",
        ),
        pytest.param(
            "AA@1AA@1",
            False,
            [ReasonPasswordInvalid.MISSING_LOWERCASE.value],
            id="missing_lowercase",
        ),
        pytest.param(
            "aa@1aa@1",
            False,
            [ReasonPasswordInvalid.MISSING_UPPERCASE.value],
            id="missing_uppercase",
        ),
        pytest.param(
            "Aa@@Aa@@",
            False,
            [ReasonPasswordInvalid.MISSING_DIGIT.value],
            id="missing_digit",
        ),
        pytest.param(
            "Aa11Aa11",
            False,
            [ReasonPasswordInvalid.MISSING_SPECIAL.value],
            id="missing_special",
        ),
        pytest.param(
            "a ",
            False,
            [
                ReasonPasswordInvalid.TOO_SHORT.value,
                ReasonPasswordInvalid.CONTAINS_SPACE.value,
                ReasonPasswordInvalid.MISSING_UPPERCASE.value,
                ReasonPasswordInvalid.MISSING_DIGIT.value,
                ReasonPasswordInvalid.MISSING_SPECIAL.value,
            ],
            id="missing_special",
        ),
        pytest.param(
            "password",
            False,
            [
                ReasonPasswordInvalid.MISSING_UPPERCASE.value,
                ReasonPasswordInvalid.MISSING_DIGIT.value,
                ReasonPasswordInvalid.MISSING_SPECIAL.value,
            ],
            id="missing_special",
        ),
    ],
)
def test_validate_password(password, expected_is_valid, expected_reasons):
    is_valid, reasons = validate_password(password)
    assert is_valid == expected_is_valid
    assert reasons == expected_reasons
