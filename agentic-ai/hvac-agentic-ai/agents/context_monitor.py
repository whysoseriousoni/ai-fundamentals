"""
Tracks token usage per agent across a single pipeline run, so you can see
which agent is closest to blowing its context window before it happens.

Design notes for learning purposes:
- vLLM's OpenAI-compatible /chat/completions response includes a real
  `usage` block (prompt_tokens, completion_tokens) computed by the actual
  model tokenizer — we use that instead of estimating, so the numbers are
  exact, not approximate.
- Each agent declares its own `max_context_tokens` (matches the --max-model-len
  you serve it with in vLLM). The monitor flags an agent as "at risk" once it
  crosses a configurable warning ratio (default 80%) of that budget, which is
  what you'd wire an autoscaler / conversation-trimming step off of.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List


@dataclass
class AgentCallRecord:
    agent_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    timestamp: str


@dataclass
class AgentContextBudget:
    max_context_tokens: int
    warning_ratio: float = 0.8


class ContextWindowMonitor:
    def __init__(self, budgets: Dict[str, AgentContextBudget]):
        self.budgets = budgets
        self.history: Dict[str, List[AgentCallRecord]] = {name: [] for name in budgets}

    def record(self, agent_name: str, usage: dict) -> AgentCallRecord:
        """Call this right after every LLM completion with the raw `usage` dict
        vLLM's OpenAI-compatible endpoint returns."""
        rec = AgentCallRecord(
            agent_name=agent_name,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.history.setdefault(agent_name, []).append(rec)
        return rec

    def latest_usage_pct(self, agent_name: str) -> float:
        budget = self.budgets.get(agent_name)
        records = self.history.get(agent_name, [])
        if not budget or not records:
            return 0.0
        return round(records[-1].total_tokens / budget.max_context_tokens * 100, 1)

    def is_at_risk(self, agent_name: str) -> bool:
        budget = self.budgets.get(agent_name)
        if not budget:
            return False
        pct = self.latest_usage_pct(agent_name)
        return pct >= budget.warning_ratio * 100

    def snapshot(self) -> dict:
        """A JSON-serializable snapshot for the UI's live context-monitor panel."""
        out = {}
        for name, budget in self.budgets.items():
            records = self.history.get(name, [])
            last = records[-1] if records else None
            out[name] = {
                "max_context_tokens": budget.max_context_tokens,
                "last_call_total_tokens": last.total_tokens if last else 0,
                "usage_pct": self.latest_usage_pct(name),
                "at_risk": self.is_at_risk(name),
                "calls_this_run": len(records),
                "cumulative_tokens_this_run": sum(r.total_tokens for r in records),
            }
        return out
