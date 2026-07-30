from agents.base_llm_agent import BaseLLMAgent


class DiagnosticAgent(BaseLLMAgent):
    agent_key = "diagnostic"
    tier = "reason"
    prompt_file = "diagnostic.md"
