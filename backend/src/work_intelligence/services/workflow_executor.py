"""
Workflow Executor

Executes dynamic workflows for AI-powered actions.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import uuid
import asyncio

from sqlalchemy.orm import Session

from src.work_intelligence.schemas import (
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowStepStatus,
    WorkflowStatus,
    OutputType,
    ActionDefinition,
)
from src.work_intelligence.services.action_registry import get_action_registry
from src.enterprise.workflows.engine import Workflow, WorkflowStep
from src.enterprise.orchestrator.base import AgentContext
from src.core.logging import logger


# Predefined workflow templates
WORKFLOW_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "invoice_processing": {
        "name": "Invoice Processing",
        "description": "Process an invoice end-to-end",
        "steps": [
            {"name": "classify", "action": "analyze_document", "next": "extract"},
            {"name": "extract", "action": "extract_line_items", "next": "generate"},
            {"name": "generate", "action": "generate_excel", "next": "summary"},
            {"name": "summary", "action": "generate_accounting_summary", "next": None},
        ]
    },
    "email_processing": {
        "name": "Email Processing",
        "description": "Process an email and extract actions",
        "steps": [
            {"name": "classify", "action": "analyze_document", "next": "extract"},
            {"name": "extract", "action": "extract_tasks", "next": "draft"},
            {"name": "draft", "action": "draft_email", "next": None},
        ]
    },
    "research_analysis": {
        "name": "Research Paper Analysis",
        "description": "Comprehensive analysis of research papers",
        "steps": [
            {"name": "analyze", "action": "analyze_document", "next": "graph"},
            {"name": "graph", "action": "build_knowledge_graph", "next": "presentation"},
            {"name": "presentation", "action": "create_presentation", "next": None},
        ]
    },
    "resume_analysis": {
        "name": "Resume Analysis",
        "description": "Analyze resume and suggest improvements",
        "steps": [
            {"name": "analyze", "action": "analyze_ats", "next": "match"},
            {"name": "match", "action": "match_jobs", "next": "cover"},
            {"name": "cover", "action": "generate_cover_letter", "next": None},
        ]
    },
    "meeting_processing": {
        "name": "Meeting Notes Processing",
        "description": "Process meeting notes and extract action items",
        "steps": [
            {"name": "extract", "action": "extract_action_items", "next": "timeline"},
            {"name": "timeline", "action": "generate_timeline", "next": "email"},
            {"name": "email", "action": "send_follow_up_email", "next": None},
        ]
    },
    "document_analysis": {
        "name": "Document Analysis",
        "description": "Comprehensive document analysis",
        "steps": [
            {"name": "analyze", "action": "analyze_document", "next": "insights"},
            {"name": "insights", "action": "generate_insights", "next": "summary"},
            {"name": "summary", "action": "generate_summary", "next": None},
        ]
    },
    "study_pack": {
        "name": "Study Pack Generation",
        "description": "Generate comprehensive study materials",
        "steps": [
            {"name": "flashcards", "action": "create_flashcards", "next": "quiz"},
            {"name": "quiz", "action": "create_quiz", "next": "path"},
            {"name": "path", "action": "build_learning_path", "next": None},
        ]
    },
    "financial_report": {
        "name": "Financial Report",
        "description": "Generate financial analysis report",
        "steps": [
            {"name": "extract", "action": "extract_line_items", "next": "excel"},
            {"name": "excel", "action": "generate_excel", "next": "summary"},
            {"name": "summary", "action": "generate_accounting_summary", "next": None},
        ]
    },
    "contract_review": {
        "name": "Contract Review",
        "description": "Review and analyze contract",
        "steps": [
            {"name": "summarize", "action": "summarize_clauses", "next": "extract"},
            {"name": "extract", "action": "extract_obligations", "next": None},
        ]
    },
}


@dataclass
class ExecutionState:
    """State of a workflow execution."""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    steps: List[WorkflowStepStatus]
    current_step: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    output: Optional[Any] = None
    error: Optional[str] = None


class WorkflowExecutor:
    """
    Executor for dynamic workflows.
    
    Features:
    - Predefined workflow templates
    - Progress tracking
    - Step-by-step execution
    - Error handling
    """

    def __init__(self, db: Session):
        """Initialize the workflow executor."""
        self.db = db
        self.action_registry = get_action_registry()
        self._executions: Dict[str, ExecutionState] = {}

    async def execute(
        self,
        request: WorkflowExecutionRequest
    ) -> WorkflowExecutionResponse:
        """
        Execute a workflow.
        
        Args:
            request: Workflow execution request
            
        Returns:
            Workflow execution response
        """
        # Get workflow template
        template = WORKFLOW_TEMPLATES.get(request.workflow_id)
        if not template:
            return WorkflowExecutionResponse(
                execution_id=str(uuid.uuid4()),
                workflow_id=request.workflow_id,
                status=WorkflowStatus.FAILED,
                error=f"Workflow not found: {request.workflow_id}",
                started_at=datetime.utcnow()
            )
        
        # Create execution state
        execution_id = str(uuid.uuid4())
        state = ExecutionState(
            execution_id=execution_id,
            workflow_id=request.workflow_id,
            status=WorkflowStatus.QUEUED,
            steps=[
                WorkflowStepStatus(
                    step_name=step["name"],
                    status=WorkflowStatus.QUEUED,
                    progress_percent=0
                )
                for step in template["steps"]
            ],
            current_step=0,
            started_at=datetime.utcnow()
        )
        
        self._executions[execution_id] = state
        
        # Execute workflow
        try:
            await self._execute_workflow(state, template, request, execution_id)
        except Exception as e:
            logger.exception(f"Workflow execution failed: {execution_id}")
            state.status = WorkflowStatus.FAILED
            state.error = str(e)
        
        # Build response
        return self._build_response(state)

    async def _execute_workflow(
        self,
        state: ExecutionState,
        template: Dict[str, Any],
        request: WorkflowExecutionRequest,
        execution_id: str
    ) -> None:
        """Execute workflow steps."""
        state.status = WorkflowStatus.PREPARING
        steps = template["steps"]
        
        for i, step in enumerate(steps):
            state.current_step = i
            step_status = state.steps[i]
            
            # Update step status
            step_status.status = WorkflowStatus.UNDERSTANDING
            step_status.started_at = datetime.utcnow()
            state.status = WorkflowStatus.UNDERSTANDING
            
            # Execute step
            try:
                action_id = step["action"]
                
                # Update status
                step_status.status = WorkflowStatus.REASONING
                state.status = WorkflowStatus.REASONING
                step_status.progress_percent = 25
                
                # Execute action
                step_status.status = WorkflowStatus.PROCESSING
                state.status = WorkflowStatus.PROCESSING
                step_status.progress_percent = 50
                
                result = await self._execute_action(
                    action_id=action_id,
                    document_id=request.document_id,
                    parameters=request.parameters,
                    output_type=request.output_type
                )
                
                # Update progress
                step_status.status = WorkflowStatus.GENERATING
                state.status = WorkflowStatus.GENERATING
                step_status.progress_percent = 75
                
                # Validate result
                step_status.status = WorkflowStatus.VALIDATING
                state.status = WorkflowStatus.VALIDATING
                step_status.progress_percent = 90
                
                # Complete step
                step_status.status = WorkflowStatus.COMPLETED
                step_status.progress_percent = 100
                step_status.completed_at = datetime.utcnow()
                step_status.message = f"Completed: {action_id}"
                
                # Store output from last step
                if result.get("output"):
                    state.output = result["output"]
                
            except Exception as e:
                step_status.status = WorkflowStatus.FAILED
                step_status.message = f"Failed: {str(e)}"
                state.error = str(e)
                state.status = WorkflowStatus.FAILED
                raise
        
        # Complete workflow
        state.status = WorkflowStatus.COMPLETED
        state.completed_at = datetime.utcnow()

    async def _execute_action(
        self,
        action_id: str,
        document_id: Optional[int],
        parameters: Dict[str, Any],
        output_type: Optional[OutputType]
    ) -> Dict[str, Any]:
        """Execute a single action."""
        from src.work_intelligence.schemas import ActionExecutionRequest as AER
        
        action_request = AER(
            action_id=action_id,
            document_id=document_id,
            parameters=parameters,
            output_type=output_type
        )
        
        result = await self.action_registry.execute_action(action_request, self.db)
        
        if not result.success:
            raise Exception(result.error or f"Action {action_id} failed")
        
        return {
            "output": result.output,
            "output_url": result.output_url,
            "filename": result.download_filename
        }

    def _build_response(self, state: ExecutionState) -> WorkflowExecutionResponse:
        """Build response from execution state."""
        # Calculate overall progress
        total_progress = sum(s.progress_percent for s in state.steps) / len(state.steps) if state.steps else 0
        
        # Get output from completed workflow
        output_url = None
        download_filename = None
        if state.status == WorkflowStatus.COMPLETED and state.output:
            # Would extract from last action result
            pass
        
        return WorkflowExecutionResponse(
            execution_id=state.execution_id,
            workflow_id=state.workflow_id,
            status=state.status,
            steps=state.steps,
            progress_percent=int(total_progress),
            output=state.output,
            output_url=output_url,
            download_filename=download_filename,
            error=state.error,
            started_at=state.started_at,
            completed_at=state.completed_at
        )

    def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecutionResponse]:
        """Get status of a workflow execution."""
        state = self._executions.get(execution_id)
        if not state:
            return None
        
        return self._build_response(state)

    def get_available_workflows(self) -> List[Dict[str, Any]]:
        """Get list of available workflows."""
        return [
            {
                "workflow_id": wf_id,
                "name": template["name"],
                "description": template["description"],
                "step_count": len(template["steps"]),
                "steps": [
                    {"name": s["name"], "action": s["action"]}
                    for s in template["steps"]
                ]
            }
            for wf_id, template in WORKFLOW_TEMPLATES.items()
        ]

    def get_workflow_for_action(
        self,
        action_id: str
    ) -> Optional[str]:
        """Get the workflow that contains a specific action."""
        for wf_id, template in WORKFLOW_TEMPLATES.items():
            for step in template["steps"]:
                if step["action"] == action_id:
                    return wf_id
        return None


def get_workflow_executor(db: Session) -> WorkflowExecutor:
    """Get workflow executor instance."""
    return WorkflowExecutor(db)
