"""
Shared LangChain callback for token/cost tracking — used by BOTH
evaluation/run_eval.py and api.py, so eval and production traffic are
measured with the exact same logic instead of two copies drifting
apart over time.

Provider-agnostic: reads `usage_metadata` off each AIMessage a chain
produces. Works for any LangChain chat model that populates it
(ChatGroq does, mirroring the underlying API's usage field).
"""
from langchain_core.callbacks import BaseCallbackHandler

# Groq's published rate for openai/gpt-oss-120b — update if pricing changes.
INPUT_COST_PER_1M = 0.15
OUTPUT_COST_PER_1M = 0.60


class TokenUsageCallback(BaseCallbackHandler):
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.llm_calls = 0

    def on_llm_end(self, response, **kwargs):
        for generation_list in response.generations:
            for generation in generation_list:
                message = getattr(generation, "message", None)
                usage = getattr(message, "usage_metadata", None) if message else None
                if usage:
                    self.input_tokens += usage.get("input_tokens", 0) or 0
                    self.output_tokens += usage.get("output_tokens", 0) or 0
                    self.llm_calls += 1

    def estimated_cost_usd(self) -> float:
        return (
            (self.input_tokens / 1_000_000) * INPUT_COST_PER_1M
            + (self.output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
        )