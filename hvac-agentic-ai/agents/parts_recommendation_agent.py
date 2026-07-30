from agents.base_llm_agent import BaseLLMAgent


class PartsRecommendationAgent(BaseLLMAgent):
    agent_key = "parts_recommendation"
    tier = "fast"
    prompt_file = "parts_recommendation.md"
