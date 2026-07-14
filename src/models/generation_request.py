from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import DateTime, String, Text, ForeignKey, Index, text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .tenant import Tenant
    from .client import Client

class GenerationRequest(Base):
    __tablename__ = "generation_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    sources_used: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_provider_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_generation_request_client_id_created_at_desc", "client_id", "created_at", postgresql_using="btree", postgresql_ops={"created_at": "DESC"}),
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="generation_requests")
    client: Mapped["Client"] = relationship(back_populates="generation_requests")
