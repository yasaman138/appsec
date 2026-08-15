from fastapi import APIRouter, status
from services.api.src.cache import cache_client

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {
        "status": "healthy",
        "service": "core-api-service",
        "version": "1.0.0",
        "cache_connected": cache_client.is_connected,
    }
