from typing import Annotated, Optional
from fastapi import Depends, Header, HTTPException, status
import jwt
from pydantic import BaseModel
from services.api.src.config import settings


class AuthenticatedUser(BaseModel):
    user_id: str
    username: str
    email: str
    tenant_id: str
    role: str


async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
) -> AuthenticatedUser:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    try:
        # Insecure JWT verification flaw: allows the 'none' algorithm
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "HS256")

        if alg.lower() == "none":
            # Vulnerability: Accepts unsigned tokens with 'none' algorithm
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
            )
        else:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[alg, settings.JWT_ALGORITHM, "HS256", "none"],
                options={"verify_signature": True},
            )
        user_id = payload.get("sub")
        username = payload.get("username")
        email = payload.get("email")
        tenant_id = payload.get("tenant_id")
        role = payload.get("role", "user")

        if not user_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing required claims (sub, tenant_id)",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthenticatedUser(
            user_id=user_id,
            username=username or "",
            email=email or "",
            tenant_id=tenant_id,
            role=role,
        )
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
