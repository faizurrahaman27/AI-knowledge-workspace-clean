import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.services.document_service import get_owned_document
from src.utils.embeddings import generate_embeddings
from src.utils.vector_store import hybrid_search
from src.utils.reranker import rerank
from src.utils.llm import compare_documents

router = APIRouter(prefix="/compare", tags=["Document Comparison"])


class CompareRequest(BaseModel):
    document_id_a: int
    document_id_b: int
    question: str


def _event(event_type: str, **fields) -> str:
    return json.dumps({"type": event_type, **fields}) + "\n"


def _get_context(question: str, document_id: int) -> str:
    embedding = generate_embeddings([question])[0]
    docs, metas = hybrid_search(
        query_embedding=embedding, query_text=question, document_id=document_id, n_results=20
    )
    docs, metas, _scores = rerank(question=question, documents=docs, metadatas=metas, top_k=5)
    return "\n".join(f"[Page {m.get('page')}] {d}" for d, m in zip(docs, metas))


@router.post("/")
def compare(
    request: CompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc_a = get_owned_document(db, request.document_id_a, current_user)
    doc_b = get_owned_document(db, request.document_id_b, current_user)

    if doc_a.id == doc_b.id:
        raise HTTPException(status_code=400, detail="Pick two different documents to compare.")

    def generate():
        yield _event("status", stage="retrieval", label=f"Searching {doc_a.filename}...")
        context_a = _get_context(request.question, doc_a.id)
        yield _event("status", stage="retrieval", label=f"Searching {doc_b.filename}...")
        context_b = _get_context(request.question, doc_b.id)

        if not context_a.strip() or not context_b.strip():
            yield _event("token", text="I couldn't find enough relevant content in one or both documents.")
            yield _event("done")
            return

        yield _event("status", stage="generation", label="Comparing documents...")

        for chunk in compare_documents(
            context_a=context_a, context_b=context_b,
            name_a=doc_a.filename, name_b=doc_b.filename,
            question=request.question,
        ):
            yield _event("token", text=chunk)

        yield _event("status", stage="generation", done=True, label="Done")
        yield _event("done")

    return StreamingResponse(generate(), media_type="application/x-ndjson")
