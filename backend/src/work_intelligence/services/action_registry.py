"""
Action Registry

Plugin architecture for AI-powered actions.
Each action registers itself with the registry and can be executed dynamically.
"""

from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio

from sqlalchemy.orm import Session

from src.work_intelligence.schemas import (
    ActionDefinition,
    ActionCategory,
    DocumentType,
    OutputType,
    ActionExecutionRequest,
    ActionExecutionResponse,
)
from src.core.logging import logger


@dataclass
class ActionHandler:
    """Handler for an action."""
    definition: ActionDefinition
    handler_func: Callable
    workflow_steps: Optional[List[Dict[str, Any]]] = None
    requires_document: bool = True
    requires_auth: bool = True
    enabled: bool = True


class ActionRegistry:
    """
    Registry for all available actions.
    
    Features:
    - Plugin architecture
    - Dynamic registration
    - Action execution
    - Workflow generation
    """

    def __init__(self):
        """Initialize the action registry."""
        self._actions: Dict[str, ActionHandler] = {}
        self._categories: Dict[ActionCategory, List[str]] = {}
        self._document_type_actions: Dict[DocumentType, List[str]] = {}
        self._initialize_default_actions()

    def _initialize_default_actions(self) -> None:
        """Initialize default actions."""
        # Document Analysis Actions
        self.register(ActionDefinition(
            id="analyze_document",
            title="Analyze Document",
            description="Perform comprehensive analysis of the document",
            icon="search",
            category=ActionCategory.ANALYSIS,
            supported_document_types=list(DocumentType),
            supported_languages=["en", "es", "fr", "de", "ar", "hi", "zh"],
            required_permissions=["read"],
            estimated_duration_seconds=30,
            output_type=OutputType.MARKDOWN,
            tags=["analysis", "ai", "understanding"]
        ))

        self.register(ActionDefinition(
            id="extract_entities",
            title="Extract Entities",
            description="Extract named entities, people, organizations, and concepts",
            icon="tag",
            category=ActionCategory.ANALYSIS,
            supported_document_types=list(DocumentType),
            supported_languages=["en", "es", "fr", "de"],
            required_permissions=["read"],
            estimated_duration_seconds=20,
            output_type=OutputType.JSON,
            tags=["extraction", "entities", "nlp"]
        ))

        self.register(ActionDefinition(
            id="generate_insights",
            title="Generate Insights",
            description="Generate AI-powered insights and key findings",
            icon="lightbulb",
            category=ActionCategory.ANALYSIS,
            supported_document_types=list(DocumentType),
            supported_languages=["en", "es", "fr", "de"],
            required_permissions=["read"],
            estimated_duration_seconds=45,
            output_type=OutputType.MARKDOWN,
            tags=["insights", "ai", "findings"]
        ))

        # Invoice Actions
        self.register(ActionDefinition(
            id="extract_line_items",
            title="Extract Line Items",
            description="Extract all line items from an invoice",
            icon="list",
            category=ActionCategory.EXTRACTION,
            supported_document_types=[DocumentType.INVOICE],
            supported_languages=["en", "es", "fr", "de"],
            required_permissions=["read"],
            estimated_duration_seconds=15,
            output_type=OutputType.JSON,
            tags=["invoice", "extraction", "line_items"]
        ))

        self.register(ActionDefinition(
            id="generate_excel",
            title="Generate Excel",
            description="Create a structured Excel spreadsheet from invoice or data",
            icon="file-spreadsheet",
            category=ActionCategory.CREATION,
            supported_document_types=[DocumentType.INVOICE, DocumentType.SPREADSHEET],
            supported_languages=["en"],
            required_permissions=["read", "write"],
            estimated_duration_seconds=30,
            output_type=OutputType.XLSX,
            tags=["excel", "spreadsheet", "export"]
        ))

        self.register(ActionDefinition(
            id="generate_accounting_summary",
            title="Generate Accounting Summary",
            description="Create an accounting summary report",
            icon="calculator",
            category=ActionCategory.CREATION,
            supported_document_types=[DocumentType.INVOICE],
            supported_languages=["en"],
            required_permissions=["read"],
            estimated_duration_seconds=45,
            output_type=OutputType.PDF,
            tags=["accounting", "summary", "report"]
        ))

        # Email Actions
        self.register(ActionDefinition(
            id="draft_email",
            title="Draft Email",
            description="Draft a professional email based on document content",
            icon="mail",
            category=ActionCategory.COMMUNICATION,
            supported_document_types=[DocumentType.EMAIL, DocumentType.INVOICE, DocumentType.CONTRACT],
            supported_languages=["en", "es", "fr", "de"],
            required_permissions=["read"],
            estimated_duration_seconds=20,
            output_type=OutputType.EMAIL,
            tags=["email", "draft", "communication"]
        ))

        self.register(ActionDefinition(
            id="extract_tasks",
            title="Extract Action Items",
            description="Extract action items and tasks from meeting notes or emails",
            icon="check-square",
            category=ActionCategory.EXTRACTION,
            supported_document_types=[DocumentType.EMAIL, DocumentType.MEETING_NOTES],
            supported_languages=["en"],
            required_permissions=["read"],
            estimated_duration_seconds=15,
            output_type=OutputType.JSON,
            tags=["tasks", "action_items", "extraction"]
        ))

        # Translation Actions
        self.register(ActionDefinition(
            id="translate_document",
            title="Translate Document",
            description="Translate the document to another language",
            icon="globe",
            category=ActionCategory.TRANSLATION,
            supported_document_types=list(DocumentType),
            supported_languages=["en", "es", "fr", "de", "ar", "hi", "zh", "ja", "pt", "ru"],
            required_permissions=["read"],
            estimated_duration_seconds=60,
            output_type=OutputType.TEXT,
            tags=["translation", "language", "multilingual"]
        ))

        # Research Paper Actions
        self.register(ActionDefinition(
            id="create_presentation",
            title="Create Presentation",
            description="Generate a PowerPoint presentation from research paper",
            icon="presentation",
            category=ActionCategory.CREATION,
            supported_document_types=[DocumentType.RESEARCH_PAPER, DocumentType.BUSINESS_REPORT],
            supported_languages=["en"],
            required_permissions=["read"],
            estimated_duration_seconds=60,
            output_type=OutputType.PPTX,
            tags=["presentation", "slides", "pptx"]
        ))

        self.register(ActionDefinition(
            id="build_knowledge_graph",
            title="Build Knowledge Graph",
            description="Extract and visualize knowledge graph from document",
            icon="graph",
            category=ActionCategory.ANALYSIS,
            supported_document_types=[DocumentType.RESEARCH_PAPER, DocumentType.BOOK],
            supported_languages=["en"],
            required_permissions=["read"],
            estimated_duration_seconds=45,
            output_type=OutputType.JSON,
            tags=["knowledge", "graph", "entities"]
        ))

        # Resume Actions
        self.register(ActionDefinition(
            id="analyze_ats",
            title="ATS Analysis",
            description="Analyze resume for ATS compatibility",
            icon="clipboard",
            category=ActionCategory.ANALYSIS,
            supported_document_types=[DocumentType.RESUME],
            supported_languages=["en"],
            required_permissions=["read"],
            estimated_duration_seconds=20,
            output_type=OutputType.MARKDOWN,
            tags=["ats", "resume", "analysis"]
        ))

        self.register(ActionDefinition(
            id="match_jobs",
            title="Match Jobs",
            description="Match resume skills to job descriptions",
            icon="briefcase",
            category=ActionCategory.ANALYSIS,
            supported_document_types=[DocumentType.RESUME],
            supported_languages=["en"],
            required_permissions=["read"],
            estimated_duration_seconds=30,
            output_type=OutputType.MARKDOWN,
            tags=["jobs", "matching", "career"]
        ))

        self.register(ActionDefinition(
            id="generate_cover_letter",
            title="Generate Cover Letter",
            description="Generate a tailored cover letter",
            icon="file-text",
            category=ActionCategory.CREATION,
            supported_document_types=[DocumentType.RESUME],
            supported_languages=["en"],
            required_permissions=["read", "write"],
            estimated_duration_seconds=30,
            output_type=OutputType.DOCX,
            tags=["cover_letter", "job", "creation"]
        ))

        # Contract Actions
        self.register(ActionDefinition(
            id="summarize_clauses",
            title="Summarize Clauses",
            description="Summarize key clauses and obligations",
            icon="file",
            category=ActionCategory.ANALYSIS,
            supported_document_types=[DocumentType.CONTRACT, DocumentType.LEGAL_DOCUMENT],
            supported_languages=["en"],
            required_permissions=["read"],
            estimated_duration_seconds=30,
            output_type=OutputType.MARKDOWN,
            tags=["contract", "clauses", "summary"]
        ))

        self.register(ActionDefinition(
            id="extract_obligations",
            title="Extract Obligations",
            description="Extract and list all obligations from contract",
            icon="list",
            category=ActionCategory.EXTRACTION,
            supported_document_types=[DocumentType.CONTRACT, DocumentType.LEGAL_DOCUMENT],
            supported_languages=["en"],
            required_permissions=["read"],
            estimated_duration_seconds=25,
            output_type=OutputType.JSON,
            tags=["obligations", "contract", "extraction"]
        ))

        # Meeting Notes Actions
        self.register(ActionDefinition(
            id="generate_timeline",
            title="Generate Timeline",
            description="Create a timeline of events from meeting notes",
            icon="clock",
            category=ActionCategory.CREATION,
            supported_document_types=[DocumentType.MEETING_NOTES],
            supported_languages=["en"],
            required_permissions=["read"],
            estimated_duration_seconds=20,
            output_type=OutputType.MARKDOWN,
            tags=["timeline", "meeting", "creation"]
        ))

        self.register(ActionDefinition(
            id="send_follow_up_email",
            title="Send Follow-up Email",
            description="Generate and send follow-up email with action items",
            icon="send",
            category=ActionCategory.COMMUNICATION,
            supported_document_types=[DocumentType.MEETING_NOTES, DocumentType.EMAIL],
            supported_languages=["en"],
            required_permissions=["read", "write"],
            estimated_duration_seconds=15,
            output_type=OutputType.EMAIL,
            tags=["follow_up", "email", "action_items"]
        ))

        # Learning Actions
        self.register(ActionDefinition(
            id="create_flashcards",
            title="Create Flashcards",
            description="Generate flashcards for studying",
            icon="layers",
            category=ActionCategory.LEARNING,
            supported_document_types=[
                DocumentType.RESEARCH_PAPER, DocumentType.LECTURE_NOTES, DocumentType.BOOK
            ],
            supported_languages=["en"],
            required_permissions=["read", "write"],
            estimated_duration_seconds=30,
            output_type=OutputType.MARKDOWN,
            tags=["flashcards", "learning", "study"]
        ))

        self.register(ActionDefinition(
            id="create_quiz",
            title="Create Quiz",
            description="Generate a quiz from document content",
            icon="help-circle",
            category=ActionCategory.LEARNING,
            supported_document_types=[
                DocumentType.RESEARCH_PAPER, DocumentType.LECTURE_NOTES, DocumentType.BOOK
            ],
            supported_languages=["en"],
            required_permissions=["read", "write"],
            estimated_duration_seconds=30,
            output_type=OutputType.MARKDOWN,
            tags=["quiz", "learning", "test"]
        ))

        self.register(ActionDefinition(
            id="build_learning_path",
            title="Build Learning Path",
            description="Create a personalized learning path",
            icon="map",
            category=ActionCategory.LEARNING,
            supported_document_types=[DocumentType.RESEARCH_PAPER, DocumentType.LECTURE_NOTES],
            supported_languages=["en"],
            required_permissions=["read", "write"],
            estimated_duration_seconds=45,
            output_type=OutputType.MARKDOWN,
            tags=["learning_path", "education", "path"]
        ))

        # Export Actions
        self.register(ActionDefinition(
            id="export_pdf",
            title="Export as PDF",
            description="Export document or analysis as PDF",
            icon="file",
            category=ActionCategory.EXPORT,
            supported_document_types=list(DocumentType),
            supported_languages=["en"],
            required_permissions=["read"],
            estimated_duration_seconds=15,
            output_type=OutputType.PDF,
            tags=["pdf", "export"]
        ))

        self.register(ActionDefinition(
            id="export_csv",
            title="Export as CSV",
            description="Export data as CSV spreadsheet",
            icon="file",
            category=ActionCategory.EXPORT,
            supported_document_types=[DocumentType.SPREADSHEET, DocumentType.INVOICE],
            supported_languages=["en"],
            required_permissions=["read"],
            estimated_duration_seconds=10,
            output_type=OutputType.CSV,
            tags=["csv", "export", "data"]
        ))

    def register(self, definition: ActionDefinition) -> None:
        """
        Register an action.
        
        Args:
            definition: Action definition
        """
        handler = ActionHandler(
            definition=definition,
            handler_func=self._default_handler,
            requires_document=bool(definition.supported_document_types)
        )
        
        self._actions[definition.id] = handler
        
        # Add to categories
        if definition.category not in self._categories:
            self._categories[definition.category] = []
        self._categories[definition.category].append(definition.id)
        
        # Add to document type mapping
        for doc_type in definition.supported_document_types:
            if doc_type not in self._document_type_actions:
                self._document_type_actions[doc_type] = []
            self._document_type_actions[doc_type].append(definition.id)
        
        logger.info(f"Registered action: {definition.id}")

    def register_handler(
        self,
        action_id: str,
        handler_func: Callable,
        workflow_steps: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Register a custom handler for an action.
        
        Args:
            action_id: Action ID
            handler_func: Handler function
            workflow_steps: Optional workflow steps
        """
        if action_id in self._actions:
            self._actions[action_id].handler_func = handler_func
            self._actions[action_id].workflow_steps = workflow_steps
            logger.info(f"Registered custom handler for action: {action_id}")

    def get_action(self, action_id: str) -> Optional[ActionDefinition]:
        """Get action definition by ID."""
        handler = self._actions.get(action_id)
        return handler.definition if handler else None

    def get_all_actions(self) -> List[ActionDefinition]:
        """Get all registered actions."""
        return [h.definition for h in self._actions.values() if h.enabled]

    def get_actions_by_category(
        self,
        category: ActionCategory
    ) -> List[ActionDefinition]:
        """Get actions by category."""
        action_ids = self._categories.get(category, [])
        return [
            self._actions[aid].definition
            for aid in action_ids
            if aid in self._actions and self._actions[aid].enabled
        ]

    def get_actions_for_document_type(
        self,
        document_type: DocumentType
    ) -> List[ActionDefinition]:
        """Get actions available for a document type."""
        action_ids = self._document_type_actions.get(document_type, [])
        return [
            self._actions[aid].definition
            for aid in action_ids
            if aid in self._actions and self._actions[aid].enabled
        ]

    def get_actions_for_languages(
        self,
        languages: List[str]
    ) -> List[ActionDefinition]:
        """Get actions available for given languages."""
        return [
            action for action in self.get_all_actions()
            if any(lang in action.supported_languages for lang in languages)
        ]

    async def execute_action(
        self,
        request: ActionExecutionRequest,
        db: Session
    ) -> ActionExecutionResponse:
        """
        Execute an action.
        
        Args:
            request: Action execution request
            db: Database session
            
        Returns:
            Action execution response
        """
        start_time = datetime.utcnow()
        
        # Get action
        handler = self._actions.get(request.action_id)
        if not handler:
            return ActionExecutionResponse(
                action_id=request.action_id,
                success=False,
                error=f"Action not found: {request.action_id}",
                execution_time_ms=0
            )
        
        if not handler.enabled:
            return ActionExecutionResponse(
                action_id=request.action_id,
                success=False,
                error=f"Action is disabled: {request.action_id}",
                execution_time_ms=0
            )
        
        try:
            # Execute handler
            result = await handler.handler_func(
                db=db,
                action_id=request.action_id,
                document_id=request.document_id,
                parameters=request.parameters,
                output_type=request.output_type or handler.definition.output_type
            )
            
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return ActionExecutionResponse(
                action_id=request.action_id,
                success=True,
                output=result.get("output"),
                output_url=result.get("output_url"),
                download_filename=result.get("filename"),
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.exception(f"Action execution failed: {request.action_id}")
            
            return ActionExecutionResponse(
                action_id=request.action_id,
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )

    async def _default_handler(
        self,
        db: Session,
        action_id: str,
        document_id: Optional[int],
        parameters: Dict[str, Any],
        output_type: OutputType
    ) -> Dict[str, Any]:
        """Default handler for actions."""
        # This would integrate with LLM services in production
        return {
            "output": f"Action {action_id} executed successfully",
            "output_url": None,
            "filename": None
        }

    def get_actions_summary(self) -> Dict[str, Any]:
        """Get summary of all actions."""
        return {
            "total_actions": len([h for h in self._actions.values() if h.enabled]),
            "by_category": {
                cat.value: len(ids)
                for cat, ids in self._categories.items()
            },
            "by_document_type": {
                dt.value: len(ids)
                for dt, ids in self._document_type_actions.items()
            }
        }


# Global registry instance
_action_registry: Optional[ActionRegistry] = None


def get_action_registry() -> ActionRegistry:
    """Get the global action registry."""
    global _action_registry
    if _action_registry is None:
        _action_registry = ActionRegistry()
    return _action_registry
