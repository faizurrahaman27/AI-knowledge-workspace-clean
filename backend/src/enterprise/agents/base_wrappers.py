"""
Base Agent Wrappers

Provides agent implementations that wrap existing service functions
and expose them through the enterprise agent interface.

These agents provide backward compatibility with existing functionality
while enabling agent orchestration.
"""

import time
from typing import Optional

from src.enterprise.orchestrator.base import (
    BaseAgent,
    AgentMetadata,
    AgentContext,
    AgentResult,
    AgentCapability,
    AgentStatus,
)
from src.core.logging import logger


class ChatAgent(BaseAgent):
    """
    Agent wrapper for RAG chat functionality.
    
    Wraps the existing chat service to provide:
    - Question answering from documents
    - Multi-document reasoning
    - Streaming responses (via orchestrator events)
    """
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            agent_id="chat_agent",
            name="RAG Chat Agent",
            description="Answers questions about documents using retrieval-augmented generation",
            version="1.0.0",
            capabilities=[
                AgentCapability.QUESTION_ANSWERING,
                AgentCapability.SEMANTIC_SEARCH,
                AgentCapability.MULTI_DOCUMENT_REASONING,
            ],
            max_concurrent_tasks=10,
            tags=["rag", "chat", "qa", "documents"]
        )
    
    async def execute(self, context: AgentContext) -> AgentResult:
        start_time = time.time()
        
        try:
            question = context.parameters.get("question", "")
            document_ids = context.parameters.get("document_ids", context.document_ids)
            workspace_id = context.workspace_id or context.parameters.get("workspace_id")
            explain_level = context.parameters.get("explain_level")
            want_translation = context.parameters.get("want_translation", True)
            
            if not question:
                return AgentResult(
                    success=False,
                    error="No question provided",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # Import and use existing chat service
            from src.services.chat_service import chat
            from src.db.database import SessionLocal
            
            db = SessionLocal()
            try:
                # Get user
                from src.models.user import User
                user = db.query(User).filter(User.id == context.user_id).first()
                
                if not user:
                    return AgentResult(
                        success=False,
                        error="User not found",
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                
                # Build response chunks
                chunks = []
                async for chunk in chat(
                    db=db,
                    question=question,
                    document_id=document_ids[0] if document_ids and not workspace_id else None,
                    workspace_id=workspace_id,
                    current_user=user,
                    explain_level=explain_level,
                    want_translation=want_translation,
                ):
                    chunks.append(chunk)
                
                return AgentResult(
                    success=True,
                    output={"chunks": chunks, "question": question},
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    artifacts={"document_ids": document_ids, "workspace_id": workspace_id}
                )
            finally:
                db.close()
                
        except Exception as e:
            logger.exception(f"ChatAgent error: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )


class DocumentAgent(BaseAgent):
    """
    Agent wrapper for document processing.
    
    Handles:
    - PDF upload and processing
    - Web extraction
    - GitHub integration
    - OCR from images
    """
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            agent_id="document_agent",
            name="Document Processing Agent",
            description="Ingests and processes documents from various sources",
            version="1.0.0",
            capabilities=[
                AgentCapability.PDF_PROCESSING,
                AgentCapability.WEB_EXTRACTION,
                AgentCapability.GITHUB_INTEGRATION,
                AgentCapability.OCR_PROCESSING,
            ],
            max_concurrent_tasks=5,
            requires_api_keys=["GROQ_API_KEY"],
            tags=["documents", "ingestion", "pdf", "ocr"]
        )
    
    async def execute(self, context: AgentContext) -> AgentResult:
        start_time = time.time()
        
        try:
            source_type = context.parameters.get("source_type")
            source_data = context.parameters.get("source_data", {})
            
            if source_type == "pdf_upload":
                # Handle PDF upload
                file_path = source_data.get("file_path")
                original_name = source_data.get("filename", "upload.pdf")
                
                from src.services.document_service import _ingest_pdf_file
                from src.db.database import SessionLocal
                from src.models.user import User
                
                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.id == context.user_id).first()
                    if not user:
                        return AgentResult(success=False, error="User not found")
                    
                    import os
                    size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    
                    doc = _ingest_pdf_file(
                        db, file_path, original_name, size, user
                    )
                    
                    return AgentResult(
                        success=True,
                        output={"document_id": doc.id, "filename": doc.filename},
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                finally:
                    db.close()
            
            elif source_type == "web_url":
                from src.services.document_service import ingest_from_url
                from src.db.database import SessionLocal
                from src.models.user import User
                
                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.id == context.user_id).first()
                    if not user:
                        return AgentResult(success=False, error="User not found")
                    
                    doc = ingest_from_url(db, source_data["url"], user)
                    
                    return AgentResult(
                        success=True,
                        output={"document_id": doc.id, "filename": doc.filename},
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                finally:
                    db.close()
            
            elif source_type == "github_file":
                from src.services.document_service import ingest_from_github
                from src.db.database import SessionLocal
                from src.models.user import User
                
                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.id == context.user_id).first()
                    if not user:
                        return AgentResult(success=False, error="User not found")
                    
                    doc = ingest_from_github(db, source_data["url"], user)
                    
                    return AgentResult(
                        success=True,
                        output={"document_id": doc.id, "filename": doc.filename},
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                finally:
                    db.close()
            
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown source_type: {source_type}",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
                
        except Exception as e:
            logger.exception(f"DocumentAgent error: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )


class FlashcardAgent(BaseAgent):
    """
    Agent for flashcard generation and review scheduling.
    """
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            agent_id="flashcard_agent",
            name="Flashcard Agent",
            description="Generates flashcards and manages spaced repetition reviews",
            version="1.0.0",
            capabilities=[
                AgentCapability.FLASHCARD_GENERATION,
                AgentCapability.SPACED_REPETITION,
            ],
            max_concurrent_tasks=5,
            tags=["flashcards", "study", "spaced_repetition"]
        )
    
    async def execute(self, context: AgentContext) -> AgentResult:
        start_time = time.time()
        
        try:
            document_id = context.parameters.get("document_id") or (context.document_ids[0] if context.document_ids else None)
            action = context.parameters.get("action", "generate")
            count = context.parameters.get("count", 10)
            
            if not document_id:
                return AgentResult(
                    success=False,
                    error="No document_id provided",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            from src.services.flashcard_service import (
                generate_and_save_flashcards,
                get_due_flashcards,
                review_flashcard
            )
            from src.db.database import SessionLocal
            from src.models.user import User
            
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == context.user_id).first()
                if not user:
                    return AgentResult(success=False, error="User not found")
                
                if action == "generate":
                    cards = generate_and_save_flashcards(db, document_id, user, count=count)
                    return AgentResult(
                        success=True,
                        output={"flashcard_count": len(cards), "card_ids": [c.id for c in cards]},
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        artifacts={"document_id": document_id}
                    )
                
                elif action == "get_due":
                    cards = get_due_flashcards(db, user, document_id=document_id)
                    return AgentResult(
                        success=True,
                        output={"due_cards": len(cards)},
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                
                elif action == "review":
                    flashcard_id = context.parameters.get("flashcard_id")
                    grade = context.parameters.get("grade")
                    
                    if not flashcard_id or not grade:
                        return AgentResult(
                            success=False,
                            error="flashcard_id and grade required for review"
                        )
                    
                    card = review_flashcard(db, flashcard_id, user, grade)
                    return AgentResult(
                        success=True,
                        output={"next_review": str(card.due_at)},
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                
                else:
                    return AgentResult(
                        success=False,
                        error=f"Unknown action: {action}",
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.exception(f"FlashcardAgent error: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )


class MindmapAgent(BaseAgent):
    """
    Agent for mind map and concept map generation.
    """
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            agent_id="mindmap_agent",
            name="Mind Map Agent",
            description="Generates visual mind maps and concept maps from documents",
            version="1.0.0",
            capabilities=[
                AgentCapability.MINDMAP_GENERATION,
                AgentCapability.DOCUMENT_SUMMARIZATION,
            ],
            max_concurrent_tasks=5,
            tags=["mindmap", "visualization", "concepts"]
        )
    
    async def execute(self, context: AgentContext) -> AgentResult:
        start_time = time.time()
        
        try:
            document_id = context.parameters.get("document_id") or (context.document_ids[0] if context.document_ids else None)
            workspace_id = context.workspace_id or context.parameters.get("workspace_id")
            
            if document_id:
                from src.api.mindmap import create_mindmap
                from src.schemas.mindmap import MindmapRequest
                from src.db.database import SessionLocal
                from src.models.user import User
                
                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.id == context.user_id).first()
                    if not user:
                        return AgentResult(success=False, error="User not found")
                    
                    request = MindmapRequest(document_id=document_id)
                    mindmap = create_mindmap(request, db, user)
                    
                    return AgentResult(
                        success=True,
                        output=mindmap,
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        artifacts={"document_id": document_id, "type": "mindmap"}
                    )
                finally:
                    db.close()
            
            elif workspace_id:
                from src.api.mindmap import create_workspace_knowledge_graph
                from src.schemas.mindmap import WorkspaceMindmapRequest
                from src.db.database import SessionLocal
                from src.models.user import User
                
                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.id == context.user_id).first()
                    if not user:
                        return AgentResult(success=False, error="User not found")
                    
                    request = WorkspaceMindmapRequest(workspace_id=workspace_id)
                    graph = create_workspace_knowledge_graph(request, db, user)
                    
                    return AgentResult(
                        success=True,
                        output=graph,
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        artifacts={"workspace_id": workspace_id, "type": "knowledge_graph"}
                    )
                finally:
                    db.close()
            
            else:
                return AgentResult(
                    success=False,
                    error="No document_id or workspace_id provided",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
                
        except Exception as e:
            logger.exception(f"MindmapAgent error: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )


class StudyPackAgent(BaseAgent):
    """
    Agent for generating comprehensive study packs.
    
    Combines multiple study tools in a predefined workflow.
    """
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            agent_id="study_pack_agent",
            name="Study Pack Agent",
            description="Generates comprehensive study packs including summaries, flashcards, quizzes, and mind maps",
            version="1.0.0",
            capabilities=[
                AgentCapability.DOCUMENT_SUMMARIZATION,
                AgentCapability.QUIZ_GENERATION,
                AgentCapability.FLASHCARD_GENERATION,
                AgentCapability.MINDMAP_GENERATION,
                AgentCapability.NOTES_GENERATION,
            ],
            max_concurrent_tasks=3,
            tags=["study", "education", "comprehensive"]
        )
    
    async def execute(self, context: AgentContext) -> AgentResult:
        start_time = time.time()
        
        try:
            document_id = context.parameters.get("document_id") or (context.document_ids[0] if context.document_ids else None)
            
            if not document_id:
                return AgentResult(
                    success=False,
                    error="No document_id provided",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            from src.api.agent import _generate_study_pack_sections
            from src.db.database import SessionLocal
            from src.models.user import User
            
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == context.user_id).first()
                if not user:
                    return AgentResult(success=False, error="User not found")
                
                document, sections = _generate_study_pack_sections(db, document_id, user)
                
                return AgentResult(
                    success=True,
                    output={
                        "document_title": document.filename,
                        "summary": sections.get("summary", ""),
                        "questions": sections.get("important_questions", ""),
                        "flashcards": sections.get("flashcards", ""),
                        "quiz": sections.get("quiz", ""),
                        "mindmap": sections.get("mindmap", "")
                    },
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    artifacts={
                        "document_id": document_id,
                        "sections": list(sections.keys())
                    }
                )
            finally:
                db.close()
                
        except Exception as e:
            logger.exception(f"StudyPackAgent error: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )


class CompareAgent(BaseAgent):
    """
    Agent for comparing documents and sources.
    """
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            agent_id="compare_agent",
            name="Document Comparison Agent",
            description="Compares multiple documents and identifies similarities and differences",
            version="1.0.0",
            capabilities=[
                AgentCapability.COMPARATIVE_ANALYSIS,
                AgentCapability.MULTI_DOCUMENT_REASONING,
            ],
            max_concurrent_tasks=5,
            tags=["comparison", "analysis", "documents"]
        )
    
    async def execute(self, context: AgentContext) -> AgentResult:
        start_time = time.time()
        
        try:
            doc_a_id = context.parameters.get("document_id_a")
            doc_b_id = context.parameters.get("document_id_b")
            question = context.parameters.get("question", "Compare these documents")
            
            if not doc_a_id or not doc_b_id:
                return AgentResult(
                    success=False,
                    error="Both document_id_a and document_id_b required",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            from src.api.compare import _get_context
            from src.utils.llm import compare_documents
            from src.services.document_service import get_owned_document
            from src.db.database import SessionLocal
            from src.models.user import User
            
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == context.user_id).first()
                if not user:
                    return AgentResult(success=False, error="User not found")
                
                doc_a = get_owned_document(db, doc_a_id, user)
                doc_b = get_owned_document(db, doc_b_id, user)
                
                # Get context from both documents
                context_a = _get_context(question, doc_a_id)
                context_b = _get_context(question, doc_b_id)
                
                # Generate comparison
                comparison_chunks = []
                for chunk in compare_documents(
                    context_a, context_b,
                    doc_a.filename, doc_b.filename,
                    question
                ):
                    comparison_chunks.append(chunk)
                
                return AgentResult(
                    success=True,
                    output={"comparison": "".join(comparison_chunks)},
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    artifacts={
                        "document_ids": [doc_a_id, doc_b_id],
                        "documents": [doc_a.filename, doc_b.filename]
                    }
                )
            finally:
                db.close()
                
        except Exception as e:
            logger.exception(f"CompareAgent error: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )


class ScanAgent(BaseAgent):
    """
    Agent for OCR scanning and image understanding.
    """
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            agent_id="scan_agent",
            name="Scan & OCR Agent",
            description="Processes scanned documents and images using OCR and vision models",
            version="1.0.0",
            capabilities=[
                AgentCapability.OCR_PROCESSING,
                AgentCapability.VIDEO_TRANSCRIPTION,  # Reusing for image understanding
            ],
            max_concurrent_tasks=5,
            tags=["ocr", "scanning", "images", "vision"]
        )
    
    async def execute(self, context: AgentContext) -> AgentResult:
        start_time = time.time()
        
        try:
            action = context.parameters.get("action", "analyze")
            language_code = context.parameters.get("language_code")
            
            if action == "analyze":
                file_path = context.parameters.get("file_path")
                
                if not file_path:
                    return AgentResult(
                        success=False,
                        error="file_path required for analysis",
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                
                from src.services.scan_service import analyze_scan
                import tempfile
                from pathlib import Path
                
                # Create a mock UploadFile for analyze_scan
                class MockUploadFile:
                    def __init__(self, path):
                        self.filename = Path(path).name
                        self.file = open(path, "rb")
                
                mock_file = MockUploadFile(file_path)
                try:
                    result = analyze_scan(mock_file, language_code=language_code)
                    
                    return AgentResult(
                        success=True,
                        output={
                            "text": result.extracted_text,
                            "summary": result.summary,
                            "language": result.language_name
                        },
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                finally:
                    mock_file.file.close()
            
            elif action == "understand_visual":
                file_path = context.parameters.get("file_path")
                question = context.parameters.get("question")
                
                if not file_path:
                    return AgentResult(
                        success=False,
                        error="file_path required for visual understanding",
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                
                from src.utils.vision import describe_visual
                
                description = describe_visual(file_path, question)
                
                return AgentResult(
                    success=True,
                    output={"description": description},
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown action: {action}",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
                
        except Exception as e:
            logger.exception(f"ScanAgent error: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
