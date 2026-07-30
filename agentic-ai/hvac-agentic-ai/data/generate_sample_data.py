"""
Generates fake-but-realistic HVAC operational data for the 9-agent practice project.
Run once: `python generate_sample_data.py` -> writes JSON files into ./sample_data/

This stands in for the real systems each agent's tools would eventually call:
telemetry DB, CMMS/equipment registry, parts ERP, CRM, workforce scheduling, product catalog.
"""
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)
OUT = Path(__file__).parent / "sample_data"
OUT.mkdir(exist_ok=True)

CUSTOMERS = [
    {"customer_id": "CUST-1001", "name": "Aravind Residence", "type": "home", "sla_tier": "standard",
     "preferred_channel": "sms", "phone": "+91-98xxxx1001", "city": "Chennai"},
    {"customer_id": "CUST-1002", "name": "Lakeview Apartments - Block C", "type": "home", "sla_tier": "premium",
     "preferred_channel": "app", "phone": "+91-98xxxx1002", "city": "Chennai"},
    {"customer_id": "CUST-2001", "name": "Meridian Textiles Pvt Ltd", "type": "office", "sla_tier": "enterprise",
     "preferred_channel": "email", "phone": "+91-98xxxx2001", "city": "Coimbatore"},
    {"customer_id": "CUST-2002", "name": "Orion IT Park - Tower 2", "type": "office", "sla_tier": "premium",
     "preferred_channel": "email", "phone": "+91-98xxxx2002", "city": "Chennai"},
]

EQUIPMENT_MODELS = ["SplitAC-1.5T-InverterX", "DuctedAC-5T-CommercialPro", "VRF-10T-EnterpriseFlow", "SplitAC-1T-EcoLite"]

FAULT_CODES_KB = [
    {"fault_code": "E1", "symptom": "high discharge pressure", "probable_causes": ["condenser coil fouling", "refrigerant overcharge", "condenser fan failure"],
     "recommended_diagnostics": ["inspect condenser coil for dust/debris", "check condenser fan motor current draw", "verify refrigerant charge against nameplate"]},
    {"fault_code": "E2", "symptom": "low suction pressure", "probable_causes": ["refrigerant undercharge/leak", "clogged filter/evaporator", "expansion valve stuck closed"],
     "recommended_diagnostics": ["leak-test with electronic sniffer", "inspect/replace air filter", "check superheat across expansion valve"]},
    {"fault_code": "E5", "symptom": "compressor overcurrent trip", "probable_causes": ["compressor winding degradation", "capacitor failure", "voltage imbalance"],
     "recommended_diagnostics": ["megger test compressor windings", "measure run/start capacitor uF vs rated", "measure 3-phase voltage imbalance"]},
    {"fault_code": "E9", "symptom": "abnormal vibration/noise", "probable_causes": ["fan blade imbalance", "loose mounting bolts", "bearing wear"],
     "recommended_diagnostics": ["vibration spectrum analysis", "torque-check mounting hardware", "inspect bearing play"]},
]

BOM = {
    "SplitAC-1.5T-InverterX": ["PN-COMP-15T", "PN-CAP-35UF", "PN-FANMOTOR-STD", "PN-PCB-INV-A3", "PN-FILTER-STD"],
    "DuctedAC-5T-CommercialPro": ["PN-COMP-50T", "PN-CAP-50UF", "PN-FANMOTOR-HD", "PN-PCB-COMM-B1", "PN-FILTER-HD"],
    "VRF-10T-EnterpriseFlow": ["PN-COMP-100T-VRF", "PN-PCB-VRF-C2", "PN-FANMOTOR-VRF", "PN-EXV-VRF", "PN-FILTER-HD"],
    "SplitAC-1T-EcoLite": ["PN-COMP-10T", "PN-CAP-25UF", "PN-FANMOTOR-STD", "PN-PCB-INV-A1", "PN-FILTER-STD"],
}

PARTS_CATALOG = {
    "PN-COMP-15T": {"name": "1.5T Rotary Compressor", "compatible_models": ["SplitAC-1.5T-InverterX"]},
    "PN-COMP-50T": {"name": "5T Scroll Compressor", "compatible_models": ["DuctedAC-5T-CommercialPro"]},
    "PN-COMP-100T-VRF": {"name": "10T VRF Compressor Module", "compatible_models": ["VRF-10T-EnterpriseFlow"]},
    "PN-COMP-10T": {"name": "1T Rotary Compressor", "compatible_models": ["SplitAC-1T-EcoLite"]},
    "PN-CAP-35UF": {"name": "35uF Run Capacitor", "compatible_models": ["SplitAC-1.5T-InverterX"]},
    "PN-CAP-50UF": {"name": "50uF Run Capacitor", "compatible_models": ["DuctedAC-5T-CommercialPro"]},
    "PN-CAP-25UF": {"name": "25uF Run Capacitor", "compatible_models": ["SplitAC-1T-EcoLite"]},
    "PN-FANMOTOR-STD": {"name": "Standard Condenser Fan Motor", "compatible_models": ["SplitAC-1.5T-InverterX", "SplitAC-1T-EcoLite"]},
    "PN-FANMOTOR-HD": {"name": "Heavy Duty Condenser Fan Motor", "compatible_models": ["DuctedAC-5T-CommercialPro"]},
    "PN-FANMOTOR-VRF": {"name": "VRF Outdoor Fan Motor", "compatible_models": ["VRF-10T-EnterpriseFlow"]},
    "PN-PCB-INV-A3": {"name": "Inverter Control PCB A3", "compatible_models": ["SplitAC-1.5T-InverterX"]},
    "PN-PCB-INV-A1": {"name": "Inverter Control PCB A1", "compatible_models": ["SplitAC-1T-EcoLite"]},
    "PN-PCB-COMM-B1": {"name": "Commercial Control PCB B1", "compatible_models": ["DuctedAC-5T-CommercialPro"]},
    "PN-PCB-VRF-C2": {"name": "VRF Main Control PCB C2", "compatible_models": ["VRF-10T-EnterpriseFlow"]},
    "PN-EXV-VRF": {"name": "Electronic Expansion Valve (VRF)", "compatible_models": ["VRF-10T-EnterpriseFlow"]},
    "PN-FILTER-STD": {"name": "Standard Air Filter", "compatible_models": ["SplitAC-1.5T-InverterX", "SplitAC-1T-EcoLite"]},
    "PN-FILTER-HD": {"name": "Heavy Duty Air Filter", "compatible_models": ["DuctedAC-5T-CommercialPro", "VRF-10T-EnterpriseFlow"]},
}

TECHNICIANS = [
    {"technician_id": "TECH-01", "name": "R. Suresh", "skills": ["split_ac", "inverter_pcb"], "city": "Chennai", "available_slots": ["2026-07-30 09:00", "2026-07-30 13:00", "2026-07-31 10:00"]},
    {"technician_id": "TECH-02", "name": "K. Priya", "skills": ["ducted_ac", "commercial_hvac"], "city": "Chennai", "available_slots": ["2026-07-30 11:00", "2026-07-31 09:00"]},
    {"technician_id": "TECH-03", "name": "M. Vignesh", "skills": ["vrf", "commercial_hvac", "compressor_overhaul"], "city": "Coimbatore", "available_slots": ["2026-07-30 14:00", "2026-08-01 09:00"]},
    {"technician_id": "TECH-04", "name": "A. Divya", "skills": ["split_ac", "residential_hvac"], "city": "Chennai", "available_slots": ["2026-07-30 10:00", "2026-07-30 15:00"]},
]

PRODUCT_CATALOG = [
    {"sku": "AMC-STD-1YR", "category": "amc", "name": "Standard AMC (2 services/yr)", "price_inr": 4500},
    {"sku": "AMC-PREM-1YR", "category": "amc", "name": "Premium AMC (4 services/yr + priority)", "price_inr": 8500},
    {"sku": "UPG-INVERTER-1.5T", "category": "upgrade", "name": "Upgrade to 1.5T 5-star Inverter unit", "price_inr": 38000},
    {"sku": "UPG-VRF-MODULE", "category": "upgrade", "name": "VRF outdoor module capacity add-on", "price_inr": 145000},
    {"sku": "AIR-PURIFY-ADDON", "category": "cross_sell", "name": "In-duct air purification add-on", "price_inr": 12000},
]

BUSINESS_RULES = {
    "priority_matrix": {
        "enterprise": {"failure_prob_threshold_escalate": 0.5, "sla_response_hours": 4},
        "premium": {"failure_prob_threshold_escalate": 0.6, "sla_response_hours": 8},
        "standard": {"failure_prob_threshold_escalate": 0.75, "sla_response_hours": 24},
    },
    "warranty_default_years": 2,
    "auto_dispatch_failure_prob": 0.7,
    "remote_fix_eligible_faults": ["E1", "E9"],
}

def gen_equipment():
    equipment = []
    unit_no = 1
    for cust in CUSTOMERS:
        n_units = 1 if cust["type"] == "home" else random.randint(2, 3)
        for _ in range(n_units):
            model = random.choice(EQUIPMENT_MODELS) if cust["type"] == "office" else random.choice(EQUIPMENT_MODELS[:1] + EQUIPMENT_MODELS[3:])
            install_date = datetime(2022, 1, 1) + timedelta(days=random.randint(0, 900))
            equipment.append({
                "unit_id": f"UNIT-{unit_no:04d}",
                "customer_id": cust["customer_id"],
                "model": model,
                "install_date": install_date.strftime("%Y-%m-%d"),
                "location": cust["city"],
                "warranty_years": 2 if cust["type"] == "home" else 3,
            })
            unit_no += 1
    return equipment

EQUIPMENT = gen_equipment()

def gen_telemetry():
    telemetry = {}
    for eq in EQUIPMENT:
        anomalous = random.random() < 0.4
        base = {
            "temperature_c": round(random.uniform(4, 12), 1),
            "pressure_psi_discharge": round(random.uniform(180, 230), 1),
            "pressure_psi_suction": round(random.uniform(60, 90), 1),
            "vibration_mm_s": round(random.uniform(0.5, 2.0), 2),
            "current_draw_amps": round(random.uniform(4, 9), 2),
            "airflow_cfm": round(random.uniform(350, 500), 1),
            "humidity_pct": round(random.uniform(40, 60), 1),
            "runtime_hours_today": round(random.uniform(2, 14), 1),
        }
        if anomalous:
            fault = random.choice(FAULT_CODES_KB)
            if fault["fault_code"] == "E1":
                base["pressure_psi_discharge"] = round(random.uniform(260, 310), 1)
            elif fault["fault_code"] == "E2":
                base["pressure_psi_suction"] = round(random.uniform(20, 45), 1)
            elif fault["fault_code"] == "E5":
                base["current_draw_amps"] = round(random.uniform(12, 18), 2)
            elif fault["fault_code"] == "E9":
                base["vibration_mm_s"] = round(random.uniform(4.5, 8.0), 2)
            base["_injected_fault_code_for_demo"] = fault["fault_code"]
        telemetry[eq["unit_id"]] = {
            "unit_id": eq["unit_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "readings": base,
            "thresholds": {
                "pressure_psi_discharge_max": 250, "pressure_psi_suction_min": 55,
                "vibration_mm_s_max": 3.5, "current_draw_amps_max": 11,
            },
        }
    return telemetry

def gen_maintenance_history():
    history = {}
    for eq in EQUIPMENT:
        n = random.randint(0, 3)
        records = []
        for i in range(n):
            d = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 900))
            fault = random.choice(FAULT_CODES_KB)
            records.append({
                "date": d.strftime("%Y-%m-%d"),
                "fault_code": fault["fault_code"],
                "action_taken": random.choice(["part replaced", "cleaned & serviced", "recalibrated", "monitored, no action"]),
                "parts_used": random.sample(BOM[eq["model"]], k=min(1, len(BOM[eq["model"]]))),
                "technician_id": random.choice(TECHNICIANS)["technician_id"],
            })
        history[eq["unit_id"]] = sorted(records, key=lambda r: r["date"])
    return history

def gen_spare_inventory():
    inventory = []
    for pn, meta in PARTS_CATALOG.items():
        inventory.append({
            "part_number": pn,
            "name": meta["name"],
            "compatible_models": meta["compatible_models"],
            "stock_qty": random.randint(0, 25),
            "warehouse": random.choice(["Chennai-WH1", "Coimbatore-WH1"]),
            "reorder_threshold": 5,
        })
    return inventory

def write(name, obj):
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(obj, indent=2))
    print(f"wrote {path} ({len(json.dumps(obj))} bytes)")

if __name__ == "__main__":
    write("customers", CUSTOMERS)
    write("equipment_registry", EQUIPMENT)
    write("telemetry_latest", gen_telemetry())
    write("fault_codes_kb", FAULT_CODES_KB)
    write("bom", BOM)
    write("spare_parts_inventory", gen_spare_inventory())
    write("maintenance_history", gen_maintenance_history())
    write("technicians", TECHNICIANS)
    write("product_catalog", PRODUCT_CATALOG)
    write("business_rules", BUSINESS_RULES)
    print("\nDone. Sample data lives in data/sample_data/*.json")
