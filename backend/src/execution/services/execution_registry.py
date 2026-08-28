"""
Execution Registry

Plugin architecture for executable actions.
Each action registers itself with the registry and can be executed.
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

from src.execution.schemas import (
    ActionDefinition,
    WorkflowDefinition,
    ActionType,
    OutputFormat,
)
from src.core.logging import logger


@dataclass
class ActionHandler:
    """Handler for an action."""
    definition: ActionDefinition
    handler_func: Callable
    validator_func: Optional[Callable] = None
    enabled: bool = True


class ExecutionRegistry:
    """
    Registry for all executable actions.
    
    Features:
    - Plugin architecture
    - Dynamic registration
    - Action execution
    - Workflow generation
    """

    def __init__(self):
        """Initialize the execution registry."""
        self._actions: Dict[str, ActionHandler] = {}
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._action_categories: Dict[str, List[str]] = {}
        self._initialize_default_actions()
        self._initialize_default_workflows()

    def _initialize_default_actions(self) -> None:
        """Initialize default executable actions."""
        
        # Excel Generation Actions
        self.register(ActionDefinition(
            action_id="generate_excel_invoice",
            name="Generate Invoice Excel",
            description="Generate structured Excel spreadsheet from invoice",
            action_type=ActionType.GENERATE,
            category="invoice",
            supported_formats=[OutputFormat.XLSX],
            supported_document_types=["invoice"],
            required_parameters={"include_formulas": True},
            estimated_duration_seconds=30,
            tags=["excel", "invoice", "spreadsheet"]
        ))

        self.register(ActionDefinition(
            action_id="generate_excel_data",
            name="Generate Data Excel",
            description="Generate Excel from structured data",
            action_type=ActionType.GENERATE,
            category="data",
            supported_formats=[OutputFormat.XLSX],
            supported_document_types=["spreadsheet", "invoice"],
            estimated_duration_seconds=25,
            tags=["excel", "data"]
        ))

        # PDF Generation Actions
        self.register(ActionDefinition(
            action_id="generate_pdf_report",
            name="Generate PDF Report",
            description="Generate professional PDF report",
            action_type=ActionType.GENERATE,
            category="report",
            supported_formats=[OutputFormat.PDF],
            supported_document_types=["invoice", "contract", "business_report", "research_paper"],
            estimated_duration_seconds=45,
            tags=["pdf", "report"]
        ))

        self.register(ActionDefinition(
            action_id="generate_pdf_summary",
            name="Generate PDF Summary",
            description="Generate concise PDF summary",
            action_type=ActionType.GENERATE,
            category="summary",
            supported_formats=[OutputFormat.PDF],
            supported_document_types=["research_paper", "book", "lecture_notes"],
            estimated_duration_seconds=30,
            tags=["pdf", "summary"]
        ))

        # Presentation Generation
        self.register(ActionDefinition(
            action_id="generate_pptx_presentation",
            name="Generate Presentation",
            description="Generate PowerPoint presentation",
            action_type=ActionType.GENERATE,
            category="presentation",
            supported_formats=[OutputFormat.PPTX],
            supported_document_types=["research_paper", "business_report", "meeting_notes"],
            estimated_duration_seconds=60,
            tags=["powerpoint", "slides", "presentation"]
        ))

        # Document Generation
        self.register(ActionDefinition(
            action_id="generate_docx_cover_letter",
            name="Generate Cover Letter",
            description="Generate professional cover letter",
            action_type=ActionType.GENERATE,
            category="job",
            supported_formats=[OutputFormat.DOCX],
            supported_document_types=["resume"],
            estimated_duration_seconds=30,
            tags=["docx", "cover_letter", "job"]
        ))

        self.register(ActionDefinition(
            action_id="generate_docx_notes",
            name="Generate Document Notes",
            description="Generate formatted document notes",
            action_type=ActionType.GENERATE,
            category="notes",
            supported_formats=[OutputFormat.DOCX],
            supported_document_types=["research_paper", "lecture_notes", "book"],
            estimated_duration_seconds=30,
            tags=["docx", "notes"]
        ))

        self.register(ActionDefinition(
            action_id="generate_docx_contract_summary",
            name="Generate Contract Summary",
            description="Generate contract summary document",
            action_type=ActionType.GENERATE,
            category="contract",
            supported_formats=[OutputFormat.DOCX],
            supported_document_types=["contract", "legal_document"],
            estimated_duration_seconds=45,
            tags=["docx", "contract", "summary"]
        ))

        # Flashcard Generation
        self.register(ActionDefinition(
            action_id="generate_flashcards",
            name="Generate Flashcards",
            description="Generate flashcards for studying",
            action_type=ActionType.GENERATE,
            category="learning",
            supported_formats=[OutputFormat.CSV, OutputFormat.JSON],
            supported_document_types=["research_paper", "book", "lecture_notes"],
            estimated_duration_seconds=30,
            tags=["flashcards", "learning", "study"]
        ))

        # Quiz Generation
        self.register(ActionDefinition(
            action_id="generate_quiz",
            name="Generate Quiz",
            description="Generate quiz with questions",
            action_type=ActionType.GENERATE,
            category="learning",
            supported_formats=[OutputFormat.JSON, OutputFormat.PDF],
            supported_document_types=["research_paper", "book", "lecture_notes"],
            estimated_duration_seconds=40,
            tags=["quiz", "test", "learning"]
        ))

        # Email Generation
        self.register(ActionDefinition(
            action_id="generate_email_reply",
            name="Generate Email Reply",
            description="Generate professional email reply",
            action_type=ActionType.GENERATE,
            category="communication",
            supported_formats=[OutputFormat.TEXT],
            supported_document_types=["email"],
            estimated_duration_seconds=20,
            tags=["email", "reply", "communication"]
        ))

        self.register(ActionDefinition(
            action_id="generate_email_reminder",
            name="Generate Payment Reminder",
            description="Generate payment reminder email",
            action_type=ActionType.GENERATE,
            category="communication",
            supported_formats=[OutputFormat.TEXT],
            supported_document_types=["invoice"],
            estimated_duration_seconds=15,
            tags=["email", "reminder", "invoice"]
        ))

        self.register(ActionDefinition(
            action_id="generate_email_followup",
            name="Generate Follow-up Email",
            description="Generate meeting follow-up email",
            action_type=ActionType.GENERATE,
            category="communication",
            supported_formats=[OutputFormat.TEXT],
            supported_document_types=["meeting_notes"],
            estimated_duration_seconds=20,
            tags=["email", "follow_up", "meeting"]
        ))

        # Analysis Actions
        self.register(ActionDefinition(
            action_id="analyze_ats",
            name="ATS Analysis",
            description="Analyze resume for ATS compatibility",
            action_type=ActionType.ANALYZE,
            category="resume",
            supported_formats=[OutputFormat.JSON, OutputFormat.MARKDOWN],
            supported_document_types=["resume"],
            estimated_duration_seconds=25,
            tags=["ats", "resume", "analysis"]
        ))

        self.register(ActionDefinition(
            action_id="analyze_contract_risks",
            name="Contract Risk Analysis",
            description="Analyze contract for risks",
            action_type=ActionType.ANALYZE,
            category="contract",
            supported_formats=[OutputFormat.JSON, OutputFormat.MARKDOWN],
            supported_document_types=["contract", "legal_document"],
            estimated_duration_seconds=45,
            tags=["risk", "contract", "analysis"]
        ))

        self.register(ActionDefinition(
            action_id="analyze_invoice_discrepancies",
            name="Invoice Discrepancy Analysis",
            description="Check invoice for discrepancies",
            action_type=ActionType.ANALYZE,
            category="invoice",
            supported_formats=[OutputFormat.JSON],
            supported_document_types=["invoice"],
            estimated_duration_seconds=20,
            tags=["discrepancy", "invoice", "analysis"]
        ))

        # Extraction Actions
        self.register(ActionDefinition(
            action_id="extract_line_items",
            name="Extract Line Items",
            description="Extract line items from invoice",
            action_type=ActionType.EXTRACT,
            category="invoice",
            supported_formats=[OutputFormat.JSON, OutputFormat.CSV],
            supported_document_types=["invoice"],
            estimated_duration_seconds=15,
            tags=["line_items", "extraction", "invoice"]
        ))

        self.register(ActionDefinition(
            action_id="extract_action_items",
            name="Extract Action Items",
            description="Extract action items from meeting notes",
            action_type=ActionType.EXTRACT,
            category="meeting",
            supported_formats=[OutputFormat.JSON, OutputFormat.MARKDOWN],
            supported_document_types=["meeting_notes", "email"],
            estimated_duration_seconds=15,
            tags=["action_items", "extraction", "meeting"]
        ))

        self.register(ActionDefinition(
            action_id="extract_obligations",
            name="Extract Contract Obligations",
            description="Extract obligations from contract",
            action_type=ActionType.EXTRACT,
            category="contract",
            supported_formats=[OutputFormat.JSON, OutputFormat.MARKDOWN],
            supported_document_types=["contract", "legal_document"],
            estimated_duration_seconds=25,
            tags=["obligations", "extraction", "contract"]
        ))

        # Summary Actions
        self.register(ActionDefinition(
            action_id="generate_summary",
            name="Generate Summary",
            description="Generate document summary",
            action_type=ActionType.GENERATE,
            category="summary",
            supported_formats=[OutputFormat.MARKDOWN, OutputFormat.PDF],
            supported_document_types=["*"],
            estimated_duration_seconds=30,
            tags=["summary", "generate"]
        ))

        self.register(ActionDefinition(
            action_id="generate_contract_summary",
            name="Generate Contract Summary",
            description="Generate contract clause summary",
            action_type=ActionType.GENERATE,
            category="contract",
            supported_formats=[OutputFormat.MARKDOWN, OutputFormat.DOCX],
            supported_document_types=["contract", "legal_document"],
            estimated_duration_seconds=30,
            tags=["summary", "contract"]
        ))

        self.register(ActionDefinition(
            action_id="generate_meeting_minutes",
            name="Generate Meeting Minutes",
            description="Generate formatted meeting minutes",
            action_type=ActionType.GENERATE,
            category="meeting",
            supported_formats=[OutputFormat.MARKDOWN, OutputFormat.DOCX],
            supported_document_types=["meeting_notes"],
            estimated_duration_seconds=25,
            tags=["minutes", "meeting", "generate"]
        ))

        # Calendar/Event Actions
        self.register(ActionDefinition(
            action_id="generate_calendar_event",
            name="Generate Calendar Event",
            description="Generate calendar event from content",
            action_type=ActionType.GENERATE,
            category="calendar",
            supported_formats=[OutputFormat.JSON],
            supported_document_types=["email", "meeting_notes"],
            estimated_duration_seconds=10,
            tags=["calendar", "event", "generate"]
        ))

        # Learning Path Actions
        self.register(ActionDefinition(
            action_id="generate_learning_path",
            name="Generate Learning Path",
            description="Generate personalized learning path",
            action_type=ActionType.GENERATE,
            category="learning",
            supported_formats=[OutputFormat.MARKDOWN, OutputFormat.JSON],
            supported_document_types=["research_paper", "lecture_notes", "book"],
            estimated_duration_seconds=45,
            tags=["learning_path", "education", "generate"]
        ))

        # Mind Map Actions
        self.register(ActionDefinition(
            action_id="generate_mindmap",
            name="Generate Mind Map",
            description="Generate concept mind map",
            action_type=ActionType.GENERATE,
            category="learning",
            supported_formats=[OutputFormat.JSON, OutputFormat.MARKDOWN],
            supported_document_types=["research_paper", "book", "lecture_notes"],
            estimated_duration_seconds=40,
            tags=["mindmap", "concept", "generate"]
        ))

        # Export Actions
        self.register(ActionDefinition(
            action_id="export_all_formats",
            name="Export in All Formats",
            description="Export document in all available formats",
            action_type=ActionType.EXPORT,
            category="export",
            supported_formats=[OutputFormat.PDF, OutputFormat.DOCX, OutputFormat.MARKDOWN, OutputFormat.HTML],
            supported_document_types=["*"],
            estimated_duration_seconds=120,
            tags=["export", "all_formats"]
        ))

        self.register(ActionDefinition(
            action_id="export_bundle",
            name="Export Complete Bundle",
            description="Export complete output bundle with all artifacts",
            action_type=ActionType.EXPORT,
            category="export",
            supported_formats=[OutputFormat.ZIP],
            supported_document_types=["*"],
            estimated_duration_seconds=180,
            tags=["export", "bundle", "zip"]
        ))

        logger.info(f"Registered {len(self._actions)} default actions")

    def _initialize_default_workflows(self) -> None:
        """Initialize default workflows."""
        
        # Invoice Processing Workflow
        self.register_workflow(WorkflowDefinition(
            workflow_id="invoice_complete",
            name="Complete Invoice Processing",
            description="Process invoice end-to-end with Excel, summary, and email",
            steps=[
                {"action_id": "extract_line_items", "name": "Extract Line Items"},
                {"action_id": "generate_excel_invoice", "name": "Generate Excel"},
                {"action_id": "analyze_invoice_discrepancies", "name": "Check Discrepancies"},
                {"action_id": "generate_email_reminder", "name": "Generate Reminder Email"},
            ],
            estimated_duration_seconds=120,
            produces_formats=[OutputFormat.XLSX, OutputFormat.JSON, OutputFormat.TEXT]
        ))

        # Research Paper Workflow
        self.register_workflow(WorkflowDefinition(
            workflow_id="research_complete",
            name="Complete Research Package",
            description="Generate comprehensive study materials from research paper",
            steps=[
                {"action_id": "generate_summary", "name": "Generate Summary"},
                {"action_id": "generate_pptx_presentation", "name": "Generate Slides"},
                {"action_id": "generate_flashcards", "name": "Generate Flashcards"},
                {"action_id": "generate_quiz", "name": "Generate Quiz"},
                {"action_id": "generate_learning_path", "name": "Generate Learning Path"},
                {"action_id": "generate_mindmap", "name": "Generate Mind Map"},
            ],
            estimated_duration_seconds=300,
            produces_formats=[OutputFormat.PDF, OutputFormat.PPTX, OutputFormat.CSV, OutputFormat.JSON]
        ))

        # Resume Workflow
        self.register_workflow(WorkflowDefinition(
            workflow_id="resume_complete",
            name="Complete Resume Package",
            description="Complete resume analysis and improvement package",
            steps=[
                {"action_id": "analyze_ats", "name": "ATS Analysis"},
                {"action_id": "generate_docx_cover_letter", "name": "Generate Cover Letter"},
                {"action_id": "generate_learning_path", "name": "Suggest Interview Prep"},
            ],
            estimated_duration_seconds=120,
            produces_formats=[OutputFormat.DOCX, OutputFormat.JSON, OutputFormat.MARKDOWN]
        ))

        # Contract Workflow
        self.register_workflow(WorkflowDefinition(
            workflow_id="contract_complete",
            name="Complete Contract Review",
            description="Comprehensive contract analysis and summary",
            steps=[
                {"action_id": "generate_contract_summary", "name": "Generate Summary"},
                {"action_id": "extract_obligations", "name": "Extract Obligations"},
                {"action_id": "analyze_contract_risks", "name": "Risk Analysis"},
            ],
            estimated_duration_seconds=180,
            produces_formats=[OutputFormat.DOCX, OutputFormat.JSON, OutputFormat.MARKDOWN]
        ))

        # Meeting Notes Workflow
        self.register_workflow(WorkflowDefinition(
            workflow_id="meeting_complete",
            name="Complete Meeting Package",
            description="Process meeting notes with minutes, actions, and follow-up",
            steps=[
                {"action_id": "generate_meeting_minutes", "name": "Generate Minutes"},
                {"action_id": "extract_action_items", "name": "Extract Actions"},
                {"action_id": "generate_calendar_event", "name": "Generate Calendar Events"},
                {"action_id": "generate_email_followup", "name": "Generate Follow-up"},
            ],
            estimated_duration_seconds=120,
            produces_formats=[OutputFormat.DOCX, OutputFormat.JSON, OutputFormat.TEXT]
        ))

        # Email Workflow
        self.register_workflow(WorkflowDefinition(
            workflow_id="email_complete",
            name="Complete Email Processing",
            description="Process email with summary, tasks, and reply",
            steps=[
                {"action_id": "generate_summary", "name": "Summarize Email"},
                {"action_id": "extract_action_items", "name": "Extract Tasks"},
                {"action_id": "generate_email_reply", "name": "Generate Reply"},
            ],
            estimated_duration_seconds=90,
            produces_formats=[OutputFormat.TEXT, OutputFormat.JSON, OutputFormat.MARKDOWN]
        ))

        # Learning Package Workflow
        self.register_workflow(WorkflowDefinition(
            workflow_id="learning_complete",
            name="Complete Learning Package",
            description="Generate all learning materials",
            steps=[
                {"action_id": "generate_summary", "name": "Generate Summary"},
                {"action_id": "generate_flashcards", "name": "Generate Flashcards"},
                {"action_id": "generate_quiz", "name": "Generate Quiz"},
                {"action_id": "generate_learning_path", "name": "Generate Learning Path"},
            ],
            estimated_duration_seconds=180,
            produces_formats=[OutputFormat.PDF, OutputFormat.CSV, OutputFormat.JSON]
        ))

        logger.info(f"Registered {len(self._workflows)} default workflows")

    def register(self, definition: ActionDefinition) -> None:
        """
        Register an action.
        
        Args:
            definition: Action definition
        """
        handler = ActionHandler(
            definition=definition,
            handler_func=self._default_handler
        )
        
        self._actions[definition.action_id] = handler
        
        # Add to categories
        if definition.category not in self._action_categories:
            self._action_categories[definition.category] = []
        self._action_categories[definition.category].append(definition.action_id)
        
        logger.info(f"Registered action: {definition.action_id}")

    def register_handler(
        self,
        action_id: str,
        handler_func: Callable,
        validator_func: Optional[Callable] = None
    ) -> None:
        """
        Register a custom handler for an action.
        
        Args:
            action_id: Action ID
            handler_func: Handler function
            validator_func: Optional validator function
        """
        if action_id in self._actions:
            self._actions[action_id].handler_func = handler_func
            self._actions[action_id].validator_func = validator_func
            logger.info(f"Registered custom handler for action: {action_id}")

    def register_workflow(self, definition: WorkflowDefinition) -> None:
        """Register a workflow."""
        self._workflows[definition.workflow_id] = definition
        logger.info(f"Registered workflow: {definition.workflow_id}")

    def get_action(self, action_id: str) -> Optional[ActionDefinition]:
        """Get action definition by ID."""
        handler = self._actions.get(action_id)
        return handler.definition if handler else None

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition by ID."""
        return self._workflows.get(workflow_id)

    def get_all_actions(self) -> List[ActionDefinition]:
        """Get all registered actions."""
        return [h.definition for h in self._actions.values() if h.enabled]

    def get_all_workflows(self) -> List[WorkflowDefinition]:
        """Get all registered workflows."""
        return list(self._workflows.values())

    def get_actions_by_category(self, category: str) -> List[ActionDefinition]:
        """Get actions by category."""
        action_ids = self._action_categories.get(category, [])
        return [
            self._actions[aid].definition
            for aid in action_ids
            if aid in self._actions and self._actions[aid].enabled
        ]

    def get_actions_for_document_type(
        self,
        document_type: str
    ) -> List[ActionDefinition]:
        """Get actions available for a document type."""
        return [
            action for action in self.get_all_actions()
            if document_type in action.supported_document_types or "*" in action.supported_document_types
        ]

    def get_actions_by_format(
        self,
        output_format: OutputFormat
    ) -> List[ActionDefinition]:
        """Get actions that produce a specific format."""
        return [
            action for action in self.get_all_actions()
            if output_format in action.supported_formats
        ]

    async def execute_action(
        self,
        action_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an action.
        
        Args:
            action_id: Action to execute
            context: Execution context
            
        Returns:
            Execution result
        """
        handler = self._actions.get(action_id)
        if not handler:
            raise ValueError(f"Action not found: {action_id}")
        
        if not handler.enabled:
            raise ValueError(f"Action is disabled: {action_id}")
        
        # Validate if validator exists
        if handler.validator_func:
            handler.validator_func(context)
        
        # Execute handler
        result = await handler.handler_func(context)
        
        return result

    async def _default_handler(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Default handler - to be replaced by actual implementations."""
        return {
            "output": f"Action executed: {context.get('action_id')}",
            "success": True
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get registry summary."""
        return {
            "total_actions": len([h for h in self._actions.values() if h.enabled]),
            "total_workflows": len(self._workflows),
            "by_category": {
                cat: len(ids)
                for cat, ids in self._action_categories.items()
            },
            "supported_formats": list(set(
                fmt for action in self.get_all_actions()
                for fmt in action.supported_formats
            ))
        }


# Global registry instance
_execution_registry: Optional[ExecutionRegistry] = None


def get_execution_registry() -> ExecutionRegistry:
    """Get the global execution registry."""
    global _execution_registry
    if _execution_registry is None:
        _execution_registry = ExecutionRegistry()
    return _execution_registry
