import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "stubs"))


def _fresh_vector_store():
    for mod in list(sys.modules):
        if mod == "chromadb" or mod == "src" or mod.startswith("src."):
            del sys.modules[mod]
    from src.utils import vector_store
    return vector_store


def test_tokenizer_finds_tokens_in_arabic_text():
    vs = _fresh_vector_store()
    tokens = vs._tokenize("مرحبا بكم في هذا المستند حول الذكاء الاصطناعي")
    assert len(tokens) > 0, "Arabic text must produce tokens, not silently zero"
    assert "الذكاء" in tokens


def test_tokenizer_finds_tokens_in_russian_and_cyrillic():
    vs = _fresh_vector_store()
    tokens = vs._tokenize("Это документ об искусственном интеллекте")
    assert len(tokens) > 0
    assert "искусственном" in tokens


def test_tokenizer_still_works_for_english():
    vs = _fresh_vector_store()
    tokens = vs._tokenize("This is a document about artificial intelligence")
    assert "artificial" in tokens
    assert "intelligence" in tokens


def test_bm25_search_finds_arabic_keyword_match():
    vs = _fresh_vector_store()

    vs.add_documents(
        ids=["a", "b"],
        documents=[
            "الفصل الأول يتحدث عن الطقس والمناخ.",
            "الفصل الثاني يشرح الذكاء الاصطناعي والتعلم الآلي.",
        ],
        embeddings=[[0.0] * 8, [0.0] * 8],
        metadatas=[
            {"document_id": 1, "page": 1, "chunk": 1, "filename": "ar.pdf"},
            {"document_id": 1, "page": 2, "chunk": 1, "filename": "ar.pdf"},
        ],
    )

    docs, metas = vs._bm25_search("الذكاء الاصطناعي", document_id=1, n_results=5)

    assert docs, "BM25 should find the AI chapter for an Arabic keyword query"
    assert "الذكاء" in docs[0]


def test_hybrid_search_works_end_to_end_for_arabic():
    vs = _fresh_vector_store()

    vs.add_documents(
        ids=["a", "b"],
        documents=[
            "هذا النص يتحدث عن الطبخ والوصفات.",
            "هذا النص يشرح البرمجة وتطوير البرمجيات.",
        ],
        embeddings=[[0.1] * 8, [0.2] * 8],
        metadatas=[
            {"document_id": 2, "page": 1, "chunk": 1, "filename": "ar2.pdf"},
            {"document_id": 2, "page": 2, "chunk": 1, "filename": "ar2.pdf"},
        ],
    )

    docs, metas = vs.hybrid_search(
        query_embedding=[0.2] * 8, query_text="البرمجة", document_id=2, n_results=5
    )

    assert len(docs) == 2
    assert metas[0]["document_id"] == 2
