"""
Thin wrapper around the OpenAI-compatible clients for the two vLLM instances.

MODEL_FAST  -> smaller model, cheap templated/lookup-style generation
               (Customer Outreach, Parts Recommendation)
MODEL_REASON -> larger of the two models, used where more judgment is needed
               (Orchestrator, Diagnostic, Revenue Opportunity)

Point these at whatever you actually serve — see docker-compose.yml.
Swap the model names for whatever you pull, the rest of the code doesn't care.
"""
import os
from openai import AsyncOpenAI

MODEL_FAST_BASE_URL = os.environ.get("MODEL_FAST_URL", "http://127.0.0.1:8000/v1")
MODEL_FAST_NAME = os.environ.get("MODEL_FAST_NAME", "Qwen2.5-1.5B-Instruct")

MODEL_REASON_BASE_URL = os.environ.get("MODEL_REASON_URL", "http://127.0.0.1:8001/v1")
MODEL_REASON_NAME = os.environ.get("MODEL_REASON_NAME", "Qwen2.5-3B-Instruct")

_fast_client = AsyncOpenAI(base_url=MODEL_FAST_BASE_URL, api_key="not-needed")
_reason_client = AsyncOpenAI(base_url=MODEL_REASON_BASE_URL, api_key="not-needed")

CLIENTS = {"fast": (_fast_client, MODEL_FAST_NAME), "reason": (_reason_client, MODEL_REASON_NAME)}


async def chat_completion(tier: str, messages: list, tools: list | None = None, temperature: float = 0.2):
    """tier is 'fast' or 'reason'. Returns the raw OpenAI-shaped response dict
    (so callers can read both `choices` and `usage`)."""
    client, model_name = CLIENTS[tier]
    kwargs = {"model": model_name, "messages": messages, "temperature": temperature}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    response = await client.chat.completions.create(**kwargs)
    return response
