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


def test_secret_key_entropy_validation():
    from services.auth.src.config import AuthSettings
    import pydantic

    # Short key should fail validation
    with pytest.raises(pydantic.ValidationError) as exc_info:
        AuthSettings(JWT_SECRET_KEY="short-weak-key")
    assert "at least 32 characters" in str(exc_info.value)


def test_production_secret_key_hardening():
    from services.auth.src.config import AuthSettings
    import pydantic

    # Default key in production mode must be rejected
    with pytest.raises(pydantic.ValidationError) as exc_info:
        AuthSettings(
            APP_ENV="production",
            JWT_SECRET_KEY="appsec-super-secret-key-change-in-production-2026",
        )
    assert "Default placeholder JWT_SECRET_KEY is strictly forbidden in production mode" in str(exc_info.value)

    # Strong custom key in production mode should pass
    prod_settings = AuthSettings(
        APP_ENV="production",
        JWT_SECRET_KEY="a-very-strong-and-cryptographically-random-production-key-9999",
    )
    assert prod_settings.APP_ENV == "production"
    assert "..." in prod_settings.get_masked_secret()

