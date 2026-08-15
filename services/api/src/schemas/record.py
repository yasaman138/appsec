from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RecordCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    is_sensitive: bool = False


class RecordUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    is_sensitive: Optional[bool] = None


class RecordResponse(BaseModel):
    id: str
    title: str
    content: str
    tenant_id: str
    owner_id: str
    is_sensitive: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecordListResponse(BaseModel):
    items: List[RecordResponse]
    total: int
    limit: int
    offset: int
