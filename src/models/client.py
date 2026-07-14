from datetime import datetime
from typing import List, TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint, text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .tenant import Tenant
    from .document import Document
    from .document_chunk import DocumentChunk
    from .voice_profile import VoiceProfile
    from .generation_request import GenerationRequest

class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    llm_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    usage_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_this_month: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uix_client_tenant_id_name"),
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="clients")
    documents: Mapped[List["Document"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    chunks: Mapped[List["DocumentChunk"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    voice_profile: Mapped["VoiceProfile"] = relationship(back_populates="client", uselist=False, cascade="all, delete-orphan")
    generation_requests: Mapped[List["GenerationRequest"]] = relationship(back_populates="client", cascade="all, delete-orphan")
