import pytest
from httpx import ASGITransport, AsyncClient
from services.auth.src.database import init_db
from services.auth.src.main import app


@pytest.mark.asyncio
async def test_auth_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "auth-service"


@pytest.mark.asyncio
async def test_auth_registration_and_login_flow():
    await init_db()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Register a new user
        reg_payload = {
            "username": "john_doe",
            "email": "john@tenant-alpha.com",
            "password": "Password123!",
            "tenant_id": "tenant-alpha",
            "role": "user",
        }
        reg_resp = await client.post("/auth/register", json=reg_payload)
        assert reg_resp.status_code == 201
        reg_data = reg_resp.json()
        assert reg_data["username"] == "john_doe"
        assert reg_data["email"] == "john@tenant-alpha.com"
        assert reg_data["tenant_id"] == "tenant-alpha"
        assert "id" in reg_data
        assert "hashed_password" not in reg_data

        # 2. Attempt duplicate registration
        dup_resp = await client.post("/auth/register", json=reg_payload)
        assert dup_resp.status_code == 409

        # 3. Successful Login
        login_resp = await client.post(
            "/auth/login",
            json={"username": "john_doe", "password": "Password123!"},
        )
        assert login_resp.status_code == 200
        token_data = login_resp.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        assert token_data["expires_in"] > 0
        token = token_data["access_token"]

        # 4. Invalid Login
        invalid_login = await client.post(
            "/auth/login",
            json={"username": "john_doe", "password": "WrongPassword!"},
        )
        assert invalid_login.status_code == 401

        # 5. Get current user profile with token
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = await client.get("/auth/me", headers=headers)
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["username"] == "john_doe"
        assert me_data["tenant_id"] == "tenant-alpha"

        # 6. Verify token endpoint
        verify_resp = await client.get("/auth/verify", headers=headers)
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert verify_data["username"] == "john_doe"
        assert verify_data["tenant_id"] == "tenant-alpha"

        # 7. Unauthenticated request to /auth/me
        unauth_resp = await client.get("/auth/me")
        assert unauth_resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_rate_limiting_enforcement():
    from services.auth.src.routers.auth import auth_rate_limiter

    # Set temporary low limit for test
    orig_max = auth_rate_limiter.max_requests
    auth_rate_limiter.max_requests = 2
    auth_rate_limiter.reset()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            login_data = {"username": "rate_user", "password": "Password123!"}
            # Request 1 & 2 pass through to auth check (401 because user doesn't exist)
            resp1 = await client.post("/auth/login", json=login_data)
            resp2 = await client.post("/auth/login", json=login_data)
            assert resp1.status_code == 401
            assert resp2.status_code == 401

            # Request 3 is blocked by rate limiter with 429
            resp3 = await client.post("/auth/login", json=login_data)
            assert resp3.status_code == 429
            assert "Too many requests" in resp3.json()["detail"]
            assert "retry-after" in resp3.headers
    finally:
        auth_rate_limiter.max_requests = orig_max
        auth_rate_limiter.reset()

