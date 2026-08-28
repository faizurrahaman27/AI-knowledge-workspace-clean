class _Collection:
    def __init__(self):
        self._data = []
    def add(self, ids, documents, embeddings, metadatas):
        for i, d, e, m in zip(ids, documents, embeddings, metadatas):
            self._data.append({"id": i, "document": d, "embedding": e, "metadata": m})
    def query(self, query_embeddings, n_results, where=None):
        docs = [x["document"] for x in self._data if not where or x["metadata"].get("document_id") == where.get("document_id")]
        metas = [x["metadata"] for x in self._data if not where or x["metadata"].get("document_id") == where.get("document_id")]
        return {"documents": [docs[:n_results]], "metadatas": [metas[:n_results]]}
    def get(self, where=None, include=None):
        docs = [x["document"] for x in self._data if not where or x["metadata"].get("document_id") == where.get("document_id")]
        metas = [x["metadata"] for x in self._data if not where or x["metadata"].get("document_id") == where.get("document_id")]
        return {"documents": docs, "metadatas": metas}
    def delete(self, where=None):
        self._data = [x for x in self._data if not where or x["metadata"].get("document_id") != where.get("document_id")]

class PersistentClient:
    def __init__(self, path=None):
        self._collections = {}
    def get_or_create_collection(self, name):
        return self._collections.setdefault(name, _Collection())
