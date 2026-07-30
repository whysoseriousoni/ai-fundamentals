from agents.base_llm_agent import BaseLLMAgent


class OrchestratorAgent(BaseLLMAgent):
    agent_key = "orchestrator"
    tier = "reason"
    prompt_file = "orchestrator.md"
