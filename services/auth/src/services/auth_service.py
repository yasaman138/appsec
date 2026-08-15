from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
import bcrypt
from fastapi import HTTPException, status
import jwt

from services.auth.src.config import settings
from services.auth.src.models.user import User
from services.auth.src.repositories.user_repository import UserRepository
from services.auth.src.schemas.auth import (
    Token,
    TokenPayload,
    UserLogin,
    UserRegister,
)


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp()), "iat": int(now.timestamp())})
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return TokenPayload(**payload)
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, user_in: UserRegister) -> User:
        # Check existing username
        existing_user = await self.user_repo.get_by_username(user_in.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered",
            )

        # Check existing email
        existing_email = await self.user_repo.get_by_email(user_in.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        # Hash password and create record
        hashed_pwd = hash_password(user_in.password)
        new_user = User(
            id=str(uuid.uuid4()),
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_pwd,
            tenant_id=user_in.tenant_id,
            role=user_in.role or "user",
        )
        return await self.user_repo.create(new_user)

    async def login(self, login_in: UserLogin) -> Token:
        user = await self.user_repo.get_by_username(login_in.username)
        if not user or not verify_password(login_in.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate JWT Token with full identity and tenant context
        expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        payload = {
            "sub": user.id,
            "username": user.username,
            "email": user.email,
            "tenant_id": user.tenant_id,
            "role": user.role,
        }
        token = create_access_token(
            data=payload,
            expires_delta=timedelta(minutes=expires_minutes),
        )
        return Token(
            access_token=token,
            token_type="bearer",
            expires_in=expires_minutes * 60,
        )

    async def get_current_user_from_token(self, token: str) -> User:
        payload = decode_access_token(token)
        user = await self.user_repo.get_by_id(payload.sub)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user
