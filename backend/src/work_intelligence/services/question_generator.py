"""
Question Generator

Generates intelligent suggested questions based on document content.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.work_intelligence.schemas import (
    QuestionGenerationRequest,
    GeneratedQuestion,
    QuestionGenerationResponse,
    DocumentType,
)
from src.models.document import Document
from src.knowledge.models import KnowledgeEntity, KnowledgeConcept, GeneratedQuestion as KGQuestion
from src.core.logging import logger


# Question templates by document type
QUESTION_TEMPLATES: Dict[DocumentType, List[Dict[str, str]]] = {
    DocumentType.INVOICE: [
        {"type": "factual", "template": "Who issued this invoice?", "action": None},
        {"type": "factual", "template": "What is the total amount due?", "action": "extract_line_items"},
        {"type": "factual", "template": "When is the payment due?", "action": None},
        {"type": "factual", "template": "What items were purchased?", "action": "extract_line_items"},
        {"type": "analysis", "template": "Are there any discrepancies in the line items?", "action": "analyze_document"},
        {"type": "action", "template": "Generate an Excel spreadsheet of these items", "action": "generate_excel"},
        {"type": "action", "template": "Create an accounting summary", "action": "generate_accounting_summary"},
        {"type": "action", "template": "Draft an email to the vendor", "action": "draft_email"},
    ],
    DocumentType.EMAIL: [
        {"type": "factual", "template": "Who sent this email?", "action": None},
        {"type": "factual", "template": "What is the main topic?", "action": "generate_summary"},
        {"type": "action", "template": "Extract action items from this email", "action": "extract_tasks"},
        {"type": "action", "template": "Draft a reply email", "action": "draft_email"},
        {"type": "action", "template": "Create a calendar event from this", "action": "create_calendar_event"},
    ],
    DocumentType.RESEARCH_PAPER: [
        {"type": "factual", "template": "What is the main research question?", "action": None},
        {"type": "factual", "template": "What are the key findings?", "action": None},
        {"type": "factual", "template": "What methodology was used?", "action": None},
        {"type": "conceptual", "template": "Explain this paper in simple terms", "action": "explain_simply"},
        {"type": "conceptual", "template": "What are the limitations of this study?", "action": None},
        {"type": "action", "template": "Create flashcards for studying", "action": "create_flashcards"},
        {"type": "action", "template": "Generate a quiz from this paper", "action": "create_quiz"},
        {"type": "action", "template": "Create a presentation summarizing this", "action": "create_presentation"},
        {"type": "action", "template": "Build a knowledge graph", "action": "build_knowledge_graph"},
        {"type": "action", "template": "Create a learning path", "action": "build_learning_path"},
    ],
    DocumentType.RESUME: [
        {"type": "factual", "template": "What is the candidate's professional summary?", "action": None},
        {"type": "factual", "template": "What are the key skills?", "action": None},
        {"type": "analysis", "template": "How well does this match the job description?", "action": "match_jobs"},
        {"type": "analysis", "template": "What ATS score would this resume receive?", "action": "analyze_ats"},
        {"type": "action", "template": "Suggest improvements for this resume", "action": "analyze_ats"},
        {"type": "action", "template": "Generate a cover letter", "action": "generate_cover_letter"},
        {"type": "action", "template": "Suggest relevant job positions", "action": "match_jobs"},
    ],
    DocumentType.CONTRACT: [
        {"type": "factual", "template": "What are the key terms of this contract?", "action": None},
        {"type": "factual", "template": "What are the termination conditions?", "action": None},
        {"type": "analysis", "template": "What are the main risks?", "action": "summarize_clauses"},
        {"type": "analysis", "template": "Are there any compliance issues?", "action": "check_compliance"},
        {"type": "action", "template": "Summarize the key clauses", "action": "summarize_clauses"},
        {"type": "action", "template": "Extract all obligations", "action": "extract_obligations"},
        {"type": "action", "template": "Generate a risk report", "action": "generate_risk_report"},
    ],
    DocumentType.MEETING_NOTES: [
        {"type": "factual", "template": "What were the main discussion points?", "action": None},
        {"type": "action", "template": "Extract all action items", "action": "extract_action_items"},
        {"type": "action", "template": "Create a timeline of events", "action": "generate_timeline"},
        {"type": "action", "template": "Generate a summary for absent team members", "action": "generate_summary"},
        {"type": "action", "template": "Send follow-up emails to attendees", "action": "send_follow_up_email"},
        {"type": "action", "template": "Create tasks from action items", "action": "create_tasks"},
    ],
    DocumentType.BUSINESS_REPORT: [
        {"type": "factual", "template": "What are the key metrics?", "action": None},
        {"type": "factual", "template": "What is the financial performance?", "action": None},
        {"type": "action", "template": "Extract all KPIs", "action": "extract_metrics"},
        {"type": "action", "template": "Create a presentation summarizing findings", "action": "create_presentation"},
        {"type": "action", "template": "Generate an executive summary", "action": "generate_summary"},
        {"type": "action", "template": "Track these metrics over time", "action": "track_kpis"},
    ],
    DocumentType.LECTURE_NOTES: [
        {"type": "conceptual", "template": "What are the main topics covered?", "action": None},
        {"type": "conceptual", "template": "What are the key concepts?", "action": None},
        {"type": "action", "template": "Create flashcards for studying", "action": "create_flashcards"},
        {"type": "action", "template": "Generate a quiz to test understanding", "action": "create_quiz"},
        {"type": "action", "template": "Create a learning path", "action": "build_learning_path"},
        {"type": "action", "template": "Summarize the lecture", "action": "generate_summary"},
    ],
    DocumentType.SPREADSHEET: [
        {"type": "factual", "template": "What data is in this spreadsheet?", "action": None},
        {"type": "analysis", "template": "What trends or patterns exist?", "action": "analyze_data"},
        {"type": "action", "template": "Create charts from this data", "action": "generate_charts"},
        {"type": "action", "template": "Generate a summary report", "action": "create_summary"},
        {"type": "action", "template": "Export as CSV", "action": "export_csv"},
    ],
    DocumentType.UNKNOWN: [
        {"type": "factual", "template": "What is this document about?", "action": "analyze_document"},
        {"type": "conceptual", "template": "Can you summarize this document?", "action": "generate_summary"},
        {"type": "action", "template": "What actions can I take with this?", "action": "suggest_actions"},
    ],
}


class QuestionGenerator:
    """
    Generator for intelligent suggested questions.
    
    Features:
    - Document type-aware question generation
    - Entity-based questions
    - Action-oriented questions
    - Difficulty levels
    """

    def __init__(self, db: Session):
        """Initialize the question generator."""
        self.db = db

    async def generate(
        self,
        request: QuestionGenerationRequest
    ) -> QuestionGenerationResponse:
        """
        Generate suggested questions.
        
        Args:
            request: Question generation request
            
        Returns:
            Generated questions
        """
        # Get document context
        content = request.content or ""
        document_type = request.document_type
        
        if request.document_id and not content:
            doc = self.db.query(Document).filter(
                Document.id == request.document_id
            ).first()
            
            if doc:
                content = doc.filename
                if doc.summary:
                    content += " " + (doc.summary.content or "")
        
        # Determine document type
        if not document_type:
            document_type = self._infer_document_type(content)
        
        # Generate questions
        questions = []
        
        # Get template questions
        templates = QUESTION_TEMPLATES.get(
            document_type,
            QUESTION_TEMPLATES[DocumentType.UNKNOWN]
        )
        
        # Filter by question types if specified
        if request.question_types:
            templates = [
                t for t in templates
                if t["type"] in request.question_types
            ]
        
        # Add template questions
        for template in templates[:request.max_questions]:
            questions.append(GeneratedQuestion(
                question=template["template"],
                type=template["type"],
                context="Document content",
                difficulty=self._get_difficulty(template["type"]),
                related_action=template.get("action")
            ))
        
        # Add entity-based questions if available
        if request.document_id:
            entity_questions = await self._generate_entity_questions(
                request.document_id,
                request.max_questions - len(questions)
            )
            questions.extend(entity_questions)
        
        return QuestionGenerationResponse(
            questions=questions[:request.max_questions],
            total_count=len(questions),
            document_id=request.document_id
        )

    async def _generate_entity_questions(
        self,
        document_id: int,
        max_count: int
    ) -> List[GeneratedQuestion]:
        """Generate questions based on extracted entities."""
        questions = []
        
        # Get entities
        entities = self.db.query(KnowledgeEntity).filter(
            KnowledgeEntity.document_id == document_id
        ).limit(10).all()
        
        for entity in entities[:max_count]:
            entity_name = entity.name
            entity_type = str(entity.entity_type.value if hasattr(entity.entity_type, 'value') else entity.entity_type)
            
            # Generate appropriate question
            if entity_type in ["person", "PERSON"]:
                questions.append(GeneratedQuestion(
                    question=f"Tell me more about {entity_name}",
                    type="conceptual",
                    context=f"Related to person: {entity_name}",
                    difficulty="intermediate",
                    related_action="explain_detailed"
                ))
            elif entity_type in ["organization", "ORGANIZATION", "company", "COMPANY"]:
                questions.append(GeneratedQuestion(
                    question=f"What is {entity_name} and what do they do?",
                    type="conceptual",
                    context=f"Related to organization: {entity_name}",
                    difficulty="intermediate",
                    related_action="explain_detailed"
                ))
            elif entity_type in ["technology", "TECHNOLOGY"]:
                questions.append(GeneratedQuestion(
                    question=f"Explain {entity_name} in detail",
                    type="conceptual",
                    context=f"Related to technology: {entity_name}",
                    difficulty="advanced",
                    related_action="explain_detailed"
                ))
        
        # Get concepts
        concepts = self.db.query(KnowledgeConcept).filter(
            KnowledgeConcept.document_id == document_id
        ).limit(5).all()
        
        for concept in concepts[:max(0, max_count - len(entities))]:
            questions.append(GeneratedQuestion(
                question=f"What is {concept.name}?",
                type="conceptual",
                context=concept.description or "Document concept",
                difficulty="intermediate",
                related_action="explain_detailed"
            ))
        
        return questions

    def _infer_document_type(self, content: str) -> DocumentType:
        """Infer document type from content."""
        content_lower = content.lower()
        
        # Check for keywords
        if any(kw in content_lower for kw in ["invoice", "amount due", "line item"]):
            return DocumentType.INVOICE
        elif any(kw in content_lower for kw in ["meeting", "action items", "attendees"]):
            return DocumentType.MEETING_NOTES
        elif any(kw in content_lower for kw in ["abstract", "methodology", "results", "conclusion"]):
            return DocumentType.RESEARCH_PAPER
        elif any(kw in content_lower for kw in ["resume", "experience", "skills", "education"]):
            return DocumentType.RESUME
        elif any(kw in content_lower for kw in ["contract", "agreement", "party", "shall"]):
            return DocumentType.CONTRACT
        elif any(kw in content_lower for kw in ["from:", "to:", "subject:", "sent:"]):
            return DocumentType.EMAIL
        elif any(kw in content_lower for kw in ["executive summary", "revenue", "profit", "kpi"]):
            return DocumentType.BUSINESS_REPORT
        elif any(kw in content_lower for kw in ["lecture", "course", "chapter"]):
            return DocumentType.LECTURE_NOTES
        
        return DocumentType.UNKNOWN

    def _get_difficulty(self, question_type: str) -> str:
        """Get difficulty based on question type."""
        difficulty_map = {
            "factual": "beginner",
            "conceptual": "intermediate",
            "analysis": "intermediate",
            "action": "beginner",
        }
        return difficulty_map.get(question_type, "intermediate")


def get_question_generator(db: Session) -> QuestionGenerator:
    """Get question generator instance."""
    return QuestionGenerator(db)
