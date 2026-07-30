"""
Shared MCP client used by every agent to reach the tool server started by
mcp_server/server.py. Each agent only ever gets the subset of tools it's
supposed to have (the "2 tools per agent" access-control pattern) — the MCP
server itself exposes all 18 tools, and this module is where per-agent
scoping is enforced, since the lightweight FastMCP server doesn't do
per-client tool filtering on its own.
"""
import os
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8010/mcp")

# Which tools each agent is allowed to call. Matches the "2 sample function
# calls per agent" requirement — add more here as an agent's needs grow.
AGENT_TOOL_SCOPES = {
    "orchestrator": ["get_business_rules", "get_customer_priority"],
    "device_monitoring": ["get_live_telemetry", "get_sensor_thresholds"],
    "ml_prediction": ["get_equipment_profile", "get_maintenance_history"],
    "diagnostic": ["search_fault_codes", "get_maintenance_manual"],
    "service_decision": ["get_sla_status", "get_warranty_status"],
    "parts_recommendation": ["get_bom", "check_spare_inventory"],
    "customer_outreach": ["get_customer_profile", "get_appointment_options"],
    "field_scheduling": ["get_technician_availability", "get_technician_location"],
    "revenue_opportunity": ["get_installed_base", "get_product_catalog"],
}


@asynccontextmanager
async def mcp_session():
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


class ScopedToolClient:
    """A tool client bound to one agent's allowed tool names."""

    def __init__(self, agent_key: str):
        if agent_key not in AGENT_TOOL_SCOPES:
            raise ValueError(f"unknown agent_key '{agent_key}'")
        self.agent_key = agent_key
        self.allowed = set(AGENT_TOOL_SCOPES[agent_key])

    async def call(self, tool_name: str, arguments: dict) -> str:
        """Returns a JSON string, always safe to json.loads(). FastMCP emits
        one content block per top-level list element when a tool returns a
        list, rather than one block containing the whole list — so a tool
        returning N results comes back as N content blocks. We reassemble
        those into a single JSON array here so callers can always just
        `json.loads(await tools.call(...))` regardless of whether the
        underlying tool returned a dict, a list, or a scalar."""
        if tool_name not in self.allowed:
            raise PermissionError(
                f"agent '{self.agent_key}' is not scoped to call tool '{tool_name}' "
                f"(allowed: {sorted(self.allowed)})"
            )
        async with mcp_session() as session:
            result = await session.call_tool(tool_name, arguments)
            if not result.content:
                # None of this project's tools return a bare null; an empty
                # result here always means a list-returning tool found zero
                # matches (FastMCP emits zero content blocks for []).
                return "[]"
            if len(result.content) == 1:
                return result.content[0].text
            # multiple blocks -> the tool returned a list; reassemble it
            import json as _json
            items = [_json.loads(c.text) for c in result.content]
            return _json.dumps(items)

    def openai_tool_schemas(self, all_tool_defs: list) -> list:
        """Filter the MCP server's full tool list down to this agent's scope,
        and convert to the OpenAI-style `tools=[...]` schema vLLM expects."""
        schemas = []
        for t in all_tool_defs:
            if t.name in self.allowed:
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema,
                    },
                })
        return schemas


async def list_all_tools():
    async with mcp_session() as session:
        result = await session.list_tools()
        return result.tools
