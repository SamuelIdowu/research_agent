from uuid import UUID
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document_chunk import DocumentChunk
from src.services.embedder import embed_texts


async def retrieve_chunks(
    session: AsyncSession,
    query: str,
    client_id: UUID,
    top_k: int = 5
) -> list[DocumentChunk]:
    if not query.strip():
        return []
    
    query_embedding_res = await embed_texts([query])
    if not query_embedding_res:
        return []
        
    query_embedding = query_embedding_res[0]

    # client_id filter is mandatory
    stmt = select(DocumentChunk).where(
        DocumentChunk.client_id == client_id
    ).order_by(
        DocumentChunk.embedding.cosine_distance(query_embedding)
    ).limit(top_k)
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def retrieve_chunks_with_scores(
    session: AsyncSession,
    query: str,
    client_id: UUID,
    top_k: int = 5
) -> list[Tuple[DocumentChunk, float]]:
    if not query.strip():
        return []
        
    query_embedding_res = await embed_texts([query])
    if not query_embedding_res:
        return []
        
    query_embedding = query_embedding_res[0]

    # Cosine distance function
    distance_func = DocumentChunk.embedding.cosine_distance(query_embedding)
    
    stmt = select(
        DocumentChunk, 
        distance_func.label("distance")
    ).where(
        DocumentChunk.client_id == client_id
    ).order_by(
        distance_func
    ).limit(top_k)
    
    result = await session.execute(stmt)
    # The score is generally 1 - distance
    return [(chunk, 1.0 - float(distance)) for chunk, distance in result.all()]
