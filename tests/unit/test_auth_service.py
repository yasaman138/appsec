import pytest
from services.auth.src.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from services.auth.src.schemas.auth import TokenPayload


def test_password_hashing_and_verification():
    password = "SuperSecurePassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_creation_and_decoding():
    payload = {
        "sub": "user-uuid-1234",
        "username": "alice",
        "email": "alice@tenant-a.com",
        "tenant_id": "tenant-a",
        "role": "admin",
    }
    token = create_access_token(payload)
    assert isinstance(token, str)

    decoded = decode_access_token(token)
    assert isinstance(decoded, TokenPayload)
    assert decoded.sub == "user-uuid-1234"
    assert decoded.username == "alice"
    assert decoded.email == "alice@tenant-a.com"
    assert decoded.tenant_id == "tenant-a"
    assert decoded.role == "admin"
