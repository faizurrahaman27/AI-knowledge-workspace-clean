"""
Regression coverage for utils/vector_store.py.

This module was previously broken by an edit that deleted the `_tokenize`
function definition while leaving its call sites intact -- a NameError
that only surfaced at request time inside `/chat/`, not at import time,
so it slipped past both py_compile and the rest of the test suite. These
tests call the actual search functions (not just import the module) to
catch that class of bug going forward.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "stubs"))


def _fresh_vector_store():
    # Each test gets an isolated in-memory Chroma stub collection.
    for mod in list(sys.modules):
        if mod == "chromadb" or mod == "src" or mod.startswith("src."):
            del sys.modules[mod]
    from src.utils import vector_store
    return vector_store


def test_hybrid_search_returns_results_for_matching_query():
    vs = _fresh_vector_store()

    vs.add_documents(
        ids=["a", "b", "c"],
        documents=[
            "The cat sat on the mat.",
            "Dogs are great pets.",
            "Cats and dogs can be friends.",
        ],
        embeddings=[[0.1] * 8, [0.2] * 8, [0.15] * 8],
        metadatas=[
            {"document_id": 1, "page": 1, "chunk": 1, "filename": "x.pdf"},
            {"document_id": 1, "page": 2, "chunk": 1, "filename": "x.pdf"},
            {"document_id": 1, "page": 3, "chunk": 1, "filename": "x.pdf"},
        ],
    )

    docs, metas = vs.hybrid_search(
        query_embedding=[0.1] * 8, query_text="cat", document_id=1, n_results=5
    )

    assert len(docs) == 3
    assert len(metas) == 3
    assert all("document_id" in m for m in metas)


def test_hybrid_search_scopes_to_document_id():
    vs = _fresh_vector_store()

    vs.add_documents(
        ids=["a", "b"],
        documents=["Doc one content about cats.", "Doc two content about cats."],
        embeddings=[[0.1] * 8, [0.1] * 8],
        metadatas=[
            {"document_id": 1, "page": 1, "chunk": 1, "filename": "one.pdf"},
            {"document_id": 2, "page": 1, "chunk": 1, "filename": "two.pdf"},
        ],
    )

    docs, metas = vs.hybrid_search(
        query_embedding=[0.1] * 8, query_text="cats", document_id=1, n_results=5
    )

    assert all(m["document_id"] == 1 for m in metas)


def test_bm25_search_ranks_keyword_match_first():
    vs = _fresh_vector_store()

    vs.add_documents(
        ids=["a", "b"],
        documents=["Completely unrelated text about weather.", "The quarterly revenue figures."],
        embeddings=[[0.0] * 8, [0.0] * 8],
        metadatas=[
            {"document_id": 5, "page": 1, "chunk": 1, "filename": "f.pdf"},
            {"document_id": 5, "page": 2, "chunk": 1, "filename": "f.pdf"},
        ],
    )

    docs, metas = vs._bm25_search("quarterly revenue", document_id=5, n_results=5)

    assert docs, "BM25 search should find a lexical match"
    assert "revenue" in docs[0].lower()


def test_get_document_chunks_sample_orders_by_page():
    vs = _fresh_vector_store()

    vs.add_documents(
        ids=["a", "b", "c"],
        documents=["page3 text", "page1 text", "page2 text"],
        embeddings=[[0.0] * 8] * 3,
        metadatas=[
            {"document_id": 9, "page": 3, "chunk": 1, "filename": "f.pdf"},
            {"document_id": 9, "page": 1, "chunk": 1, "filename": "f.pdf"},
            {"document_id": 9, "page": 2, "chunk": 1, "filename": "f.pdf"},
        ],
    )

    docs, metas = vs.get_document_chunks_sample(document_id=9, max_chunks=10)

    pages = [m["page"] for m in metas]
    assert pages == sorted(pages)
