from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, Text, ForeignKey, Index, text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .document import Document
    from .client import Client

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_document_chunk_client_id", "client_id"),
        # The IVFFlat index on embedding will be added manually in the alembic migration.
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")
    client: Mapped["Client"] = relationship(back_populates="chunks")
