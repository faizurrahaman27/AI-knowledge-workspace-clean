"""
Recommendation Engine

Generates AI-powered recommendations for actions based on context.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.work_intelligence.schemas import (
    RecommendationRequest,
    Recommendation,
    RecommendationResponse,
    DocumentType,
    ActionCategory,
)
from src.work_intelligence.services.action_registry import get_action_registry
from src.work_intelligence.services.document_classifier import get_document_classifier
from src.models.document import Document
from src.core.logging import logger


# Action priority scores based on document type
ACTION_PRIORITY_MAP: Dict[DocumentType, Dict[str, int]] = {
    DocumentType.INVOICE: {
        "extract_line_items": 10,
        "generate_excel": 9,
        "generate_accounting_summary": 8,
        "create_email": 7,
        "translate": 6,
    },
    DocumentType.EMAIL: {
        "draft_email": 10,
        "extract_tasks": 9,
        "generate_summary": 8,
        "create_calendar_event": 7,
    },
    DocumentType.RESEARCH_PAPER: {
        "create_presentation": 10,
        "create_flashcards": 9,
        "create_quiz": 8,
        "build_knowledge_graph": 7,
        "build_learning_path": 6,
    },
    DocumentType.RESUME: {
        "analyze_ats": 10,
        "match_jobs": 9,
        "generate_cover_letter": 8,
    },
    DocumentType.CONTRACT: {
        "summarize_clauses": 10,
        "extract_obligations": 9,
        "check_compliance": 8,
        "generate_risk_report": 7,
    },
    DocumentType.MEETING_NOTES: {
        "extract_action_items": 10,
        "generate_timeline": 9,
        "create_tasks": 8,
        "send_follow_up_email": 7,
    },
    DocumentType.SPREADSHEET: {
        "analyze_data": 10,
        "generate_charts": 9,
        "create_summary": 8,
        "export_csv": 7,
    },
    DocumentType.BUSINESS_REPORT: {
        "generate_summary": 10,
        "extract_metrics": 9,
        "create_presentation": 8,
        "track_kpis": 7,
    },
    DocumentType.LECTURE_NOTES: {
        "create_flashcards": 10,
        "create_quiz": 9,
        "build_learning_path": 8,
        "generate_summary": 7,
    },
    DocumentType.UNKNOWN: {
        "analyze_document": 10,
        "generate_summary": 8,
        "suggest_actions": 6,
    },
}

# Default action priorities
DEFAULT_ACTION_PRIORITIES: Dict[str, int] = {
    "analyze_document": 8,
    "generate_insights": 7,
    "extract_entities": 6,
    "translate_document": 5,
    "export_pdf": 4,
}


class RecommendationEngine:
    """
    Engine for generating action recommendations.
    
    Considers:
    - Document type
    - Document content
    - User history
    - Workspace context
    - Language
    """

    def __init__(self, db: Session):
        """Initialize the recommendation engine."""
        self.db = db
        self.action_registry = get_action_registry()
        self.document_classifier = get_document_classifier(db)

    async def recommend(
        self,
        request: RecommendationRequest
    ) -> RecommendationResponse:
        """
        Generate recommendations.
        
        Args:
            request: Recommendation request
            
        Returns:
            Recommendations response
        """
        # Classify document if not provided
        document_type = None
        language = None
        
        if request.document_id:
            doc = self.db.query(Document).filter(
                Document.id == request.document_id
            ).first()
            
            if doc:
                document_type = self._infer_document_type(doc)
                language = doc.language_code
        
        # Use context if provided
        if request.context:
            document_type = request.context.get("document_type", document_type)
            language = request.context.get("language", language)
        
        # Get document type from enum
        doc_type = None
        if document_type:
            try:
                doc_type = DocumentType(document_type.lower()) if isinstance(document_type, str) else document_type
            except ValueError:
                pass
        
        # Generate recommendations
        recommendations = []
        
        if doc_type and doc_type in ACTION_PRIORITY_MAP:
            # Use document-specific priorities
            priorities = ACTION_PRIORITY_MAP[doc_type]
            
            for action_id, priority in priorities.items():
                action = self.action_registry.get_action(action_id)
                if action:
                    # Check language support
                    if language and language not in action.supported_languages:
                        continue
                    
                    recommendations.append(Recommendation(
                        action_id=action.id,
                        title=action.title,
                        description=action.description,
                        reason=f"Recommended for {doc_type.value}",
                        confidence=min(priority / 10, 0.95),
                        priority=priority,
                        category=action.category,
                        workflow_id=action.workflow_id,
                        estimated_duration_seconds=action.estimated_duration_seconds,
                        icon=action.icon
                    ))
        else:
            # Use default priorities
            for action_id, priority in DEFAULT_ACTION_PRIORITIES.items():
                action = self.action_registry.get_action(action_id)
                if action:
                    recommendations.append(Recommendation(
                        action_id=action.id,
                        title=action.title,
                        description=action.description,
                        reason="General recommendation",
                        confidence=0.5,
                        priority=priority,
                        category=action.category,
                        workflow_id=action.workflow_id,
                        estimated_duration_seconds=action.estimated_duration_seconds,
                        icon=action.icon
                    ))
        
        # Sort by priority and confidence
        recommendations.sort(
            key=lambda r: (r.priority * 0.6 + r.confidence * 10 * 0.4),
            reverse=True
        )
        
        # Limit results
        recommendations = recommendations[:request.max_recommendations]
        
        return RecommendationResponse(
            recommendations=recommendations,
            total_count=len(recommendations)
        )

    def _infer_document_type(self, doc: Document) -> str:
        """Infer document type from document metadata."""
        content_type = doc.content_type or ""
        filename = doc.filename.lower()
        
        # Check content type
        if "pdf" in content_type or filename.endswith(".pdf"):
            return "research_paper"  # Default for PDFs
        elif "image" in content_type:
            return "scanned_document"
        elif "spreadsheet" in content_type or filename.endswith((".xlsx", ".xls", ".csv")):
            return "spreadsheet"
        elif "presentation" in content_type or filename.endswith((".pptx", ".ppt")):
            return "presentation"
        elif "document" in content_type or filename.endswith((".docx", ".doc")):
            return "unknown"
        
        # Default
        return "unknown"

    async def recommend_for_intent(
        self,
        intent_category: str,
        document_type: Optional[str] = None,
        language: Optional[str] = None,
        max_recommendations: int = 5
    ) -> List[Recommendation]:
        """
        Generate recommendations for a specific intent.
        
        Args:
            intent_category: User's intent category
            document_type: Document type
            language: Document language
            max_recommendations: Maximum recommendations
            
        Returns:
            List of recommendations
        """
        # Map intent to actions
        intent_action_map = {
            "analyze": ["analyze_document", "generate_insights", "extract_entities"],
            "create": ["generate_summary", "create_presentation", "create_flashcards"],
            "extract": ["extract_line_items", "extract_tasks", "extract_obligations"],
            "translate": ["translate_document"],
            "compare": ["compare_documents"],
            "summarize": ["generate_summary", "summarize_clauses"],
            "explain": ["explain_simply", "explain_detailed"],
            "generate": ["generate_excel", "generate_csv", "generate_cover_letter"],
            "export": ["export_pdf", "export_csv"],
            "communicate": ["draft_email", "send_follow_up_email"],
            "plan": ["generate_timeline", "build_learning_path"],
            "review": ["analyze_ats", "summarize_clauses"],
            "track": ["track_progress", "extract_metrics"],
        }
        
        action_ids = intent_action_map.get(intent_category.lower(), ["analyze_document"])
        recommendations = []
        
        for action_id in action_ids:
            action = self.action_registry.get_action(action_id)
            if action:
                # Check document type support
                if document_type:
                    try:
                        doc_type = DocumentType(document_type.lower())
                        if doc_type not in action.supported_document_types:
                            continue
                    except ValueError:
                        pass
                
                # Check language support
                if language and language not in action.supported_languages:
                    continue
                
                recommendations.append(Recommendation(
                    action_id=action.id,
                    title=action.title,
                    description=action.description,
                    reason=f"Matches your intent: {intent_category}",
                    confidence=0.85,
                    priority=8,
                    category=action.category,
                    workflow_id=action.workflow_id,
                    estimated_duration_seconds=action.estimated_duration_seconds,
                    icon=action.icon
                ))
        
        return recommendations[:max_recommendations]


def get_recommendation_engine(db: Session) -> RecommendationEngine:
    """Get recommendation engine instance."""
    return RecommendationEngine(db)
