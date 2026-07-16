from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import Document


async def create_document(
    session: AsyncSession,
    client_id: UUID,
    tenant_id: UUID,
    source_type: str,
    title: Optional[str],
    source_url: Optional[str]
) -> Document:
    document = Document(
        client_id=client_id,
        tenant_id=tenant_id,
        source_type=source_type,
        title=title,
        source_url=source_url,
        status="pending"
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def get_document(session: AsyncSession, document_id: UUID, client_id: UUID) -> Optional[Document]:
    stmt = select(Document).where(
        Document.id == document_id,
        Document.client_id == client_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_documents(
    session: AsyncSession,
    client_id: UUID,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 50
) -> Tuple[list[Document], int]:
    base_stmt = select(Document).where(
        Document.client_id == client_id,
        Document.tenant_id == tenant_id
    )

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_count = await session.scalar(count_stmt) or 0

    stmt = base_stmt.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    documents = result.scalars().all()

    return list(documents), total_count


async def update_status(
    session: AsyncSession,
    document_id: UUID,
    status: str,
    error_message: Optional[str] = None
) -> Document:
    stmt = select(Document).where(Document.id == document_id)
    result = await session.execute(stmt)
    document = result.scalar_one()

    document.status = status
    await session.commit()
    await session.refresh(document)
    return document

async def delete_document(session: AsyncSession, document_id: UUID, client_id: UUID) -> bool:
    document = await get_document(session, document_id, client_id)
    if not document:
        return False
    await session.delete(document)
    await session.commit()
    return True
