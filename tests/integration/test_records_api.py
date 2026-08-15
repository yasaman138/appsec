import pytest
from httpx import ASGITransport, AsyncClient
from services.api.src.database import init_db
from services.api.src.main import app
from services.auth.src.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_records_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "core-api-service"


@pytest.mark.asyncio
async def test_records_crud_and_tenant_isolation():
    await init_db()

    # Generate test JWT tokens for two distinct tenants
    tenant_a_token = create_access_token({
        "sub": "user-a-1",
        "username": "alice",
        "email": "alice@tenant-a.com",
        "tenant_id": "tenant-a",
        "role": "admin",
    })
    tenant_b_token = create_access_token({
        "sub": "user-b-1",
        "username": "bob",
        "email": "bob@tenant-b.com",
        "tenant_id": "tenant-b",
        "role": "user",
    })

    headers_a = {"Authorization": f"Bearer {tenant_a_token}"}
    headers_b = {"Authorization": f"Bearer {tenant_b_token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Unauthenticated request must fail with 401
        unauth_resp = await client.get("/records")
        assert unauth_resp.status_code == 401

        # 2. Tenant A creates a record
        create_payload = {
            "title": "Tenant A Secret Plan",
            "content": "Confidential roadmap for tenant A",
            "is_sensitive": True,
        }
        create_resp = await client.post("/records", json=create_payload, headers=headers_a)
        assert create_resp.status_code == 201
        record_a = create_resp.json()
        record_a_id = record_a["id"]
        assert record_a["title"] == "Tenant A Secret Plan"
        assert record_a["tenant_id"] == "tenant-a"
        assert record_a["owner_id"] == "user-a-1"

        # 3. Tenant A gets their record (cache miss -> populate)
        get_resp = await client.get(f"/records/{record_a_id}", headers=headers_a)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == record_a_id

        # 4. Tenant A gets their record again (cache hit)
        get_resp_cached = await client.get(f"/records/{record_a_id}", headers=headers_a)
        assert get_resp_cached.status_code == 200
        assert get_resp_cached.json()["title"] == "Tenant A Secret Plan"

        # 5. Cross-tenant isolation check: Tenant B attempts to read Tenant A's record
        cross_tenant_resp = await client.get(f"/records/{record_a_id}", headers=headers_b)
        assert cross_tenant_resp.status_code == 404

        # 6. Tenant B lists records -> should see 0 records
        list_b_resp = await client.get("/records", headers=headers_b)
        assert list_b_resp.status_code == 200
        assert list_b_resp.json()["total"] == 0
        assert len(list_b_resp.json()["items"]) == 0

        # 7. Tenant A lists records -> should see 1 record
        list_a_resp = await client.get("/records", headers=headers_a)
        assert list_a_resp.status_code == 200
        assert list_a_resp.json()["total"] >= 1

        # 8. Tenant A updates their record
        update_payload = {"title": "Updated Tenant A Plan", "is_sensitive": False}
        update_resp = await client.put(f"/records/{record_a_id}", json=update_payload, headers=headers_a)
        assert update_resp.status_code == 200
        updated_data = update_resp.json()
        assert updated_data["title"] == "Updated Tenant A Plan"
        assert updated_data["is_sensitive"] is False

        # 9. Tenant A deletes their record
        del_resp = await client.delete(f"/records/{record_a_id}", headers=headers_a)
        assert del_resp.status_code == 204

        # 10. Subsequent GET returns 404
        post_del_get = await client.get(f"/records/{record_a_id}", headers=headers_a)
        assert post_del_get.status_code == 404
