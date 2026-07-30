"""
ML Prediction (Failure Probability) Agent — an ML Model slot, not an LLM.

For this practice project it's a transparent heuristic scorer standing in
for a trained model, so the pipeline is runnable without a training step.
Swap `_score` for `joblib.load("model.pkl").predict_proba(...)` once you've
actually trained something on real telemetry + maintenance history.
"""
import json
from agents.mcp_tools import ScopedToolClient


class MLPredictionAgent:
    agent_key = "ml_prediction"

    def __init__(self, context_monitor=None):
        self.tools = ScopedToolClient(self.agent_key)
        self.context_monitor = context_monitor

    def _score(self, anomaly_result: dict, history: list) -> tuple[float, float]:
        """Returns (failure_probability, confidence). Heuristic stand-in:
        each anomalous sensor adds risk; repeat faults in history add more."""
        score = 0.1
        for a in anomaly_result.get("anomalous_sensors", []):
            severity = abs(a["value"] - a["threshold"]) / max(a["threshold"], 1)
            score += 0.15 + min(severity, 0.3)
        score += min(len(history) * 0.08, 0.25)
        prob = min(round(score, 2), 0.98)
        confidence = 0.9 if len(history) >= 1 else 0.65  # more history -> more confident
        return prob, confidence

    async def run(self, unit_id: str, anomaly_result: dict) -> dict:
        profile_raw = await self.tools.call("get_equipment_profile", {"unit_id": unit_id})
        history_raw = await self.tools.call("get_maintenance_history", {"unit_id": unit_id})
        profile = json.loads(profile_raw)
        history = json.loads(history_raw)

        failure_probability, confidence = self._score(anomaly_result, history)

        return {
            "unit_id": unit_id,
            "equipment_model": profile.get("model"),
            "failure_probability": failure_probability,
            "confidence_score": confidence,
            "remaining_useful_life_days": None,  # left as a future enhancement
            "features_used": {
                "anomalous_sensor_count": len(anomaly_result.get("anomalous_sensors", [])),
                "prior_repair_count": len(history),
            },
        }
