from agents.base_llm_agent import BaseLLMAgent


class CustomerOutreachAgent(BaseLLMAgent):
    agent_key = "customer_outreach"
    tier = "fast"
    prompt_file = "customer_outreach.md"
