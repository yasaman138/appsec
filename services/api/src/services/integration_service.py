import time
from typing import Optional
import httpx
from services.api.src.schemas.integration import (
    WebhookTestRequest,
    WebhookTestResponse,
)


class IntegrationService:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client

    async def test_webhook(
        self, request_in: WebhookTestRequest
    ) -> WebhookTestResponse:
        start_time = time.time()
        # Vulnerability (Blind SSRF): Direct network request to user-supplied URL
        # Lacks any IP blocklist, private subnet filtering (RFC 1918), or localhost/169.254.169.254 checks
        try:
            method = request_in.method.upper()
            json_payload = request_in.payload if method in ["POST", "PUT", "PATCH"] else None
            
            if self._client:
                resp = await self._client.request(
                    method=method,
                    url=request_in.url,
                    headers=request_in.headers,
                    json=json_payload,
                    timeout=5.0,
                )
            else:
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                    resp = await client.request(
                        method=method,
                        url=request_in.url,
                        headers=request_in.headers,
                        json=json_payload,
                    )

            elapsed = (time.time() - start_time) * 1000
            return WebhookTestResponse(
                status="success",
                target_url=request_in.url,
                status_code=resp.status_code,
                response_body=resp.text[:1000],
                elapsed_ms=round(elapsed, 2),
            )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            return WebhookTestResponse(
                status="error",
                target_url=request_in.url,
                error=str(e),
                elapsed_ms=round(elapsed, 2),
            )
