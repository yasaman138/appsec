from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class WebhookTestRequest(BaseModel):
    url: str = Field(..., description="Target webhook URL to test")
    method: str = Field("POST", description="HTTP method to use (GET, POST, etc.)")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Custom headers")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Optional JSON payload")


class WebhookTestResponse(BaseModel):
    status: str
    target_url: str
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    elapsed_ms: Optional[float] = None
    error: Optional[str] = None
