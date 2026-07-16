from uuid import UUID
from typing import Optional

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document_chunk import DocumentChunk
from src.repositories import document_repo
from src.services.chunker import chunk_text, chunk_url
from src.services.embedder import embed_texts


async def ingest_document(
    session: AsyncSession,
    document_id: UUID,
    client_id: UUID,
    source_type: str,
    content: Optional[str],
    url: Optional[str]
) -> int:
    # Set document status to processing
    await document_repo.update_status(session, document_id, "processing")
    
    try:
        if source_type == "url":
            if not url:
                raise ValueError("URL is required when source_type is url")
            chunks = chunk_url(url)
        else:
            if not content:
                raise ValueError("Content is required when source_type is text")
            chunks = chunk_text(content)
        
        if not chunks:
            # Empty document
            await document_repo.update_status(session, document_id, "ready")
            return 0
        
        embeddings = await embed_texts(chunks)
        
        chunk_data = [
            {
                "document_id": document_id,
                "client_id": client_id,
                "text": chunk_text_content,
                "embedding": embedding,
                "chunk_index": i
            }
            for i, (chunk_text_content, embedding) in enumerate(zip(chunks, embeddings))
        ]
        
        if chunk_data:
            stmt = insert(DocumentChunk).values(chunk_data)
            await session.execute(stmt)
            await session.commit()
            
        await document_repo.update_status(session, document_id, "ready")
        return len(chunk_data)
        
    except Exception as e:
        # Note: In the future we can save the exact error to the document model
        await document_repo.update_status(session, document_id, "failed", error_message=str(e))
        # Re-raise so the endpoint can handle/log it
        raise
