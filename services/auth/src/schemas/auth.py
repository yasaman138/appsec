from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    tenant_id: str = Field(..., min_length=1, max_length=36)
    role: Optional[str] = Field(default="user", max_length=50)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str  # user_id
    username: str
    email: str
    tenant_id: str
    role: str
    exp: Optional[int] = None
    iat: Optional[int] = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    tenant_id: str
    role: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
