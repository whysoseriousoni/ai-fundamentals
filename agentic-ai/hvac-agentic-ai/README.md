# HVAC Agentic AI — Practice Project

A 9-agent agentic system for HVAC service operations (homes & offices), built to
practice local model hosting, MCP tool servers, per-agent tool scoping, context
window management, and multi-agent orchestration. Runs on RTX 4070 / 32GB RAM / R7 5700x.

Everything in this repo has been tested and works — the MCP server, all 18 tools,
the 4 deterministic agents, the tool-calling loop, the pipeline wiring, and the
FastAPI + chat UI — using a mock LLM standing in for vLLM (no GPU in the build
environment). **You still need to point it at real vLLM instances** as described
below; nothing here required faking the hard parts, just the final model calls.

## Architecture

```
                     ┌─────────────────────┐
   chat UI  ───────► │   FastAPI (api/)    │
                     └──────────┬──────────┘
                                 │
                     ┌───────────────────────┐
                     │  Orchestrator Agent   │  (LLM — reasoning tier)
                     └──────────┬────────────┘
                                 │
     ┌───────────────┬──────────┴─────────┬───────────────┐
     ▼                ▼                    ▼               ▼
Device Monitoring  ML Prediction      Diagnostic       Service Decision
 (rules, no LLM)   (ML model stub)    (LLM — reason)    (rules, no LLM)
     │                │                    │                    │
     └────────────────┴─────────┬──────────┴────────────────────┘
                                 ▼
              ┌──────────────────┬──────────────────┬─────────────────┐
              ▼                  ▼                  ▼                 ▼
     Parts Recommendation  Field Scheduling   Customer Outreach   Revenue Opportunity
       (LLM — fast tier)   (optimization,     (LLM — fast tier)     (LLM — reason)
                             no LLM)

     All 9 agents reach data through mcp_server/server.py (18 tools, 2 per agent)
```

5 of the 9 agents call an LLM; 4 are deliberately plain Python (rules /
optimization / an ML-model stand-in) — matching the architecture table you gave,
and matching good practice: don't burn GPU cycles on a threshold check.

| Agent | Type | Model tier |
|---|---|---|
| Orchestrator | LLM | reason |
| Device Monitoring | rules | — |
| ML Prediction | ML model (stub) | — |
| Diagnostic | LLM | reason |
| Service Decision | rules + optimization | — |
| Parts Recommendation | LLM | fast |
| Field Scheduling | optimization | — |
| Customer Outreach | LLM | fast |
| Revenue Opportunity | LLM | reason |

## 1. Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# generate the sample datasets every agent's tools read from
python3 data/generate_sample_data.py
```

## 2. Host the 2 models with vLLM

Two vLLM instances share your 12GB 4070 — sized to fit with headroom:

```bash
# terminal 1 — fast tier (Parts Recommendation, Customer Outreach)
vllm serve Qwen/Qwen2.5-1.5B-Instruct \
  --served-model-name Qwen2.5-1.5B-Instruct \
  --port 8000 --gpu-memory-utilization 0.35 --max-model-len 4096 --max-num-seqs 16

# terminal 2 — reasoning tier (Orchestrator, Diagnostic, Revenue Opportunity)
vllm serve Qwen/Qwen2.5-3B-Instruct \
  --served-model-name Qwen2.5-3B-Instruct \
  --port 8001 --gpu-memory-utilization 0.5 --max-model-len 8192 --max-num-seqs 8
```

Or `docker compose up vllm-fast vllm-reason` (see `docker-compose.yml`) if you'd
rather containerize from the start. If you OOM, drop `--gpu-memory-utilization`
first, then `--max-model-len`, before dropping model size.

Swap in whatever two models you actually want to practice with — nothing else
in the codebase cares about the specific model, only the env vars in `.env`.

## 3. Start the MCP tool server

```bash
MCP_TRANSPORT=streamable-http MCP_PORT=8010 python3 mcp_server/server.py
```

This exposes all 18 tools (2 per agent) over `http://localhost:8010/mcp`, backed
by the JSON files in `data/sample_data/`. Verify it's up:

```bash
curl -s http://localhost:8010/mcp   # should not connection-refuse
```

## 4. Start the orchestration API

```bash
cp .env.example .env   # adjust ports/model names if you changed them
uvicorn api.main:app --reload --port 8080
```

Key endpoints:
- `POST /chat {"message": "..."}` — main entry point the UI uses. If the message
  mentions a unit like `UNIT-0001`, the full pipeline runs; otherwise it's routed
  to the Orchestrator as a general question.
- `POST /pipeline/{unit_id}` — force-run the full pipeline against a specific unit.
- `GET /context-stats` — current per-agent token usage snapshot.
- `GET /units` — list of sample unit_ids to try (from the equipment registry).

## 5. Open the chat UI

Just open `ui/index.html` in a browser (or serve it: `python3 -m http.server 8090 --directory ui`).
It talks to `http://localhost:8080` by default — override with a URL hash, e.g.
`ui/index.html#http://localhost:9090` if you run the API on a different port.

Try: `UNIT-0001 seems to be running warm, can you check it?` — this triggers the
full pipeline and the right-hand panel will show live token usage per agent as
each one gets called.

## Everything with one command

```bash
docker compose up --build
```
(brings up both vLLM instances, the MCP server, and the API — you still open
`ui/index.html` yourself, it's a static file, not containerized)

## Design notes / what to poke at next

- **Context window monitoring** (`agents/context_monitor.py`) reads the real
  `usage` block vLLM returns per call — not an estimate. Budgets in
  `api/main.py` should match whatever `--max-model-len` you actually serve.
- **Per-agent tool scoping** (`agents/mcp_tools.py`, `AGENT_TOOL_SCOPES`) is
  enforced in the client, not the server — the MCP server exposes all 18 tools
  to anyone who connects. A stricter version would run separate MCP server
  instances or namespace tools per agent role.
- **The pipeline is linear** (`agents/pipeline.py`) for readability. A more
  realistic system would let the Orchestrator's own output dynamically decide
  which downstream agents to call and in what order, rather than hardcoding
  the sequence in Python.
- **ML Prediction is a heuristic stub**, not a trained model — a good next step
  once you have real telemetry is to train something small (gradient boosted
  trees work well for tabular failure prediction) and swap `_score()` for
  `model.predict_proba(...)`.
- **Field Scheduling is greedy single-stop** — swap in OR-Tools CP-SAT once
  you're scheduling multiple simultaneous jobs and want real route optimization.
