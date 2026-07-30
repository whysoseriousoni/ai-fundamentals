from agents.base_llm_agent import BaseLLMAgent


class RevenueOpportunityAgent(BaseLLMAgent):
    agent_key = "revenue_opportunity"
    tier = "reason"
    prompt_file = "revenue_opportunity.md"
