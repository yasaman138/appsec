from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from services.auth.src.database import Base as AuthBase, get_db as get_auth_db
from services.auth.src.main import app as auth_app
from services.auth.src.services.auth_service import create_access_token
from services.api.src.database import Base as ApiBase, get_db as get_api_db
from services.api.src.main import app as api_app


# Test database setup with SQLite in-memory for fast and isolated test runs
TEST_AUTH_DB_URL = "sqlite+aiosqlite:///:memory:"
TEST_API_DB_URL = "sqlite+aiosqlite:///:memory:"

auth_test_engine = create_async_engine(TEST_AUTH_DB_URL, echo=False)
api_test_engine = create_async_engine(TEST_API_DB_URL, echo=False)

AuthTestSessionLocal = async_sessionmaker(
    bind=auth_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
ApiTestSessionLocal = async_sessionmaker(
    bind=api_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def prepare_databases():
    from services.auth.src.routers.auth import auth_rate_limiter
    from services.api.src.routers.integrations import webhook_rate_limiter

    auth_rate_limiter.reset()
    webhook_rate_limiter.reset()

    # Setup Auth DB tables
    async with auth_test_engine.begin() as conn:
        await conn.run_sync(AuthBase.metadata.create_all)

    # Setup API DB tables
    async with api_test_engine.begin() as conn:
        await conn.run_sync(ApiBase.metadata.create_all)

    yield

    # Teardown
    async with auth_test_engine.begin() as conn:
        await conn.run_sync(AuthBase.metadata.drop_all)
    async with api_test_engine.begin() as conn:
        await conn.run_sync(ApiBase.metadata.drop_all)


async def override_get_auth_db() -> AsyncGenerator[AsyncSession, None]:
    async with AuthTestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def override_get_api_db() -> AsyncGenerator[AsyncSession, None]:
    async with ApiTestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


auth_app.dependency_overrides[get_auth_db] = override_get_auth_db
api_app.dependency_overrides[get_api_db] = override_get_api_db


@pytest_asyncio.fixture
async def auth_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=auth_app),
        base_url="http://auth.test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=api_app),
        base_url="http://api.test",
    ) as client:
        yield client


@pytest.fixture
def make_token():
    def _make(
        user_id: str = "user-test-1",
        username: str = "testuser",
        email: str = "test@example.com",
        tenant_id: str = "tenant-test",
        role: str = "user",
    ) -> str:
        return create_access_token({
            "sub": user_id,
            "username": username,
            "email": email,
            "tenant_id": tenant_id,
            "role": role,
        })
    return _make
