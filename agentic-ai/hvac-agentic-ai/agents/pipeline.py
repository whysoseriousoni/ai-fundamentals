"""
Wires the 9 agents into the end-to-end workflow:

  Device Monitoring -> ML Prediction -> Diagnostic -> Service Decision
      -> (Parts Recommendation + Field Scheduling + Customer Outreach)
      -> Revenue Opportunity

The Orchestrator Agent runs first and produces a priority/routing decision;
the sequence below is the concrete execution the orchestrator's routing
decision maps to for this practice project (a real system might let the
orchestrator's output dynamically skip/reorder steps — kept linear here so
it's easy to follow while you're learning the pattern).
"""
import json

from agents.orchestrator_agent import OrchestratorAgent
from agents.device_monitoring_agent import DeviceMonitoringAgent
from agents.ml_prediction_agent import MLPredictionAgent
from agents.diagnostic_agent import DiagnosticAgent
from agents.service_decision_agent import ServiceDecisionAgent
from agents.parts_recommendation_agent import PartsRecommendationAgent
from agents.customer_outreach_agent import CustomerOutreachAgent
from agents.field_scheduling_agent import FieldSchedulingAgent
from agents.revenue_opportunity_agent import RevenueOpportunityAgent
from agents.mcp_tools import ScopedToolClient


async def run_pipeline(unit_id: str, context_monitor) -> dict:
    trace: dict = {"unit_id": unit_id, "steps": []}

    # Resolve the owning customer up front (several downstream agents need it)
    ml_tools = ScopedToolClient("ml_prediction")
    profile = json.loads(await ml_tools.call("get_equipment_profile", {"unit_id": unit_id}))
    customer_id = profile.get("customer_id")
    trace["customer_id"] = customer_id

    # 0. Orchestrator: decide priority / routing for this incoming event
    orchestrator = OrchestratorAgent(context_monitor)
    routing_note = await orchestrator.run(
        f"New device event for unit {unit_id}, customer {customer_id}. "
        f"Decide priority and confirm the agent sequence to run."
    )
    trace["steps"].append({"agent": "orchestrator", "output": routing_note})

    # 1. Device Monitoring (rules, no LLM)
    monitor = DeviceMonitoringAgent(context_monitor)
    anomaly_result = await monitor.run(unit_id)
    trace["steps"].append({"agent": "device_monitoring", "output": anomaly_result})

    if not anomaly_result.get("anomaly"):
        trace["final_decision"] = "No anomaly detected — no further action."
        return trace

    # 2. ML Prediction (ML model stand-in, no LLM)
    ml_agent = MLPredictionAgent(context_monitor)
    prediction = await ml_agent.run(unit_id, anomaly_result)
    trace["steps"].append({"agent": "ml_prediction", "output": prediction})

    # 3. Diagnostic (LLM)
    diagnostic = DiagnosticAgent(context_monitor)
    diagnostic_raw = await diagnostic.run(
        f"Unit {unit_id} shows anomalous sensors: {anomaly_result['anomalous_sensors']}. "
        f"Failure probability: {prediction['failure_probability']}. "
        f"Determine the fault code, probable failed component, and root cause."
    )
    # Best-effort fault code carried through for the deterministic downstream agents
    # (in a fuller build, have the Diagnostic Agent return structured JSON instead of prose).
    diagnostic_result = {"raw": diagnostic_raw, "fault_code": anomaly_result.get("_hint_fault_code")}
    trace["steps"].append({"agent": "diagnostic", "output": diagnostic_result})

    # 4. Service Decision Engine (rules + optimization, no LLM)
    business_rules = json.loads(await ScopedToolClient("orchestrator").call("get_business_rules", {}))
    decision_agent = ServiceDecisionAgent(context_monitor)
    decision = await decision_agent.run(
        unit_id=unit_id,
        customer_id=customer_id,
        failure_probability=prediction["failure_probability"],
        diagnostic_result=diagnostic_result,
        remote_fix_eligible_faults=business_rules.get("remote_fix_eligible_faults", []),
    )
    trace["steps"].append({"agent": "service_decision", "output": decision})
    trace["final_decision"] = decision["decision"]

    # 5. Downstream fan-out depending on the decision
    if decision["decision"] in ("Dispatch Technician", "Escalate"):
        parts_agent = PartsRecommendationAgent(context_monitor)
        parts_output = await parts_agent.run(
            f"Equipment model {profile.get('model')}, diagnosed issue: {diagnostic_raw}. "
            f"Recommend spare parts and check stock."
        )
        trace["steps"].append({"agent": "parts_recommendation", "output": parts_output})

        scheduling_agent = FieldSchedulingAgent(context_monitor)
        schedule = await scheduling_agent.run(required_skill="residential_hvac", city=profile.get("location", ""))
        trace["steps"].append({"agent": "field_scheduling", "output": schedule})

    outreach_agent = CustomerOutreachAgent(context_monitor)
    outreach_msg = await outreach_agent.run(
        f"Customer {customer_id}, unit {unit_id}. Service decision: {decision['decision']} ({decision['reason']}). "
        f"Draft the customer-facing message."
    )
    trace["steps"].append({"agent": "customer_outreach", "output": outreach_msg})

    # 6. Revenue Opportunity (LLM) — always runs last
    revenue_agent = RevenueOpportunityAgent(context_monitor)
    revenue_output = await revenue_agent.run(
        f"Customer {customer_id} just had unit {unit_id} serviced (decision: {decision['decision']}). "
        f"Review their installed base and catalog for legitimate opportunities."
    )
    trace["steps"].append({"agent": "revenue_opportunity", "output": revenue_output})

    return trace
