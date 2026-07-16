from dataclasses import dataclass
from uuid import UUID

from pydantic_ai import RunContext
from sqlalchemy.ext.asyncio import AsyncSession
from tavily import AsyncTavilyClient  # type: ignore

from src.services.retrieval import retrieve_chunks_with_scores


@dataclass
class AgentDeps:
    session: AsyncSession
    client_id: UUID
    tenant_id: UUID
    voice_profile_fragment: str
    tavily_api_key: str


async def search_knowledge_base(ctx: RunContext[AgentDeps], query: str) -> str:
    """Always use this first to ground the draft in the client's specific context. Returns text with UUIDs for citations."""
    chunks_with_scores = await retrieve_chunks_with_scores(
        ctx.deps.session, query, ctx.deps.client_id, top_k=5
    )
    if not chunks_with_scores:
        return "No relevant knowledge base content found."

    results = []
    for i, (chunk, score) in enumerate(chunks_with_scores, 1):
        # Format explicitly as required: "[id] text (score: x.xxx)"
        results.append(f"[{chunk.document_id}] {chunk.text} (score: {score:.3f})")
    
    return "\n...\n".join(results)


async def search_web(ctx: RunContext[AgentDeps], query: str) -> str:
    """Only use this if the brief asks for real-world events or trends not covered by the client's knowledge base. Returns text with [W#] identifiers."""
    if not ctx.deps.tavily_api_key:
        return "Web search unavailable: No API key configured."

    client = AsyncTavilyClient(api_key=ctx.deps.tavily_api_key)
    try:
        response = await client.search(query=query, max_results=5, include_answer=True)
        results = []
        for i, res in enumerate(response.get("results", []), 1):
            title = res.get("title", "No Title")
            content = res.get("content", "")
            url = res.get("url", "")
            results.append(f"[W{i}] {title}: {content}\nURL: {url}")
        
        if not results:
            return "No web results found."
            
        return "\n...\n".join(results)
    except Exception as e:
        return f"Web search unavailable: {str(e)}"
