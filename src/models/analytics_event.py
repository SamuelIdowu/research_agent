from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import DateTime, String, ForeignKey, Index, text, func, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .tenant import Tenant
    from .client import Client
    from .generation_request import GenerationRequest

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    generation_request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("generation_requests.id"), nullable=True)
    
    event_name: Mapped[str] = mapped_column(String(100), nullable=False) # e.g., generation_started, rag_retrieval_executed
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict[str, Any] | list[Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_analytics_event_tenant_id_created_at", "tenant_id", "created_at"),
        Index("ix_analytics_event_client_id_created_at", "client_id", "created_at"),
    )

    tenant: Mapped["Tenant"] = relationship()
    client: Mapped["Client"] = relationship()
    generation_request: Mapped["GenerationRequest"] = relationship()
