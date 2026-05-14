"""
Ranking Agent — Phase 2 will implement this.

Responsibilities:
  - Given a candidate list and user intent, use Gemini to produce a
    ranked top-3 with NATURAL-LANGUAGE JUSTIFICATION per provider.
  - This is the core "agentic reasoning" differentiator — NO hard-coded
    weighted formula. The LLM is the ranker.
  - Write a trace file with the prompt, candidates, LLM reasoning, and
    parsed result.
"""


class RankingAgent:
    """
    LLM-driven ranking of candidate providers.

    Phase 0: stub — returns an empty ranking.
    Phase 2: will use Gemini to reason about tradeoffs and rank providers.
    """

    async def run(self, candidates: list, intent: dict) -> dict:
        """
        Rank candidate providers using LLM reasoning.

        Args:
            candidates: List of provider dicts from DiscoveryAgent.
            intent: Structured intent dict from IntentAgent.

        Returns:
            Dict with 'top_3' ranked list and 'rejected' list,
            each with natural-language reasoning.
        """
        return {
            "top_3": [],
            "rejected": [],
            "reasoning_summary": "Ranking Agent not yet implemented (Phase 2).",
        }
