from datetime import datetime, timezone
import uuid
from sqlalchemy import Boolean, Column, DateTime, String, Text
from services.api.src.database import Base


class Record(Base):
    __tablename__ = "records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    tenant_id = Column(String(36), nullable=False, index=True)
    owner_id = Column(String(36), nullable=False, index=True)
    is_sensitive = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Record(id='{self.id}', title='{self.title}', tenant_id='{self.tenant_id}', owner_id='{self.owner_id}')>"
