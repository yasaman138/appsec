from datetime import datetime
from typing import List, Optional, Tuple
import uuid
from fastapi import HTTPException, status
from services.api.src.cache import CacheClient, cache_client
from services.api.src.models.record import Record
from services.api.src.repositories.record_repository import RecordRepository
from services.api.src.schemas.record import RecordCreate, RecordResponse, RecordUpdate
from services.api.src.security import AuthenticatedUser


class RecordService:
    def __init__(
        self,
        repository: RecordRepository,
        cache: CacheClient = cache_client,
    ):
        self.repo = repository
        self.cache = cache

    async def create_record(
        self, user: AuthenticatedUser, record_in: RecordCreate
    ) -> RecordResponse:
        record = Record(
            id=str(uuid.uuid4()),
            title=record_in.title,
            content=record_in.content,
            tenant_id=user.tenant_id,
            owner_id=user.user_id,
            is_sensitive=record_in.is_sensitive,
        )
        saved = await self.repo.create(record)
        response = RecordResponse.model_validate(saved)

        # Cache newly created record
        cache_key = self.cache.make_record_key(user.tenant_id, saved.id)
        await self.cache.set(cache_key, response.model_dump(mode="json"))

        return response

    async def get_record(
        self, user: AuthenticatedUser, record_id: str
    ) -> RecordResponse:
        cache_key = self.cache.make_record_key(user.tenant_id, record_id)

        # 1. Try cache first
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            return RecordResponse.model_validate(cached_data)

        # 2. Query database scoped to user's tenant
        record = await self.repo.get_by_id_and_tenant(
            record_id=record_id,
            tenant_id=user.tenant_id,
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Record not found",
            )

        response = RecordResponse.model_validate(record)
        # Populate cache on miss
        await self.cache.set(cache_key, response.model_dump(mode="json"))
        return response

    async def list_records(
        self, user: AuthenticatedUser, limit: int = 50, offset: int = 0
    ) -> Tuple[List[RecordResponse], int]:
        records, total = await self.repo.list_by_tenant(
            tenant_id=user.tenant_id,
            limit=limit,
            offset=offset,
        )
        responses = [RecordResponse.model_validate(r) for r in records]
        return responses, total

    async def update_record(
        self,
        user: AuthenticatedUser,
        record_id: str,
        record_in: RecordUpdate,
    ) -> RecordResponse:
        record = await self.repo.get_by_id_and_tenant(
            record_id=record_id,
            tenant_id=user.tenant_id,
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Record not found",
            )

        update_dict = record_in.model_dump(exclude_unset=True)
        updated = await self.repo.update(record, update_dict)
        response = RecordResponse.model_validate(updated)

        # Update cache
        cache_key = self.cache.make_record_key(user.tenant_id, record_id)
        await self.cache.set(cache_key, response.model_dump(mode="json"))
        return response

    async def delete_record(
        self, user: AuthenticatedUser, record_id: str
    ) -> None:
        record = await self.repo.get_by_id_and_tenant(
            record_id=record_id,
            tenant_id=user.tenant_id,
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Record not found",
            )

        await self.repo.delete(record)

        # Invalidate cache
        cache_key = self.cache.make_record_key(user.tenant_id, record_id)
        await self.cache.delete(cache_key)
