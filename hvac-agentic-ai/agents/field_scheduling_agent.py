"""
Field Scheduling Agent — Optimization Engine, deliberately NOT an LLM.

For this practice project it's a greedy "earliest slot, matching skill and
city" picker. A real version would swap this for a constraint solver
(e.g. OR-Tools CP-SAT / VRP) once you have multiple simultaneous jobs and
real travel-time data to optimize a route across, not just one appointment.
"""
import json
from agents.mcp_tools import ScopedToolClient


class FieldSchedulingAgent:
    agent_key = "field_scheduling"

    def __init__(self, context_monitor=None):
        self.tools = ScopedToolClient(self.agent_key)
        self.context_monitor = context_monitor

    async def run(self, required_skill: str, city: str) -> dict:
        candidates_raw = await self.tools.call(
            "get_technician_availability", {"skill": required_skill, "city": city}
        )
        candidates = json.loads(candidates_raw)

        if not candidates:
            return {"assigned_technician": None, "reason": f"no technician with skill '{required_skill}' in {city}"}

        # Greedy pick: technician with the earliest available slot.
        best_tech, best_slot = None, None
        for tech in candidates:
            for slot in tech["available_slots"]:
                if best_slot is None or slot < best_slot:
                    best_tech, best_slot = tech, slot

        loc_raw = await self.tools.call("get_technician_location", {"technician_id": best_tech["technician_id"]})
        loc = json.loads(loc_raw)

        return {
            "assigned_technician_id": best_tech["technician_id"],
            "assigned_technician_name": best_tech["name"],
            "appointment_slot": best_slot,
            "technician_base_city": loc.get("city"),
            "note": "single-stop greedy assignment — swap in OR-Tools for multi-stop route optimization",
        }
