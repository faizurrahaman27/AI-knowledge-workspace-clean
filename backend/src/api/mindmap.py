import json
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.services.document_service import get_owned_document
from src.services.workspace_service import get_workspace_document_ids, list_workspace_documents
from src.utils.vector_store import get_document_chunks_sample
from src.utils.llm import generate_mindmap, generate_knowledge_graph
from src.core.logging import logger

router = APIRouter(prefix="/mindmap", tags=["Mind Map"])


class MindmapRequest(BaseModel):
    document_id: int


class WorkspaceMindmapRequest(BaseModel):
    workspace_id: int


def _extract_json(raw: str) -> dict:
    """
    Models sometimes wrap JSON in ```json fences or add a stray sentence
    despite instructions -- pull out the first {...} block rather than
    failing outright.
    """
    raw = raw.strip()
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError("No JSON object found in model output.")


@router.post("/")
def create_mindmap(
    request: MindmapRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_owned_document(db, request.document_id, current_user)

    chunks, metadatas = get_document_chunks_sample(request.document_id, max_chunks=30)

    if not chunks:
        raise HTTPException(status_code=422, detail="This document has no processed content yet.")

    context = "\n\n".join(f"[Page {m.get('page')}] {c}" for c, m in zip(chunks, metadatas))

    raw = generate_mindmap(context=context, topic_hint=document.filename)

    try:
        tree = _extract_json(raw)
    except (ValueError, json.JSONDecodeError):
        logger.warning("Mind map JSON parse failed for document_id=%s", document.id)
        raise HTTPException(
            status_code=502,
            detail="Could not generate a well-formed mind map this time -- please try again.",
        )

    return tree


@router.post("/workspace")
def create_workspace_knowledge_graph(
    request: WorkspaceMindmapRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Merges concepts across every document in a workspace into one graph,
    instead of one tree per document -- e.g. "Bayes' Theorem" appearing
    in both a textbook and lecture slides becomes a single node citing
    both sources, not two separate nodes. See generate_knowledge_graph's
    docstring for exactly what this is and isn't (not a persistent graph
    database -- one LLM call over a sample of each document).
    """
    documents = list_workspace_documents(db, request.workspace_id, current_user)

    if not documents:
        raise HTTPException(status_code=422, detail="This workspace has no documents yet.")

    # Cap per-document chunks so the combined context stays a sane size
    # as a workspace grows -- a few representative chunks per source is
    # enough for a topic-level graph, unlike a single-document mind map
    # which can afford to sample more deeply from just one source.
    per_doc_chunk_budget = max(5, 30 // len(documents))

    context_parts = []
    source_names = []
    for doc in documents:
        chunks, metadatas = get_document_chunks_sample(doc.id, max_chunks=per_doc_chunk_budget)
        if not chunks:
            continue
        source_names.append(doc.filename)
        for c, m in zip(chunks, metadatas):
            context_parts.append(f"[Source: {doc.filename}, Page {m.get('page')}] {c}")

    if not context_parts:
        raise HTTPException(status_code=422, detail="None of this workspace's documents have processed content yet.")

    context = "\n\n".join(context_parts)
    raw = generate_knowledge_graph(context=context, source_names=source_names)

    try:
        tree = _extract_json(raw)
    except (ValueError, json.JSONDecodeError):
        logger.warning("Knowledge graph JSON parse failed for workspace_id=%s", request.workspace_id)
        raise HTTPException(
            status_code=502,
            detail="Could not generate a well-formed knowledge graph this time -- please try again.",
        )

    return tree
