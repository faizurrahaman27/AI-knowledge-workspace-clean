from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.services.document_service import get_owned_document
from src.utils.vector_store import get_document_chunks_sample
from src.utils.llm import classify_intent, generate_study_content, generate_mindmap
from src.utils.pdf_export import build_study_pack_pdf
from src.utils.autonomous_agent import run_autonomous_agent, MAX_STEPS
from src.core.logging import logger

router = APIRouter(prefix="/agent", tags=["Orchestrator"])


class AgentRequest(BaseModel):
    document_id: int
    request_text: str


class AgentResponse(BaseModel):
    intent: str
    # Populated for intents this orchestrator can fully resolve itself
    # (summary/quiz). For "question"/"compare"/"mindmap" the frontend
    # routes to the matching dedicated endpoint (/chat, /compare, /mindmap)
    # using `intent` -- streaming and multi-document inputs don't fit a
    # single JSON response.
    result: str | None = None


INTENT_TO_STUDY_MODE = {
    "summary": "summary",
    "quiz": "quiz",
}


@router.post("/", response_model=AgentResponse)
def route_request(
    request: AgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    A single-LLM-call router: classifies what the user is actually asking
    for, then either resolves it directly (summary/quiz) or tells the
    frontend which specialist endpoint to call next. This is intentionally
    a simple orchestrator pattern, not multiple autonomous agents -- see
    README for why that distinction matters.
    """
    get_owned_document(db, request.document_id, current_user)  # ownership check

    intent = classify_intent(request.request_text)

    if intent in INTENT_TO_STUDY_MODE:
        chunks, metadatas = get_document_chunks_sample(request.document_id, max_chunks=40)
        if not chunks:
            raise HTTPException(status_code=422, detail="This document has no processed content yet.")
        context = "\n\n".join(f"[Page {m.get('page')}] {c}" for c, m in zip(chunks, metadatas))
        result = generate_study_content(context=context, mode=INTENT_TO_STUDY_MODE[intent])
        return AgentResponse(intent=intent, result=result)

    return AgentResponse(intent=intent, result=None)


class AutonomousAgentResponse(BaseModel):
    answer: str
    trace: list[dict]
    incomplete: bool


@router.post("/auto", response_model=AutonomousAgentResponse)
def run_autonomous(
    request: AgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Real autonomous planning: the model decides, turn by turn, which tool
    to call (search / summarize / quiz / flashcards / mindmap) and in
    what order, based on the actual request -- unlike /study-pack above,
    which always runs the same five steps regardless of what was asked.
    See utils/autonomous_agent.py's module docstring for the distinction
    and why LLM_PROVIDER=ollama isn't supported here.

    `trace` is returned so the caller can see exactly which tools were
    called and why -- this is a transparency feature, not a UI nicety:
    an agent that can take actions on your data should show its work.
    """
    return run_autonomous_agent(db, request.document_id, current_user, request.request_text)


class StudyPackResponse(BaseModel):
    document_title: str
    summary: str
    important_questions: str
    flashcards: str
    quiz: str
    mindmap: str  # raw JSON string from generate_mindmap


def _generate_study_pack_sections(db: Session, document_id: int, current_user: User):
    document = get_owned_document(db, document_id, current_user)

    chunks, metadatas = get_document_chunks_sample(document_id, max_chunks=40)
    if not chunks:
        raise HTTPException(status_code=422, detail="This document has no processed content yet.")

    context = "\n\n".join(f"[Page {m.get('page')}] {c}" for c, m in zip(chunks, metadatas))

    # Sequential chain: each step is its own LLM call, run one after
    # another. This is the "AI Agent" workflow from the roadmap -- a
    # fixed, predictable pipeline (not a planner that decides its own
    # steps), which is an honest description of what's implemented.
    summary = generate_study_content(context=context, mode="summary")
    important_questions = generate_study_content(context=context, mode="important_questions")
    flashcards = generate_study_content(context=context, mode="flashcards")
    quiz = generate_study_content(context=context, mode="quiz")

    try:
        mindmap = generate_mindmap(context=context, topic_hint=document.filename)
    except Exception:
        logger.exception("Mindmap generation failed in study pack (document_id=%s)", document_id)
        mindmap = '{"title": "Mind map unavailable", "children": []}'

    return document, {
        "summary": summary,
        "important_questions": important_questions,
        "flashcards": flashcards,
        "quiz": quiz,
        "mindmap": mindmap,
    }


@router.post("/study-pack", response_model=StudyPackResponse)
def full_study_pack(
    request: AgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Chained workflow: Summary -> Important Questions -> Flashcards -> Quiz
    -> Mind Map, all in one call. `request_text` is accepted for symmetry
    with the router endpoint but not currently used to customize the
    pack -- every section is always generated.
    """
    document, sections = _generate_study_pack_sections(db, request.document_id, current_user)
    return StudyPackResponse(document_title=document.filename, **sections)


@router.get("/study-pack/{document_id}/pdf")
def full_study_pack_pdf(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Same chained workflow as POST /agent/study-pack, rendered straight
    to a downloadable PDF instead of JSON."""
    document, sections = _generate_study_pack_sections(db, document_id, current_user)

    pdf_bytes = build_study_pack_pdf(
        document_title=f"Study Pack: {document.filename}",
        sections=[
            ("Summary", sections["summary"]),
            ("Important Questions", sections["important_questions"]),
            ("Flashcards", sections["flashcards"]),
            ("Quiz", sections["quiz"]),
        ],
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="study_pack_{document_id}.pdf"'},
    )
