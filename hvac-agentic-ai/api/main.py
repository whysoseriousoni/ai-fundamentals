"""
FastAPI front door for the HVAC agentic pipeline. The chat UI (ui/index.html)
talks only to this service — it never talks to the LLMs or MCP server directly.

Run with:  uvicorn api.main:app --reload --port 8080
(run from the project root so the `agents` package resolves)
"""
import re
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.context_monitor import ContextWindowMonitor, AgentContextBudget
from agents.pipeline import run_pipeline, run_pipeline_streaming
from agents.orchestrator_agent import OrchestratorAgent
from agents.mcp_tools import ScopedToolClient

app = FastAPI(title="HVAC Agentic Practice API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Context budgets should match whatever --max-model-len you actually serve.
context_monitor = ContextWindowMonitor({
    "orchestrator": AgentContextBudget(max_context_tokens=8192),
    "diagnostic": AgentContextBudget(max_context_tokens=8192),
    "revenue_opportunity": AgentContextBudget(max_context_tokens=8192),
    "parts_recommendation": AgentContextBudget(max_context_tokens=4096),
    "customer_outreach": AgentContextBudget(max_context_tokens=4096),
})

UNIT_ID_PATTERN = re.compile(r"UNIT-\d{4}")


class ChatRequest(BaseModel):
    message: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/context-stats")
async def context_stats():
    return context_monitor.snapshot()


@app.get("/units")
async def list_units():
    tools = ScopedToolClient("ml_prediction")
    # get_maintenance_history isn't a full registry listing tool, so this is a light
    # convenience endpoint for the UI's dropdown, not one of the 18 agent tools.
    from pathlib import Path
    data_path = Path(__file__).parent.parent / "data" / "sample_data" / "equipment_registry.json"
    return json.loads(data_path.read_text())


@app.post("/pipeline/{unit_id}")
async def trigger_pipeline(unit_id: str):
    """Run the full 9-agent pipeline against a specific unit."""
    trace = await run_pipeline(unit_id, context_monitor)
    trace["context_window"] = context_monitor.snapshot()
    return trace


def _sse(event: dict) -> str:
    """Format one Server-Sent-Events frame. Each frame is a single JSON
    object on the `data:` line, terminated by a blank line."""
    return f"data: {json.dumps(event)}\n\n"


@app.post("/pipeline/{unit_id}/stream")
async def trigger_pipeline_stream(unit_id: str):
    """Same pipeline as /pipeline/{unit_id}, but streamed as Server-Sent
    Events — one event per agent_start / token / tool_call / tool_result /
    agent_done / step_start / step_done, so a client can show which LLM is
    executing which task as it happens instead of waiting for the whole
    ~2 minute run to finish silently."""
    async def event_stream():
        async for event in run_pipeline_streaming(unit_id, context_monitor):
            yield _sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Streaming counterpart to /chat. If the message references a unit_id,
    streams the full pipeline's progress events; otherwise streams the
    Orchestrator's token-by-token reply for a general question."""
    match = UNIT_ID_PATTERN.search(req.message)

    async def event_stream():
        if match:
            unit_id = match.group(0)
            async for event in run_pipeline_streaming(unit_id, context_monitor):
                yield _sse(event)
        else:
            orchestrator = OrchestratorAgent(context_monitor)
            async for event in orchestrator.run_streaming(req.message):
                yield _sse(event)
            yield _sse({"type": "context_window", "snapshot": context_monitor.snapshot()})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Single entry point for the UI. If the message references a unit_id
    (e.g. "UNIT-0001 seems off"), run the full pipeline against it.
    Otherwise, treat the message as a general question for the Orchestrator.
    """
    match = UNIT_ID_PATTERN.search(req.message)
    if match:
        unit_id = match.group(0)
        trace = await run_pipeline(unit_id, context_monitor)
        reply = _summarize_trace(trace)
        return {"reply": reply, "trace": trace, "context_window": context_monitor.snapshot()}

    orchestrator = OrchestratorAgent(context_monitor)
    reply = await orchestrator.run(req.message)
    return {"reply": reply, "trace": None, "context_window": context_monitor.snapshot()}


def _summarize_trace(trace: dict) -> str:
    lines = [f"Pipeline run for {trace['unit_id']} (customer {trace.get('customer_id')}):"]
    for step in trace["steps"]:
        agent = step["agent"]
        output = step["output"]
        if isinstance(output, dict):
            summary = output.get("decision") or output.get("anomaly") or output.get("failure_probability") or "done"
        else:
            summary = str(output)[:180]
        lines.append(f"- {agent}: {summary}")
    lines.append(f"Final decision: {trace.get('final_decision')}")
    return "\n".join(lines)
