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
    draft_match = re.search(r"<DRAFT>\n?(.*?)\n?</DRAFT>", raw_output, re.DOTALL)
    sources_match = re.search(r"<SOURCES>\n?(.*?)\n?</SOURCES>", raw_output, re.DOTALL)

    if not draft_match or not sources_match:
        raise ValueError("Output missing required <DRAFT> or <SOURCES> tags.")

    draft = draft_match.group(1).strip()
    sources_str = sources_match.group(1).strip()

    try:
        sources = json.loads(sources_str)
        if not isinstance(sources, list):
            raise ValueError("Sources must be a JSON array.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse sources JSON: {e}")

    return draft, sources

async def run_generation(
    deps: AgentDeps, brief: str, model_id: Optional[str] = None, api_key: Optional[str] = None
) -> Tuple[str, list[dict]]:
    
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
    
    draft, sources = parse_agent_output(result.data)
    
    return draft, sources
