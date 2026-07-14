from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, String, Text, ForeignKey, text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .client import Client

class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True)
    tone: Mapped[str | None] = mapped_column(Text, nullable=True)
    pov: Mapped[str | None] = mapped_column(String(50), nullable=True)
    banned_words: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    extra_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    client: Mapped["Client"] = relationship(back_populates="voice_profile")
