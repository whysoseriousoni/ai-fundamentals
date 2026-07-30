"""
Device Monitoring Agent — Rules + Statistical Monitoring, deliberately NOT an
LLM (matches the architecture table: "not necessarily AI"). Pure threshold
checks against live telemetry. Runs first in the pipeline and is what
actually triggers the rest of the agents — no point burning GPU cycles on a
threshold comparison a few lines of Python can do faster and more reliably.
"""
from agents.mcp_tools import ScopedToolClient


class DeviceMonitoringAgent:
    agent_key = "device_monitoring"

    def __init__(self, context_monitor=None):
        self.tools = ScopedToolClient(self.agent_key)
        self.context_monitor = context_monitor  # unused (no LLM tokens), kept for interface symmetry

    async def run(self, unit_id: str) -> dict:
        telemetry_raw = await self.tools.call("get_live_telemetry", {"unit_id": unit_id})
        thresholds_raw = await self.tools.call("get_sensor_thresholds", {"unit_id": unit_id})
        import json
        telemetry = json.loads(telemetry_raw)
        thresholds = json.loads(thresholds_raw).get("thresholds", {})

        if "error" in telemetry:
            return {"unit_id": unit_id, "data_quality_alert": telemetry["error"], "anomaly": False}

        readings = telemetry["readings"]
        anomalies = []

        if readings["pressure_psi_discharge"] > thresholds.get("pressure_psi_discharge_max", 250):
            anomalies.append({"sensor": "pressure_psi_discharge", "value": readings["pressure_psi_discharge"],
                                "threshold": thresholds.get("pressure_psi_discharge_max"), "direction": "high"})
        if readings["pressure_psi_suction"] < thresholds.get("pressure_psi_suction_min", 55):
            anomalies.append({"sensor": "pressure_psi_suction", "value": readings["pressure_psi_suction"],
                                "threshold": thresholds.get("pressure_psi_suction_min"), "direction": "low"})
        if readings["vibration_mm_s"] > thresholds.get("vibration_mm_s_max", 3.5):
            anomalies.append({"sensor": "vibration_mm_s", "value": readings["vibration_mm_s"],
                                "threshold": thresholds.get("vibration_mm_s_max"), "direction": "high"})
        if readings["current_draw_amps"] > thresholds.get("current_draw_amps_max", 11):
            anomalies.append({"sensor": "current_draw_amps", "value": readings["current_draw_amps"],
                                "threshold": thresholds.get("current_draw_amps_max"), "direction": "high"})

        return {
            "unit_id": unit_id,
            "anomaly": len(anomalies) > 0,
            "anomalous_sensors": anomalies,
            "sensor_health_status": "degraded" if anomalies else "nominal",
            "raw_readings": readings,
        }
