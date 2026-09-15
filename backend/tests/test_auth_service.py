import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.services.auth_service import ALGORITHM, create_access_token, decode_access_token, hash_password, verify_password


def test_hash_password_round_trips_with_verify():
    hashed = hash_password("correct-password")
    assert verify_password("correct-password", hashed)


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)


def test_hash_password_never_stores_the_plaintext():
    hashed = hash_password("correct-password")
    assert "correct-password" not in hashed


def test_create_and_decode_access_token_round_trips():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, "admin")

    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "admin"


def test_decode_access_token_rejects_a_tampered_token():
    token = create_access_token(uuid.uuid4(), "viewer")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(tampered)


def test_decode_access_token_rejects_a_token_signed_with_a_different_secret():
    forged = jwt.encode({"sub": str(uuid.uuid4()), "role": "admin"}, "wrong-secret", algorithm=ALGORITHM)

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(forged)


def test_decode_access_token_rejects_an_expired_token():
    expired = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "viewer", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm=ALGORITHM,
    )

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(expired)
