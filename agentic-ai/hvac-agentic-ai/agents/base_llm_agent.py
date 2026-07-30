"""
Base class for the LLM-backed agents (Orchestrator, Diagnostic, Parts
Recommendation, Customer Outreach, Revenue Opportunity).

Handles the standard tool-calling loop:
  1. send system prompt + user content + this agent's tool schemas
  2. if the model asks for a tool call -> execute via MCP, feed result back
  3. repeat until the model returns a plain answer
  4. record token usage into the shared ContextWindowMonitor after every hop

The 4 non-LLM agents (Device Monitoring, ML Prediction, Service Decision,
Field Scheduling) deliberately do NOT subclass this — they're plain
deterministic Python, matching the "not necessarily AI" / "not LLM" column
in the architecture table. See agents/device_monitoring_agent.py etc.
"""
import json
from pathlib import Path

from agents.llm_client import chat_completion
from agents.mcp_tools import ScopedToolClient, list_all_tools

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

MAX_TOOL_HOPS = 4  # safety valve against infinite tool-call loops


class BaseLLMAgent:
    agent_key: str = ""      # matches AGENT_TOOL_SCOPES key in mcp_tools.py
    tier: str = "fast"        # "fast" or "reason" — which vLLM instance to use
    prompt_file: str = ""     # filename under prompts/

    def __init__(self, context_monitor):
        self.tools = ScopedToolClient(self.agent_key)
        self.context_monitor = context_monitor
        self.system_prompt = (PROMPTS_DIR / self.prompt_file).read_text()

    async def _tool_schemas(self):
        all_tools = await list_all_tools()
        return self.tools.openai_tool_schemas(all_tools)

    async def run(self, user_content: str) -> str:
        schemas = await self._tool_schemas()
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]

        for _ in range(MAX_TOOL_HOPS):
            response = await chat_completion(self.tier, messages, tools=schemas)
            self.context_monitor.record(self.agent_key, response.usage.model_dump())

            choice = response.choices[0]
            messages.append(choice.message.model_dump(exclude_none=True))

            if not choice.message.tool_calls:
                return choice.message.content or ""

            for call in choice.message.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                try:
                    result = await self.tools.call(call.function.name, args)
                except PermissionError as e:
                    result = json.dumps({"error": str(e)})
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result,
                })

        return "[agent hit MAX_TOOL_HOPS without a final answer — check prompt/tool loop]"
