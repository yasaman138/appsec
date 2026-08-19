from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.api.src.cache import cache_client
from services.api.src.config import settings
from services.api.src.database import init_db
from services.api.src.routers.health import router as health_router
from services.api.src.routers.integrations import router as integrations_router
from services.api.src.routers.records import router as records_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Database Tables
    await init_db()
    # 2. Connect Redis Cache
    await cache_client.connect()
    yield
    # 3. Disconnect Redis Cache
    await cache_client.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

app.include_router(health_router)
app.include_router(records_router)
app.include_router(records_router, prefix="/api/v1")
app.include_router(integrations_router)
app.include_router(integrations_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.api.src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
