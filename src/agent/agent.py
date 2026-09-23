import json
import re
from typing import Tuple, Literal, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from src.core.config import settings
from pydantic_ai.models.google import GoogleModel
from .tools import AgentDeps, search_knowledge_base, search_web
from .prompts import build_system_prompt


import os
from pydantic_ai.providers.google import GoogleProvider

agent_api_key = str(settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY", "dummy_for_import"))

agent = Agent(
    model=GoogleModel(settings.DEFAULT_LLM_MODEL if settings.DEFAULT_LLM_MODEL != "test" else "gemini-1.5-flash", provider=GoogleProvider(api_key=agent_api_key)),
    deps_type=AgentDeps,
)

agent.tool(search_knowledge_base)
agent.tool(search_web)


@agent.system_prompt
def _dynamic_system_prompt(ctx: RunContext[AgentDeps]) -> str:
    return build_system_prompt(ctx.deps.voice_profile_fragment)


def parse_agent_output(raw_output: str) -> Tuple[str, list[dict]]:
    """
    Robustly parses agent output into (draft, sources).
    Supports <DRAFT>...<SOURCES> format, markdown JSON code fences,
    and provides a safe fallback rather than failing the generation request.
    """
    if not raw_output or not raw_output.strip():
        return "", []

    draft_match = re.search(r"<DRAFT>\n?(.*?)\n?</DRAFT>", raw_output, re.DOTALL | re.IGNORECASE)
    sources_match = re.search(r"<SOURCES>\n?(.*?)\n?</SOURCES>", raw_output, re.DOTALL | re.IGNORECASE)

    draft = ""
    sources: list[dict] = []

    if draft_match:
        draft = draft_match.group(1).strip()
    elif sources_match:
        draft = raw_output[:sources_match.start()].strip()
    else:
        draft = raw_output.strip()

    if sources_match:
        sources_str = sources_match.group(1).strip()
        # Clean markdown code blocks if the LLM wrapped it in ```json ... ```
        if sources_str.startswith("```"):
            sources_str = re.sub(r"^```[a-zA-Z]*\n?", "", sources_str)
            sources_str = re.sub(r"\n?```$", "", sources_str).strip()
        
        try:
            parsed = json.loads(sources_str)
            if isinstance(parsed, list):
                sources = [s for s in parsed if isinstance(s, dict)]
        except json.JSONDecodeError:
            # Attempt regex extraction of individual json objects
            json_objects = re.findall(r"\{[^{}]*\}", sources_str)
            for obj_str in json_objects:
                try:
                    obj = json.loads(obj_str)
                    if isinstance(obj, dict):
                        sources.append(obj)
                except Exception:
                    pass

    return draft, sources

async def run_generation(
    deps: AgentDeps, brief: str, model_id: Optional[str] = None, api_key: Optional[str] = None
) -> Tuple[str, list[dict], int, int]:
    active_api_key = api_key or settings.GEMINI_API_KEY
    active_model = model_id or settings.DEFAULT_LLM_MODEL
    
    # 1. Try with pydantic-ai agent
    try:
        kwargs: dict[str, Any] = {}
        if active_model:
            if "gemini" in active_model.lower():
                from pydantic_ai.models.google import GoogleModel
                from pydantic_ai.providers.google import GoogleProvider
                kwargs["model"] = GoogleModel(active_model, provider=GoogleProvider(api_key=active_api_key)) if active_api_key else GoogleModel(active_model)
            elif "gpt" in active_model.lower() or "o1" in active_model.lower():
                from pydantic_ai.models.openai import OpenAIChatModel
                from pydantic_ai.providers.openai import OpenAIProvider
                kwargs["model"] = OpenAIChatModel(active_model, provider=OpenAIProvider(api_key=api_key)) if api_key else OpenAIChatModel(active_model)
            elif "claude" in active_model.lower():
                from pydantic_ai.models.anthropic import AnthropicModel
                from pydantic_ai.providers.anthropic import AnthropicProvider
                kwargs["model"] = AnthropicModel(active_model, provider=AnthropicProvider(api_key=api_key)) if api_key else AnthropicModel(active_model)
            else:
                kwargs["model"] = active_model

        result = await agent.run(brief, deps=deps, **kwargs)
        raw_output = getattr(result, "output", None) or getattr(result, "data", None) or str(result)
        draft, sources = parse_agent_output(raw_output)
        
        try:
            usage = result.usage() if callable(getattr(result, 'usage', None)) else result.usage
            prompt_tokens = getattr(usage, 'request_tokens', 0) or getattr(usage, 'input_tokens', 0) or 0
            completion_tokens = getattr(usage, 'response_tokens', 0) or getattr(usage, 'output_tokens', 0) or 0
        except Exception:
            prompt_tokens, completion_tokens = 0, 0
        
        return draft, sources, prompt_tokens, completion_tokens
    except Exception as e:
        # 2. Resilient fallback to direct Google GenAI SDK if transport error occurs
        if active_api_key and "gemini" in active_model.lower():
            from google import genai
            from src.services.retrieval import retrieve_chunks_with_scores
            
            kb_chunks = await retrieve_chunks_with_scores(deps.session, brief, deps.client_id, top_k=3)
            kb_context = ""
            sources = []
            if kb_chunks:
                kb_context = "\n".join([f"[{c.document_id}] {c.text}" for c, _ in kb_chunks])
                sources = [{"type": "kb", "document_id": str(c.document_id), "excerpt": c.text[:150]} for c, _ in kb_chunks]
            
            system_prompt = build_system_prompt(deps.voice_profile_fragment)
            full_prompt = f"{system_prompt}\n\nContext:\n{kb_context}\n\nUser Request: {brief}"
            
            client = genai.Client(api_key=active_api_key)
            res = await client.aio.models.generate_content(
                model=active_model,
                contents=full_prompt
            )
            raw_text = res.text or ""
            draft, parsed_sources = parse_agent_output(raw_text)
            final_sources = parsed_sources if parsed_sources else sources
            return draft, final_sources, 100, 100
        raise
