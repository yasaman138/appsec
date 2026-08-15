from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.src.database import get_db
from services.auth.src.repositories.user_repository import UserRepository
from services.auth.src.schemas.auth import (
    Token,
    TokenPayload,
    UserLogin,
    UserRegister,
    UserResponse,
)
from services.auth.src.services.auth_service import AuthService, decode_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    user_repo = UserRepository(session)
    return AuthService(user_repo)


async def get_current_user_payload(
    authorization: Annotated[str, Header()] = "",
) -> TokenPayload:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split("Bearer ")[1].strip()
    return decode_access_token(token)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_in: UserRegister,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    user = await auth_service.register(user_in)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive JWT token",
)
async def login(
    login_in: UserLogin,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> Token:
    return await auth_service.login(login_in)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user identity",
)
async def get_me(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    user = await auth_service.user_repo.get_by_id(payload.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(user)


@router.get(
    "/verify",
    response_model=TokenPayload,
    status_code=status.HTTP_200_OK,
    summary="Verify JWT token and retrieve claims",
)
async def verify_token(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
) -> TokenPayload:
    return payload
