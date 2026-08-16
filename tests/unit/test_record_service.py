import pytest
from datetime import datetime, timezone
import jwt
from services.api.src.config import settings
from services.api.src.models.record import Record
from services.api.src.schemas.record import RecordCreate, RecordResponse
from services.api.src.security import AuthenticatedUser


def test_record_model_instantiation():
    record = Record(
        id="rec-123",
        title="Confidential Report",
        content="Sensitive financial details",
        tenant_id="tenant-alpha",
        owner_id="user-456",
        is_sensitive=True,
    )
    assert record.id == "rec-123"
    assert record.title == "Confidential Report"
    assert record.tenant_id == "tenant-alpha"
    assert record.is_sensitive is True


def test_record_schema_validation():
    schema = RecordCreate(
        title="Project Roadmap",
        content="Q3 deliverables and milestones",
        is_sensitive=False,
    )
    assert schema.title == "Project Roadmap"
    assert schema.content == "Q3 deliverables and milestones"
    assert schema.is_sensitive is False


def test_jwt_security_claim_parsing():
    payload = {
        "sub": "user-789",
        "username": "bob",
        "email": "bob@tenant-beta.com",
        "tenant_id": "tenant-beta",
        "role": "editor",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    
    user = AuthenticatedUser(
        user_id=decoded["sub"],
        username=decoded["username"],
        email=decoded["email"],
        tenant_id=decoded["tenant_id"],
        role=decoded["role"],
    )
    assert user.user_id == "user-789"
    assert user.tenant_id == "tenant-beta"
    assert user.role == "editor"


@pytest.mark.asyncio
async def test_http_security_headers_present():
    from httpx import ASGITransport, AsyncClient
    from services.api.src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("x-xss-protection") == "1; mode=block"
        assert "max-age" in resp.headers.get("strict-transport-security", "")
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

