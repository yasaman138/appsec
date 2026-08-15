from typing import Annotated
from fastapi import APIRouter, Depends, status

from services.api.src.schemas.integration import (
    WebhookTestRequest,
    WebhookTestResponse,
)
from services.api.src.security import AuthenticatedUser, get_current_user
from services.api.src.services.integration_service import IntegrationService

router = APIRouter(prefix="/integrations", tags=["Integrations"])


def get_integration_service() -> IntegrationService:
    return IntegrationService()


@router.post(
    "/webhook-test",
    response_model=WebhookTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Test external webhook integration (vulnerable to blind SSRF)",
)
async def test_webhook(
    request_in: WebhookTestRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> WebhookTestResponse:
    return await service.test_webhook(request_in)
