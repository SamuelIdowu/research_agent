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

    # Fallback if tags were omitted by the model
    if not draft:
        if sources_match:
            # Take everything before <SOURCES> as the draft
            draft = raw_output[:sources_match.start()].strip()
        else:
            draft = raw_output.strip()

    return draft, sources

async def run_generation(
    deps: AgentDeps, brief: str, model_id: Optional[str] = None, api_key: Optional[str] = None
) -> Tuple[str, list[dict], int, int]:
    
    kwargs: dict[str, Any] = {}
    if model_id:
        if "gemini" in model_id.lower():
            from pydantic_ai.models.google import GoogleModel
            from pydantic_ai.providers.google import GoogleProvider
            active_api_key = api_key or settings.GEMINI_API_KEY
            kwargs["model"] = GoogleModel(model_id, provider=GoogleProvider(api_key=active_api_key)) if active_api_key else GoogleModel(model_id)
        elif "gpt" in model_id.lower() or "o1" in model_id.lower():
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider
            kwargs["model"] = OpenAIChatModel(model_id, provider=OpenAIProvider(api_key=api_key)) if api_key else OpenAIChatModel(model_id)
        elif "claude" in model_id.lower():
            from pydantic_ai.models.anthropic import AnthropicModel
            from pydantic_ai.providers.anthropic import AnthropicProvider
            kwargs["model"] = AnthropicModel(model_id, provider=AnthropicProvider(api_key=api_key)) if api_key else AnthropicModel(model_id)
        else:
            kwargs["model"] = model_id

    result = await agent.run(brief, deps=deps, **kwargs)
    
    raw_output = getattr(result, "output", None) or getattr(result, "data", None) or str(result)
    draft, sources = parse_agent_output(raw_output)
    
    try:
        usage = result.usage() if callable(getattr(result, 'usage', None)) else result.usage
        prompt_tokens = getattr(usage, 'request_tokens', 0) or getattr(usage, 'input_tokens', 0) or 0
        completion_tokens = getattr(usage, 'response_tokens', 0) or getattr(usage, 'output_tokens', 0) or 0
    except Exception:
        prompt_tokens = 0
        completion_tokens = 0
    
    return draft, sources, prompt_tokens, completion_tokens
