import asyncio
import json
import time

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.models.chat import Chat
from src.models.user import User
from src.models.document import Document
from src.models.workspace import Workspace

from src.utils.embeddings import generate_embeddings
from src.utils.vector_store import hybrid_search, hybrid_search_multi
from src.utils.reranker import rerank
from src.utils.llm import ask_llm, translate_text
from src.utils.guardrails import check_user_message
from src.utils.confidence import score_to_confidence

from src.core.logging import logger
from src.core.metrics import CHAT_REQUESTS, CHAT_LATENCY, CHAT_GUARDRAIL_BLOCKS
from src.core.ws_manager import manager
from src.services.workspace_service import (
    get_workspace_document_ids, user_can_access_workspace,
)

# Event emitter for WebSocket broadcasting
_event_emitter = None

def _get_event_emitter():
    """Get event emitter instance."""
    global _event_emitter
    if _event_emitter is None:
        try:
            from src.core.event_emitter import get_event_emitter
            _event_emitter = get_event_emitter()
        except ImportError:
            pass
    return _event_emitter


async def _emit_ws_event(event_type: str, data: dict = None, workspace_id: int = None, document_id: int = None, user_id: int = None):
    """Emit an event via WebSocket."""
    emitter = _get_event_emitter()
    if emitter:
        try:
            await emitter.emit(
                event_type=event_type,
                data=data or {},
                workspace_id=workspace_id,
                document_id=document_id,
                user_id=user_id,
                immediate=True,
            )
        except Exception as e:
            logger.error(f"Failed to emit WS event {event_type}: {e}")


def _event(event_type: str, **fields) -> str:
    """Every line of the chat stream is one JSON object + newline (NDJSON).
    The frontend reads it line by line -- this is what powers the live
    pipeline visualization and keeps status/tokens/citations unambiguous
    (no fragile string-delimiter parsing)."""
    return json.dumps({"type": event_type, **fields}) + "\n"


def chat(
    db: Session,
    question: str,
    current_user: User,
    document_id: int | None = None,
    workspace_id: int | None = None,
    explain_level: str | None = None,
    want_translation: bool = True,
):
    if not document_id and not workspace_id:
        raise HTTPException(status_code=400, detail="Provide either document_id or workspace_id.")

    CHAT_REQUESTS.inc()
    start_time = time.perf_counter()

    document = None
    workspace_document_ids: list[int] = []

    if workspace_id:
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace or not user_can_access_workspace(db, workspace, current_user):
            raise HTTPException(status_code=404, detail="Workspace not found.")
        workspace_document_ids = get_workspace_document_ids(db, workspace_id, current_user)
    else:
        document = (
            db.query(Document)
            .filter(Document.id == document_id, Document.owner_id == current_user.id)
            .first()
        )

    # Emit RAG query started event via WebSocket
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_emit_ws_event(
                "rag:query:started",
                {"message": f"Query started: {question[:100]}...", "question": question},
                workspace_id=workspace_id,
                document_id=document_id,
                user_id=current_user.id,
            ))
        else:
            loop.run_until_complete(_emit_ws_event(
                "rag:query:started",
                {"message": f"Query started: {question[:100]}...", "question": question},
                workspace_id=workspace_id,
                document_id=document_id,
                user_id=current_user.id,
            ))
    except Exception:
        pass

    def generate():

        yield _event("status", stage="upload_check", label="Document ready", done=True)

        # ---------------------------------------------------
        # Guardrails
        # ---------------------------------------------------
        yield _event("status", stage="guardrail", label="Checking message safety...")

        guardrail_result = check_user_message(question)

        if not guardrail_result.allowed:
            CHAT_GUARDRAIL_BLOCKS.inc()
            logger.info(
                "Blocked chat message by guardrail: user_id=%s document_id=%s workspace_id=%s",
                current_user.id, document_id, workspace_id,
            )
            db.add(Chat(
                question=question, answer=guardrail_result.reason,
                user_id=current_user.id, document_id=document_id, workspace_id=workspace_id,
                flagged_reason="prompt_injection",
            ))
            db.commit()
            yield _event("status", stage="guardrail", label="Blocked", done=True, blocked=True)
            yield _event("token", text=guardrail_result.reason)
            yield _event("done")
            return

        yield _event("status", stage="guardrail", label="Message OK", done=True)

        # ---------------------------------------------------
        # Conversation History
        # ---------------------------------------------------
        # Workspace chats are shared: every member sees and contributes to
        # the same thread (this is the actual "collaboration" -- a joint
        # conversation, not just shared file access). Single-document
        # chats stay private per user, as before.
        history_query = db.query(Chat)
        if workspace_id:
            history_query = history_query.filter(Chat.workspace_id == workspace_id)
        else:
            history_query = history_query.filter(
                Chat.user_id == current_user.id, Chat.document_id == document_id
            )

        history_rows = history_query.order_by(desc(Chat.id)).limit(5).all()
        history_rows.reverse()
        conversation = "".join(
            f"User: {t.question}\nAssistant: {t.answer}\n\n" for t in history_rows
        )

        # ---------------------------------------------------
        # Embed
        # ---------------------------------------------------
        yield _event("status", stage="embedding", label="Understanding your question...")
        question_embedding = generate_embeddings([question])[0]
        yield _event("status", stage="embedding", label="Question embedded", done=True)

        # Emit embedding event via WebSocket
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_emit_ws_event(
                    "rag:embedding",
                    {"message": "Query embedded"},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
            else:
                loop.run_until_complete(_emit_ws_event(
                    "rag:embedding",
                    {"message": "Query embedded"},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
        except Exception:
            pass

        # ---------------------------------------------------
        # Hybrid Retrieval
        # ---------------------------------------------------
        search_label = (
            "Searching workspace documents (vector + keyword)..."
            if workspace_id else "Searching document (vector + keyword)..."
        )
        yield _event("status", stage="retrieval", label=search_label)

        # Emit retrieval started via WebSocket
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_emit_ws_event(
                    "rag:retrieval:started",
                    {"message": search_label},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
            else:
                loop.run_until_complete(_emit_ws_event(
                    "rag:retrieval:started",
                    {"message": search_label},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
        except Exception:
            pass

        if workspace_id:
            documents, metadatas = hybrid_search_multi(
                query_embedding=question_embedding,
                query_text=question,
                document_ids=workspace_document_ids,
                n_results=20,
            )
        else:
            documents, metadatas = hybrid_search(
                query_embedding=question_embedding,
                query_text=question,
                document_id=document_id,
                n_results=20,
            )
        
        # Emit retrieval completed via WebSocket with chunks
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_emit_ws_event(
                    "rag:retrieval:completed",
                    {"message": f"Found {len(documents)} candidate passages", "chunks_count": len(documents)},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
            else:
                loop.run_until_complete(_emit_ws_event(
                    "rag:retrieval:completed",
                    {"message": f"Found {len(documents)} candidate passages", "chunks_count": len(documents)},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
        except Exception:
            pass

        yield _event(
            "status", stage="retrieval", done=True,
            label=f"Found {len(documents)} candidate passages",
        )

        # ---------------------------------------------------
        # Rerank
        # ---------------------------------------------------
        yield _event("status", stage="rerank", label="Reranking for relevance...")

        # Emit reranking started via WebSocket
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_emit_ws_event(
                    "rag:reranking:started",
                    {"message": "Reranking passages for relevance"},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
            else:
                loop.run_until_complete(_emit_ws_event(
                    "rag:reranking:started",
                    {"message": "Reranking passages for relevance"},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
        except Exception:
            pass

        documents, metadatas, scores = rerank(question=question, documents=documents, metadatas=metadatas, top_k=5)
        
        # Emit reranking completed via WebSocket
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_emit_ws_event(
                    "rag:reranking:completed",
                    {"message": f"Selected top {len(documents)} passages"},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
            else:
                loop.run_until_complete(_emit_ws_event(
                    "rag:reranking:completed",
                    {"message": f"Selected top {len(documents)} passages"},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
        except Exception:
            pass
        yield _event(
            "status", stage="rerank", done=True,
            label=f"Selected top {len(documents)} passages",
        )

        confidence = score_to_confidence(scores[0] if scores else None)
        yield _event("confidence", **confidence)

        # ---------------------------------------------------
        # Build Context + Citations
        # ---------------------------------------------------
        context = ""
        citations = []
        for doc, meta in zip(documents, metadatas):
            context += f"\nPage {meta['page']}\n{doc}\n"
            citations.append({
                "filename": meta.get("filename"),
                "page": meta.get("page"),
                "chunk": meta.get("chunk"),
                # First ~200 chars of the actual cited passage -- lets the
                # frontend PDF viewer search-and-highlight the real text
                # instead of just jumping to the page.
                "snippet": doc.strip()[:200],
            })

        seen = set()
        unique_citations = []
        for c in citations:
            key = (c["filename"], c["page"])
            if key not in seen:
                seen.add(key)
                unique_citations.append(c)

        if not context.strip():
            no_context_answer = "I couldn't find that in the selected document(s)."
            db.add(Chat(
                question=question, answer=no_context_answer,
                user_id=current_user.id, document_id=document_id, workspace_id=workspace_id,
                citations=json.dumps([]),
            ))
            db.commit()
            yield _event("token", text=no_context_answer)
            yield _event("done")
            return

        # ---------------------------------------------------
        # Generate (streamed)
        # ---------------------------------------------------
        doc_language_name = (document.language_name if document else None) or "English"

        # Emit generation started via WebSocket
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_emit_ws_event(
                    "rag:generation:started",
                    {"message": "Generating answer..."},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
            else:
                loop.run_until_complete(_emit_ws_event(
                    "rag:generation:started",
                    {"message": "Generating answer..."},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
        except Exception:
            pass

        yield _event("status", stage="generation", label=f"Generating answer ({doc_language_name})...")

        answer = ""
        for chunk in ask_llm(
            context=context, question=question, history=conversation,
            explain_level=explain_level,
            answer_language_name=doc_language_name if doc_language_name != "English" else None,
        ):
            answer += chunk
            yield _event("token", text=chunk)

        yield _event("status", stage="generation", done=True, label="Answer generated")
        yield _event("citations", citations=unique_citations)

        # ---------------------------------------------------
        # Optional second-language translation
        # ---------------------------------------------------
        if want_translation and doc_language_name != "English":
            yield _event("status", stage="translation", label="Preparing English translation...")
            try:
                translation_text = translate_text(answer, "English")
                yield _event(
                    "translation", language_code="en", language_name="English",
                    text=translation_text,
                )
            except Exception:
                logger.exception("Translation failed for document_id=%s", document_id)
            yield _event("status", stage="translation", done=True, label="Translation ready")

        db.add(Chat(
            question=question, answer=answer,
            user_id=current_user.id, document_id=document_id, workspace_id=workspace_id,
            citations=json.dumps(unique_citations),
        ))
        db.commit()

        CHAT_LATENCY.observe(time.perf_counter() - start_time)

        # Emit RAG completed via WebSocket
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_emit_ws_event(
                    "rag:completed",
                    {"message": "Query completed", "answer_length": len(answer), "citations_count": len(unique_citations)},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
            else:
                loop.run_until_complete(_emit_ws_event(
                    "rag:completed",
                    {"message": "Query completed", "answer_length": len(answer), "citations_count": len(unique_citations)},
                    workspace_id=workspace_id,
                    document_id=document_id,
                    user_id=current_user.id,
                ))
        except Exception:
            pass

        # Live collaboration: push the completed turn to every other
        # member currently connected to this workspace. Runs in a worker
        # thread (StreamingResponse iterates sync generators off the main
        # event loop), so asyncio.run() here starts its own short-lived
        # loop rather than conflicting with the app's main one.
        if workspace_id:
            try:
                asyncio.run(manager.broadcast(workspace_id, {
                    "type": "chat_message",
                    "user_id": current_user.id,
                    "user_name": current_user.full_name,
                    "question": question,
                    "answer": answer,
                    "citations": unique_citations,
                }))
            except Exception:
                logger.exception("Failed to broadcast chat message for workspace_id=%s", workspace_id)

        yield _event("done")

    return generate()


def get_chat_history(
    db: Session,
    current_user: User,
    document_id: int | None = None,
    workspace_id: int | None = None,
):
    if workspace_id:
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace or not user_can_access_workspace(db, workspace, current_user):
            raise HTTPException(status_code=404, detail="Workspace not found.")
        return (
            db.query(Chat)
            .filter(Chat.workspace_id == workspace_id)
            .order_by(Chat.id.asc())
            .all()
        )

    return (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id, Chat.document_id == document_id)
        .order_by(Chat.id.asc())
        .all()
    )
