"""
Base class for the LLM-backed agents (Orchestrator, Diagnostic, Parts
Recommendation, Customer Outreach, Revenue Opportunity).

Two ways to run an agent:
  - `run(user_content)` — non-streaming, returns the final answer as a string.
    Handles the standard tool-calling loop internally.
  - `run_streaming(user_content)` — an async generator yielding progress
    events as they happen (agent_start, token, tool_call, tool_result,
    agent_done, agent_error) — this is what lets the UI show "which LLM is
    executing which task" live instead of a silent multi-second wait.

Both record token usage into the shared ContextWindowMonitor after every hop.

The 4 non-LLM agents (Device Monitoring, ML Prediction, Service Decision,
Field Scheduling) deliberately do NOT subclass this — they're plain
deterministic Python, matching the "not necessarily AI" / "not LLM" column
in the architecture table. See agents/device_monitoring_agent.py etc.
"""
import json
from pathlib import Path

from openai import BadRequestError

from agents.llm_client import chat_completion, stream_chat_completion
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

    # ------------------------------------------------------------------
    # Non-streaming path
    # ------------------------------------------------------------------
    async def run(self, user_content: str) -> str:
        schemas = await self._tool_schemas()
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]

        for _ in range(MAX_TOOL_HOPS):
            try:
                response = await chat_completion(self.tier, messages, tools=schemas)
            except BadRequestError as e:
                return f"[{self.agent_key} failed: {e.message}] — check the vLLM server log for the full rejection reason"

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

    # ------------------------------------------------------------------
    # Streaming path — yields progress events instead of returning once
    # ------------------------------------------------------------------
    async def run_streaming(self, user_content: str):
        schemas = await self._tool_schemas()
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]
        yield {"type": "agent_start", "agent": self.agent_key, "tier": self.tier}

        for _ in range(MAX_TOOL_HOPS):
            content_acc = ""
            tool_calls_acc: dict[int, dict] = {}
            usage = None

            try:
                async for chunk in stream_chat_completion(self.tier, messages, tools=schemas):
                    if chunk.usage:
                        usage = chunk.usage.model_dump()
                    if not chunk.choices:
                        continue  # the final usage-only chunk has no choices
                    delta = chunk.choices[0].delta
                    if delta.content:
                        content_acc += delta.content
                        yield {"type": "token", "agent": self.agent_key, "delta": delta.content}
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            slot = tool_calls_acc.setdefault(tc.index, {"id": None, "name": "", "arguments": ""})
                            if tc.id:
                                slot["id"] = tc.id
                            if tc.function and tc.function.name:
                                slot["name"] += tc.function.name
                            if tc.function and tc.function.arguments:
                                slot["arguments"] += tc.function.arguments
            except BadRequestError as e:
                yield {"type": "agent_error", "agent": self.agent_key, "error": e.message}
                return

            if usage:
                self.context_monitor.record(self.agent_key, usage)

            if tool_calls_acc:
                messages.append({
                    "role": "assistant",
                    "content": content_acc or None,
                    "tool_calls": [
                        {"id": slot["id"], "type": "function",
                         "function": {"name": slot["name"], "arguments": slot["arguments"]}}
                        for slot in tool_calls_acc.values()
                    ],
                })
                for slot in tool_calls_acc.values():
                    args = json.loads(slot["arguments"] or "{}")
                    yield {"type": "tool_call", "agent": self.agent_key, "tool": slot["name"], "arguments": args}
                    try:
                        result = await self.tools.call(slot["name"], args)
                    except PermissionError as e:
                        result = json.dumps({"error": str(e)})
                    yield {"type": "tool_result", "agent": self.agent_key, "tool": slot["name"], "result": result}
                    messages.append({"role": "tool", "tool_call_id": slot["id"], "content": result})
                continue  # next hop, model sees the tool results

            yield {"type": "agent_done", "agent": self.agent_key, "output": content_acc}
            return

        yield {"type": "agent_error", "agent": self.agent_key, "error": "hit MAX_TOOL_HOPS without a final answer"}
