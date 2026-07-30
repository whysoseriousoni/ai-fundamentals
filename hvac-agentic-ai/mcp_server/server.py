"""
MCP server for the HVAC agentic practice project.

Exposes 18 tools (2 per agent, matching the architecture table) as MCP tools,
backed by the JSON files in data/sample_data/. In a real deployment each of
these functions would call a real telemetry DB, CMMS, ERP, or CRM instead of
reading a JSON file.

Run standalone for testing:
    python server.py                      # stdio transport
Run as a shared HTTP service all 9 agents connect to:
    MCP_TRANSPORT=streamable-http python server.py --port 8010
"""
import json
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DATA_DIR = Path(__file__).parent.parent / "data" / "sample_data"

mcp = FastMCP("hvac-agentic-tools")


def _load(name: str):
    path = DATA_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run data/generate_sample_data.py first")
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Agent 1 — Orchestration Agent
# ---------------------------------------------------------------------------
@mcp.tool()
def get_business_rules() -> dict:
    """Return the priority matrix, SLA thresholds, warranty defaults, and
    auto-dispatch thresholds used to prioritize and route work items."""
    return _load("business_rules")


@mcp.tool()
def get_customer_priority(customer_id: str) -> dict:
    """Return a customer's SLA tier and account type, used to weight queue priority."""
    customers = _load("customers")
    for c in customers:
        if c["customer_id"] == customer_id:
            return {"customer_id": customer_id, "sla_tier": c["sla_tier"], "type": c["type"]}
    return {"error": f"unknown customer_id {customer_id}"}


# ---------------------------------------------------------------------------
# Agent 2 — Device Monitoring Agent
# ---------------------------------------------------------------------------
@mcp.tool()
def get_live_telemetry(unit_id: str) -> dict:
    """Return the latest sensor telemetry snapshot for a unit
    (temperature, pressures, vibration, current, airflow, humidity, runtime)."""
    telemetry = _load("telemetry_latest")
    return telemetry.get(unit_id, {"error": f"no telemetry for {unit_id}"})


@mcp.tool()
def get_sensor_thresholds(unit_id: str) -> dict:
    """Return the alert thresholds configured for a unit's sensors."""
    telemetry = _load("telemetry_latest")
    entry = telemetry.get(unit_id)
    if not entry:
        return {"error": f"no thresholds for {unit_id}"}
    return {"unit_id": unit_id, "thresholds": entry["thresholds"]}


# ---------------------------------------------------------------------------
# Agent 3 — ML Prediction (Failure Probability Model)
# ---------------------------------------------------------------------------
@mcp.tool()
def get_equipment_profile(unit_id: str) -> dict:
    """Return equipment master data (model, install date, warranty) used as
    features for the failure-probability model."""
    equipment = _load("equipment_registry")
    for e in equipment:
        if e["unit_id"] == unit_id:
            return e
    return {"error": f"unknown unit_id {unit_id}"}


@mcp.tool()
def get_maintenance_history(unit_id: str) -> list:
    """Return past maintenance/repair records for a unit
    (date, fault code, action taken, parts used) — used as model features
    and by the Diagnostic Agent for historical-repair context."""
    history = _load("maintenance_history")
    return history.get(unit_id, [])


# ---------------------------------------------------------------------------
# Agent 4 — Diagnostic Agent
# ---------------------------------------------------------------------------
@mcp.tool()
def search_fault_codes(query: str) -> list:
    """Search the fault-code knowledge base by fault code or symptom keyword,
    returning probable causes and recommended diagnostics."""
    kb = _load("fault_codes_kb")
    q = query.lower()
    return [f for f in kb if q in f["fault_code"].lower() or q in f["symptom"].lower()] or kb


@mcp.tool()
def get_maintenance_manual(component: str) -> dict:
    """Return maintenance-manual guidance for a component (stubbed —
    swap for a real manual/RAG lookup in production)."""
    generic = {
        "compressor": "Check winding resistance, run/start capacitor rating, and 3-phase voltage balance before replacement.",
        "condenser fan": "Verify motor bearing play, capacitor uF, and blade balance before ordering a replacement.",
        "pcb": "Check for burnt traces, dry solder joints, and firmware version mismatch before RMA.",
        "expansion valve": "Verify superheat is within spec before assuming valve failure; check for moisture/wax blockage first.",
    }
    key = component.lower()
    for k, v in generic.items():
        if k in key:
            return {"component": component, "guidance": v}
    return {"component": component, "guidance": "No specific manual entry found; escalate to senior technician."}


# ---------------------------------------------------------------------------
# Agent 5 — Service Decision Engine
# ---------------------------------------------------------------------------
@mcp.tool()
def get_sla_status(customer_id: str) -> dict:
    """Return the SLA response-time commitment for a customer's tier."""
    customers = _load("customers")
    rules = _load("business_rules")
    for c in customers:
        if c["customer_id"] == customer_id:
            tier = c["sla_tier"]
            return {"customer_id": customer_id, "sla_tier": tier,
                     "sla_response_hours": rules["priority_matrix"].get(tier, {}).get("sla_response_hours")}
    return {"error": f"unknown customer_id {customer_id}"}


@mcp.tool()
def get_warranty_status(unit_id: str) -> dict:
    """Return whether a unit is currently within its warranty period."""
    from datetime import date
    equipment = _load("equipment_registry")
    for e in equipment:
        if e["unit_id"] == unit_id:
            install = date.fromisoformat(e["install_date"])
            years = e["warranty_years"]
            expiry = install.replace(year=install.year + years)
            return {"unit_id": unit_id, "install_date": e["install_date"],
                     "warranty_expiry": expiry.isoformat(), "in_warranty": date.today() <= expiry}
    return {"error": f"unknown unit_id {unit_id}"}


# ---------------------------------------------------------------------------
# Agent 6 — Parts Recommendation Agent
# ---------------------------------------------------------------------------
@mcp.tool()
def get_bom(equipment_model: str) -> list:
    """Return the bill-of-materials (compatible part numbers) for an equipment model."""
    bom = _load("bom")
    return bom.get(equipment_model, [])


@mcp.tool()
def check_spare_inventory(part_number: str) -> dict:
    """Return stock level and warehouse location for a spare part."""
    inventory = _load("spare_parts_inventory")
    for item in inventory:
        if item["part_number"] == part_number:
            return item
    return {"error": f"unknown part_number {part_number}"}


# ---------------------------------------------------------------------------
# Agent 7 — Customer Outreach Agent
# ---------------------------------------------------------------------------
@mcp.tool()
def get_customer_profile(customer_id: str) -> dict:
    """Return a customer's contact profile: name, phone, preferred channel."""
    customers = _load("customers")
    for c in customers:
        if c["customer_id"] == customer_id:
            return c
    return {"error": f"unknown customer_id {customer_id}"}


@mcp.tool()
def get_appointment_options(city: str) -> list:
    """Return available technician appointment slots in a city."""
    technicians = _load("technicians")
    options = []
    for t in technicians:
        if t["city"].lower() == city.lower():
            for slot in t["available_slots"]:
                options.append({"technician_id": t["technician_id"], "technician_name": t["name"], "slot": slot})
    return options


# ---------------------------------------------------------------------------
# Agent 8 — Field Scheduling Agent
# ---------------------------------------------------------------------------
@mcp.tool()
def get_technician_availability(skill: str, city: str) -> list:
    """Return technicians with a given skill available in a city, with their open slots."""
    technicians = _load("technicians")
    return [t for t in technicians if skill.lower() in [s.lower() for s in t["skills"]] and t["city"].lower() == city.lower()]


@mcp.tool()
def get_technician_location(technician_id: str) -> dict:
    """Return a technician's home city/base, used for route optimization."""
    technicians = _load("technicians")
    for t in technicians:
        if t["technician_id"] == technician_id:
            return {"technician_id": technician_id, "city": t["city"], "skills": t["skills"]}
    return {"error": f"unknown technician_id {technician_id}"}


# ---------------------------------------------------------------------------
# Agent 9 — Revenue Opportunity Agent
# ---------------------------------------------------------------------------
@mcp.tool()
def get_installed_base(customer_id: str) -> list:
    """Return all equipment units installed at a customer, with model and age."""
    equipment = _load("equipment_registry")
    return [e for e in equipment if e["customer_id"] == customer_id]


@mcp.tool()
def get_product_catalog(category: str = "") -> list:
    """Return product/AMC/upgrade catalog entries, optionally filtered by
    category (amc, upgrade, cross_sell)."""
    catalog = _load("product_catalog")
    if not category:
        return catalog
    return [p for p in catalog if p["category"] == category]


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        port = int(os.environ.get("MCP_PORT", "8010"))
        mcp.settings.port = port
        print(f"Starting MCP server on streamable-http :{port}", file=sys.stderr)
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
