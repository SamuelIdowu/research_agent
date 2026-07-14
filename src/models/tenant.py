from datetime import datetime
from typing import List, TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, DateTime, String, text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .client import Client
    from .api_key import ApiKey
    from .generation_request import GenerationRequest

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    clients: Mapped[List["Client"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    api_keys: Mapped[List["ApiKey"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    generation_requests: Mapped[List["GenerationRequest"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
