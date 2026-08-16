from typing import Annotated
from fastapi import APIRouter, Depends, status

from services.api.src.schemas.integration import (
    WebhookTestRequest,
    WebhookTestResponse,
)
from services.api.src.security import (
    AuthenticatedUser,
    RateLimiter,
    get_current_user,
)
from services.api.src.services.integration_service import IntegrationService

router = APIRouter(prefix="/integrations", tags=["Integrations"])
webhook_rate_limiter = RateLimiter(max_requests=20, window_seconds=60, prefix="webhook")


def get_integration_service() -> IntegrationService:
    return IntegrationService()


@router.post(
    "/webhook-test",
    response_model=WebhookTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Test external webhook integration with SSRF and abuse defense",
    dependencies=[Depends(webhook_rate_limiter)],
)
async def test_webhook(
    request_in: WebhookTestRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> WebhookTestResponse:
    return await service.test_webhook(request_in)
