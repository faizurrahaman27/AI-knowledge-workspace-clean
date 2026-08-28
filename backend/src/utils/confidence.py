"""
Approximate answer-confidence signal, derived from the cross-encoder
reranker's top score (not from LLM logprobs -- Ollama's Python client
doesn't expose token-level probabilities the way some hosted APIs do,
so this is the honest, available signal: "how relevant was the best
matching passage to the question, according to the reranker").

This is a proxy, not a calibrated probability. Treat "High" as "the
retrieved passage clearly matches the question" rather than "the answer
is definitely correct" -- a well-matched passage can still be
misread by the generator.
"""

import math


def score_to_confidence(top_score: float | None) -> dict:
    if top_score is None:
        return {"label": "Unknown", "level": 0}

    # Cross-encoder ms-marco scores are unbounded logits; squash to (0, 1).
    normalized = 1 / (1 + math.exp(-top_score))

    if normalized >= 0.75:
        return {"label": "High", "level": 3, "score": round(normalized, 3)}
    if normalized >= 0.4:
        return {"label": "Medium", "level": 2, "score": round(normalized, 3)}
    return {"label": "Low", "level": 1, "score": round(normalized, 3)}
