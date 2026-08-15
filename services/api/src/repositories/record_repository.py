from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from services.api.src.models.record import Record


class RecordRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id_and_tenant(
        self, record_id: str, tenant_id: str
    ) -> Optional[Record]:
        query = select(Record).where(
            Record.id == record_id,
            Record.tenant_id == tenant_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self, tenant_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Record], int]:
        # Count total
        count_query = (
            select(func.count())
            .select_from(Record)
            .where(Record.tenant_id == tenant_id)
        )
        count_res = await self.session.execute(count_query)
        total = count_res.scalar_one()

        # Fetch records
        query = (
            select(Record)
            .where(Record.tenant_id == tenant_id)
            .order_by(Record.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def create(self, record: Record) -> Record:
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def update(self, record: Record, update_data: dict) -> Record:
        for key, value in update_data.items():
            if value is not None and hasattr(record, key):
                setattr(record, key, value)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def delete(self, record: Record) -> None:
        await self.session.delete(record)
        await self.session.flush()
