from services.api.src.routers.health import router as health_router
from services.api.src.routers.records import router as records_router

__all__ = ["records_router", "health_router"]
