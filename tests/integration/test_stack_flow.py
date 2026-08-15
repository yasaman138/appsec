import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_end_to_end_cross_service_happy_path(
    auth_client: AsyncClient, api_client: AsyncClient
):
    """
    End-to-end integration test verifying baseline happy path across services:
    1. User registration on Auth Service
    2. Authentication & JWT token issuance on Auth Service
    3. Token verification and identity retrieval on Auth Service
    4. Authenticated tenant record creation on Core Resource API Service
    5. Cache-backed record retrieval on Core Resource API Service
    6. Tenant isolation validation across distinct accounts
    """
    # ----------------------------------------------------
    # Step 1: Register Tenant A User on Auth Service
    # ----------------------------------------------------
    reg_response_a = await auth_client.post(
        "/auth/register",
        json={
            "username": "alice_corp",
            "email": "alice@corp-a.com",
            "password": "SecurePassword2026!",
            "tenant_id": "corp-a",
            "role": "admin",
        },
    )
    assert reg_response_a.status_code == 201
    user_a = reg_response_a.json()
    assert user_a["username"] == "alice_corp"
    assert user_a["tenant_id"] == "corp-a"

    # ----------------------------------------------------
    # Step 2: Login Tenant A User to Obtain JWT
    # ----------------------------------------------------
    login_response_a = await auth_client.post(
        "/auth/login",
        json={"username": "alice_corp", "password": "SecurePassword2026!"},
    )
    assert login_response_a.status_code == 200
    token_a = login_response_a.json()["access_token"]
    assert len(token_a) > 20

    auth_headers_a = {"Authorization": f"Bearer {token_a}"}

    # ----------------------------------------------------
    # Step 3: Verify Profile on Auth Service
    # ----------------------------------------------------
    me_resp_a = await auth_client.get("/auth/me", headers=auth_headers_a)
    assert me_resp_a.status_code == 200
    assert me_resp_a.json()["id"] == user_a["id"]

    # ----------------------------------------------------
    # Step 4: Create Resource on Core API Service
    # ----------------------------------------------------
    record_create_payload = {
        "title": "Corporate Q1 Financial Summary",
        "content": "Gross revenue up 35% YoY; Operating margin 22%.",
        "is_sensitive": True,
    }
    create_resp = await api_client.post(
        "/records",
        json=record_create_payload,
        headers=auth_headers_a,
    )
    assert create_resp.status_code == 201
    record_a = create_resp.json()
    record_id = record_a["id"]
    assert record_a["title"] == "Corporate Q1 Financial Summary"
    assert record_a["tenant_id"] == "corp-a"
    assert record_a["owner_id"] == user_a["id"]

    # ----------------------------------------------------
    # Step 5: Read Resource from Core API Service
    # ----------------------------------------------------
    get_resp = await api_client.get(f"/records/{record_id}", headers=auth_headers_a)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == record_id
    assert get_resp.json()["content"] == "Gross revenue up 35% YoY; Operating margin 22%."

    # ----------------------------------------------------
    # Step 6: Register Tenant B and Assert Isolation
    # ----------------------------------------------------
    reg_response_b = await auth_client.post(
        "/auth/register",
        json={
            "username": "bob_enterprise",
            "email": "bob@corp-b.com",
            "password": "SecurePassword2026!",
            "tenant_id": "corp-b",
            "role": "user",
        },
    )
    assert reg_response_b.status_code == 201

    login_response_b = await auth_client.post(
        "/auth/login",
        json={"username": "bob_enterprise", "password": "SecurePassword2026!"},
    )
    assert login_response_b.status_code == 200
    token_b = login_response_b.json()["access_token"]
    auth_headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant B attempts to read Tenant A's record -> Expect 404
    cross_tenant_get = await api_client.get(
        f"/records/{record_id}", headers=auth_headers_b
    )
    assert cross_tenant_get.status_code == 404

    # Tenant B list -> Expect empty list
    list_b = await api_client.get("/records", headers=auth_headers_b)
    assert list_b.status_code == 200
    assert list_b.json()["total"] == 0
    assert len(list_b.json()["items"]) == 0
