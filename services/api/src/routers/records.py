from typing import Annotated
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.src.database import get_db
from services.api.src.repositories.record_repository import RecordRepository
from services.api.src.schemas.record import (
    RecordCreate,
    RecordListResponse,
    RecordResponse,
    RecordUpdate,
)
from services.api.src.security import AuthenticatedUser, get_current_user
from services.api.src.services.record_service import RecordService

router = APIRouter(prefix="/records", tags=["Records"])


def get_record_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RecordService:
    repo = RecordRepository(session)
    return RecordService(repo)


@router.post(
    "",
    response_model=RecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant-scoped record",
)
async def create_record(
    record_in: RecordCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RecordService, Depends(get_record_service)],
) -> RecordResponse:
    return await service.create_record(current_user, record_in)


@router.get(
    "",
    response_model=RecordListResponse,
    status_code=status.HTTP_200_OK,
    summary="List records for the current tenant",
)
async def list_records(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RecordService, Depends(get_record_service)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> RecordListResponse:
    items, total = await service.list_records(current_user, limit=limit, offset=offset)
    return RecordListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{record_id}",
    response_model=RecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a tenant-scoped record by ID",
)
async def get_record(
    record_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RecordService, Depends(get_record_service)],
) -> RecordResponse:
    return await service.get_record(current_user, record_id)


@router.put(
    "/{record_id}",
    response_model=RecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a tenant-scoped record by ID",
)
async def update_record(
    record_id: str,
    record_in: RecordUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RecordService, Depends(get_record_service)],
) -> RecordResponse:
    return await service.update_record(current_user, record_id, record_in)


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tenant-scoped record by ID",
)
async def delete_record(
    record_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RecordService, Depends(get_record_service)],
) -> None:
    await service.delete_record(current_user, record_id)
