from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.generation_request import GenerationRequest


async def create_generation_request(
    session: AsyncSession, tenant_id: UUID, client_id: UUID, brief: str
) -> GenerationRequest:
    db_request = GenerationRequest(
        tenant_id=tenant_id,
        client_id=client_id,
        brief=brief,
        status="pending",
    )
    session.add(db_request)
    await session.commit()
    await session.refresh(db_request)
    return db_request


async def update_generation_request(
    session: AsyncSession, request_id: UUID, **kwargs: Any
) -> GenerationRequest:
    result = await session.execute(
        select(GenerationRequest).filter(GenerationRequest.id == request_id)
    )
    db_request = result.scalar_one()

    for key, value in kwargs.items():
        if hasattr(db_request, key):
            setattr(db_request, key, value)

    await session.commit()
    await session.refresh(db_request)
    return db_request


async def get_generation_request(
    session: AsyncSession, request_id: UUID, client_id: UUID
) -> Optional[GenerationRequest]:
    result = await session.execute(
        select(GenerationRequest).filter(
            GenerationRequest.id == request_id, GenerationRequest.client_id == client_id
        )
    )
    return result.scalar_one_or_none()


async def list_generation_requests(
    session: AsyncSession, client_id: UUID, page: int = 1, page_size: int = 20
) -> tuple[list[GenerationRequest], int]:
    offset = (page - 1) * page_size
    query = select(GenerationRequest).filter(GenerationRequest.client_id == client_id)

    # Get total count
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    # Get paginated results
    paginated_query = query.order_by(GenerationRequest.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(paginated_query)
    items = list(result.scalars().all())

    return items, total
