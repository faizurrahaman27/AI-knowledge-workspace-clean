"""
Cross-encoder reranker, with the model lazily loaded on first use
(see embeddings.py for why).

Model: mmarco-mMiniLMv2-L12-H384-v1, not the English-only
ms-marco-MiniLM-L-6-v2 this used to be. Trained on mMARCO (the
multilingual version of MS MARCO, ~100 languages) instead of just the
English MS MARCO -- the English-only cross-encoder would score
Arabic/Hindi/etc. query-passage pairs close to randomly, since it never
saw non-English text during training, silently making the "rerank for
relevance" step worthless for non-English documents even though nothing
errored.
"""

from functools import lru_cache

from src.core.logging import logger

MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(MODEL_NAME)


def rerank(
    question,
    documents,
    metadatas,
    top_k=5,
):
    """
    Rerank retrieved chunks using a Cross Encoder.
    Returns (documents, metadatas, scores) -- scores power the answer
    confidence indicator in chat_service.
    """

    if not documents:
        return [], [], []

    model = _get_model()

    pairs = [
        (question, doc)
        for doc in documents
    ]

    scores = model.predict(pairs)

    ranked = sorted(
        zip(documents, metadatas, scores),
        key=lambda x: x[2],
        reverse=True,
    )

    ranked_docs = []
    ranked_meta = []
    ranked_scores = []

    for doc, meta, score in ranked[:top_k]:
        # Log only page/score for debugging -- never the document text
        # itself, since it may contain sensitive/regulated content.
        logger.debug("Reranked chunk: page=%s score=%.4f", meta.get("page"), score)

        ranked_docs.append(doc)
        ranked_meta.append(meta)
        ranked_scores.append(float(score))

    return ranked_docs, ranked_meta, ranked_scores
