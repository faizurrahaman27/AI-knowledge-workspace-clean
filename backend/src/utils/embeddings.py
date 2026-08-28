"""
Embedding generation, with the model lazily loaded on first use.

Loading SentenceTransformer at import time (as the original version did)
means every module that merely imports this file -- including test files
that don't need embeddings -- pays the cost of downloading/loading the
model. Lazy loading keeps imports fast and makes the module easy to unit
test with a stub.

Model: paraphrase-multilingual-MiniLM-L12-v2, not the English-only
all-MiniLM-L6-v2 this used to be. Same 384-dim output (so no schema
change), but trained across 50+ languages -- the English-only model
produced weak, low-quality embeddings for e.g. Arabic or Hindi text,
which silently degraded semantic search for non-English documents even
though nothing errored. Tradeoff: this model is larger (~470MB vs ~90MB)
and slightly slower to load/run.

MIGRATION NOTE: existing documents embedded with the old model have
vectors from a different embedding space than this one produces. New
queries (using this model) against old vectors (from the old model)
won't compare meaningfully even for English text -- if you're upgrading
an existing deployment, you need to delete backend/chroma_db and
re-upload documents, not just restart the server.
"""

from functools import lru_cache

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def generate_embeddings(chunks: list[str]) -> list[list[float]]:
    if not chunks:
        return []
    model = _get_model()
    embeddings = model.encode(chunks)
    return embeddings.tolist()
