"""
Service Decision Engine — Rules + Optimization, deliberately NOT an LLM.
Decides Monitor / Remote Fix / Dispatch Technician / Escalate from
failure probability, diagnostic output, SLA, and warranty status.
"""
import json
from agents.mcp_tools import ScopedToolClient


class ServiceDecisionAgent:
    agent_key = "service_decision"

    def __init__(self, context_monitor=None):
        self.tools = ScopedToolClient(self.agent_key)
        self.context_monitor = context_monitor

    async def run(self, unit_id: str, customer_id: str, failure_probability: float,
                   diagnostic_result: dict, remote_fix_eligible_faults: list) -> dict:
        sla_raw = await self.tools.call("get_sla_status", {"customer_id": customer_id})
        warranty_raw = await self.tools.call("get_warranty_status", {"unit_id": unit_id})
        sla = json.loads(sla_raw)
        warranty = json.loads(warranty_raw)

        fault_code = diagnostic_result.get("fault_code")
        decision = "Monitor"
        reason = "Failure probability below tier escalation threshold."

        if fault_code in remote_fix_eligible_faults and failure_probability < 0.6:
            decision, reason = "Remote Fix", f"Fault {fault_code} is remote-fixable and risk is moderate."
        elif failure_probability >= 0.7:
            decision, reason = "Dispatch Technician", "Failure probability crossed auto-dispatch threshold."
        elif sla.get("sla_tier") == "enterprise" and failure_probability >= 0.5:
            decision, reason = "Escalate", "Enterprise SLA tier with elevated failure risk — escalate for priority handling."

        return {
            "unit_id": unit_id,
            "customer_id": customer_id,
            "decision": decision,
            "reason": reason,
            "sla_response_hours": sla.get("sla_response_hours"),
            "in_warranty": warranty.get("in_warranty"),
        }
