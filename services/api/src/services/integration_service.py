import time
from typing import Optional
from fastapi import HTTPException
import httpx
from services.api.src.schemas.integration import (
    WebhookTestRequest,
    WebhookTestResponse,
)
from services.api.src.utils.network import resolve_and_validate_target


class IntegrationService:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client

    async def test_webhook(
        self, request_in: WebhookTestRequest
    ) -> WebhookTestResponse:
        # Defense-in-depth: Validate target URL against SSRF and resolve/pin target IP against DNS Rebinding (TOCTOU)
        target = resolve_and_validate_target(request_in.url)
        safe_url = target.original_url
        dispatch_url = target.pinned_url if target.scheme == "http" else target.original_url

        headers = dict(request_in.headers or {})
        if target.scheme == "http":
            headers.setdefault("Host", target.host_header)

        start_time = time.time()
        try:
            method = request_in.method.upper()
            json_payload = request_in.payload if method in ["POST", "PUT", "PATCH"] else None

            if self._client:
                req = self._client.build_request(
                    method=method,
                    url=safe_url,
                    headers=request_in.headers,
                    json=json_payload,
                    timeout=5.0,
                )
                resp = await self._client.send(req)
            else:
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                    req = client.build_request(
                        method=method,
                        url=dispatch_url,
                        headers=headers,
                        json=json_payload,
                    )
                    resp = await client.send(req)

            elapsed = (time.time() - start_time) * 1000
            return WebhookTestResponse(
                status="success",
                target_url=safe_url,
                status_code=resp.status_code,
                response_body=resp.text[:1000],
                elapsed_ms=round(elapsed, 2),
            )
        except HTTPException:
            raise
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            return WebhookTestResponse(
                status="error",
                target_url=request_in.url,
                error=str(e),
                elapsed_ms=round(elapsed, 2),
            )
