import re

import chromadb
from rank_bm25 import BM25Okapi

client = chromadb.PersistentClient(path="chroma_db")

collection = client.get_or_create_collection(
    name="documents"
)


def add_documents(
    ids,
    documents,
    embeddings,
    metadatas,
):
    """
    Store document chunks into ChromaDB.
    """

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def search_documents(
    query_embedding,
    document_id,
    n_results=5,
):
    """Pure dense (vector) similarity search, scoped to one document."""

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={
            "document_id": document_id
        },
    )

    documents = []
    metadatas = []

    for doc, meta in zip(
        results["documents"][0],
        results["metadatas"][0],
    ):
        if doc and doc.strip():
            documents.append(doc)
            metadatas.append(meta)

    results["documents"][0] = documents
    results["metadatas"][0] = metadatas

    return results


def get_document_chunks_sample(document_id: int, max_chunks: int = 40):
    """
    Pulls a representative sample of a document's chunks, ordered by
    page/chunk, for whole-document tasks (study mode, summaries) where
    "most similar to a query" isn't the right selection criterion --
    we want broad coverage, not narrow relevance.
    """
    all_chunks = collection.get(
        where={"document_id": document_id},
        include=["documents", "metadatas"],
    )

    documents = all_chunks.get("documents") or []
    metadatas = all_chunks.get("metadatas") or []

    paired = sorted(
        zip(documents, metadatas),
        key=lambda x: (x[1].get("page", 0), x[1].get("chunk", 0)),
    )

    if len(paired) > max_chunks:
        # Evenly sample across the document rather than just taking the
        # first N, so later chapters aren't dropped entirely.
        step = len(paired) / max_chunks
        paired = [paired[int(i * step)] for i in range(max_chunks)]

    return [doc for doc, _ in paired], [meta for _, meta in paired]


def _tokenize(text: str) -> list[str]:
    # \w with a Python 3 str pattern is Unicode-aware by default -- this
    # matches letters from ANY script (Arabic, Devanagari, Cyrillic,
    # etc.), not just a-z0-9. The old `[a-z0-9]+` pattern silently found
    # ZERO tokens in non-Latin-script text, meaning BM25 (half of hybrid
    # retrieval) contributed nothing for e.g. Arabic or Hindi documents.
    # Known remaining limitation: CJK languages (Chinese/Japanese/Korean)
    # don't use spaces between words, so this still tokenizes a whole
    # unspaced run as one "word" rather than properly segmenting it --
    # that needs a language-specific segmenter (e.g. jieba for Chinese),
    # not a regex fix, and isn't done here.
    return re.findall(r"\w+", text.lower())


def _bm25_search(query: str, document_id: int, n_results: int):
    """
    Lexical (keyword) search over every chunk belonging to a document,
    using BM25. Chroma's dense search alone can under-rank chunks that
    contain an exact keyword, identifier, or number but are not the
    closest semantic match -- BM25 catches those.
    """

    all_chunks = collection.get(
        where={"document_id": document_id},
        include=["documents", "metadatas"],
    )

    documents = all_chunks.get("documents") or []
    metadatas = all_chunks.get("metadatas") or []

    if not documents:
        return [], []

    tokenized_corpus = [_tokenize(doc) for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)

    scores = bm25.get_scores(_tokenize(query))

    query_tokens = set(_tokenize(query))

    ranked = sorted(
        zip(documents, metadatas, scores),
        key=lambda x: x[2],
        reverse=True,
    )

    # BM25's IDF term can legitimately be zero (or negative) on small
    # corpora -- e.g. a term appearing in exactly half of a 2-chunk
    # document -- which would wrongly filter out a real keyword match if
    # we filtered on `score > 0`. Filter on actual token overlap instead;
    # the score is still used above only to *order* the results.
    top = [
        (doc, meta)
        for doc, meta, _ in ranked[:n_results]
        if query_tokens & set(_tokenize(doc))
    ]

    if not top:
        return [], []

    docs, metas = zip(*top)
    return list(docs), list(metas)


def hybrid_search(
    query_embedding,
    query_text: str,
    document_id: int,
    n_results: int = 20,
):
    """
    Combines dense vector search with BM25 lexical search using Reciprocal
    Rank Fusion (RRF), then hands the fused candidate set to the cross-
    encoder reranker downstream. This is the "hybrid retrieval" step
    called for in the capstone spec (Module 6/7).
    """

    dense_results = search_documents(
        query_embedding=query_embedding,
        document_id=document_id,
        n_results=n_results,
    )
    dense_docs = dense_results["documents"][0]
    dense_metas = dense_results["metadatas"][0]

    bm25_docs, bm25_metas = _bm25_search(query_text, document_id, n_results)

    k = 60  # standard RRF damping constant
    fused_scores: dict[str, float] = {}
    doc_by_key: dict[str, tuple] = {}

    def _key(meta: dict) -> str:
        return f"{meta.get('page')}:{meta.get('chunk')}"

    for rank, (doc, meta) in enumerate(zip(dense_docs, dense_metas)):
        key = _key(meta)
        fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        doc_by_key[key] = (doc, meta)

    for rank, (doc, meta) in enumerate(zip(bm25_docs, bm25_metas)):
        key = _key(meta)
        fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        doc_by_key.setdefault(key, (doc, meta))

    ranked_keys = sorted(fused_scores, key=fused_scores.get, reverse=True)

    fused_docs = [doc_by_key[key][0] for key in ranked_keys[:n_results]]
    fused_metas = [doc_by_key[key][1] for key in ranked_keys[:n_results]]

    return fused_docs, fused_metas


def hybrid_search_multi(
    query_embedding,
    query_text: str,
    document_ids: list[int],
    n_results: int = 20,
):
    """
    Same idea as hybrid_search(), but scoped to a workspace's whole
    document set instead of one document: runs hybrid_search per document,
    then RRF-merges the per-document results into one globally ranked
    list. Uses a document-qualified fusion key (a single-document search's
    "page:chunk" key would collide across different documents that happen
    to share page/chunk numbers).
    """
    if not document_ids:
        return [], []

    k = 60
    fused_scores: dict[str, float] = {}
    doc_by_key: dict[str, tuple] = {}

    for document_id in document_ids:
        docs, metas = hybrid_search(
            query_embedding=query_embedding,
            query_text=query_text,
            document_id=document_id,
            n_results=n_results,
        )
        for rank, (doc, meta) in enumerate(zip(docs, metas)):
            key = f"{document_id}:{meta.get('page')}:{meta.get('chunk')}"
            fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            doc_by_key[key] = (doc, meta)

    ranked_keys = sorted(fused_scores, key=fused_scores.get, reverse=True)[:n_results]

    fused_docs = [doc_by_key[key][0] for key in ranked_keys]
    fused_metas = [doc_by_key[key][1] for key in ranked_keys]

    return fused_docs, fused_metas
