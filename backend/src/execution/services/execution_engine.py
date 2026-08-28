"""
Execution Engine

Central orchestrator for the AI Execution Layer.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from sqlalchemy.orm import Session

from src.execution.schemas import (
    ExecutionRequest,
    ExecutionResponse,
    WorkflowExecutionRequest,
    ExecutionStatus,
    OutputFormat,
)
from src.execution.services.execution_registry import get_execution_registry
from src.execution.services.action_executor import get_action_executor
from src.execution.services.workflow_runner import get_workflow_runner
from src.execution.services.export_service import get_export_service
from src.execution.services.output_manager import get_output_manager
from src.execution.services.progress_tracker import get_progress_tracker
from src.core.logging import logger


class ExecutionEngine:
    """
    Central engine for AI execution.
    
    Coordinates:
    - Action execution
    - Workflow execution
    - Output management
    - Progress tracking
    """

    def __init__(self, db: Session, output_dir: str = "outputs"):
        """Initialize the execution engine."""
        self.db = db
        self.registry = get_execution_registry()
        self.output_dir = output_dir
        
        # Initialize services
        self.action_executor = get_action_executor(db, output_dir)
        self.workflow_runner = get_workflow_runner(db, output_dir)
        self.export_service = get_export_service()
        self.output_manager = get_output_manager()
        self.progress_tracker = get_progress_tracker()

    async def execute_action(
        self,
        request: ExecutionRequest
    ) -> ExecutionResponse:
        """
        Execute a single action.
        
        Args:
            request: Execution request
            
        Returns:
            Execution response
        """
        try:
            result = await self.action_executor.execute(
                action_id=request.action_id,
                document_id=request.document_id,
                parameters=request.parameters,
                output_format=request.output_format,
                language=request.language or "en",
                user_id=request.user_id
            )
            
            # Build response
            execution_id = result["execution_id"]
            record = self.progress_tracker.get_execution(execution_id)
            
            return ExecutionResponse(
                execution_id=execution_id,
                action_id=request.action_id,
                status=ExecutionStatus(result["status"]),
                progress=result["progress"],
                current_step=record.current_step if record else None,
                steps=record.steps if record else [],
                outputs=result.get("outputs", []),
                started_at=record.started_at if record else datetime.utcnow(),
                completed_at=record.completed_at if record else None,
                duration_ms=record.duration_ms if record else None
            )
            
        except Exception as e:
            logger.exception(f"Action execution failed: {request.action_id}")
            raise

    async def execute_workflow(
        self,
        request: WorkflowExecutionRequest
    ) -> ExecutionResponse:
        """
        Execute a workflow.
        
        Args:
            request: Workflow execution request
            
        Returns:
            Execution response
        """
        try:
            result = await self.workflow_runner.execute_workflow(
                workflow_id=request.workflow_id,
                document_id=request.document_id,
                workspace_id=request.workspace_id,
                parameters=request.parameters,
                output_format=request.output_format or OutputFormat.ZIP,
                language=request.language or "en",
                user_id=request.user_id
            )
            
            # Build response
            execution_id = result["execution_id"]
            record = self.progress_tracker.get_execution(execution_id)
            
            return ExecutionResponse(
                execution_id=execution_id,
                action_id=f"workflow:{request.workflow_id}",
                status=ExecutionStatus(result["status"]),
                progress=result["progress"],
                current_step=record.current_step if record else None,
                steps=record.steps if record else [],
                outputs=result.get("outputs", []),
                started_at=record.started_at if record else datetime.utcnow(),
                completed_at=record.completed_at if record else None,
                duration_ms=record.duration_ms if record else None
            )
            
        except Exception as e:
            logger.exception(f"Workflow execution failed: {request.workflow_id}")
            raise

    def get_execution(self, execution_id: str) -> Optional[ExecutionResponse]:
        """Get execution status."""
        record = self.progress_tracker.get_execution(execution_id)
        
        if not record:
            return None
        
        return ExecutionResponse(
            execution_id=execution_id,
            action_id=record.action_id,
            status=record.status,
            progress=record.progress,
            current_step=record.current_step,
            steps=record.steps,
            outputs=record.outputs,
            error=record.error,
            started_at=record.started_at,
            completed_at=record.completed_at,
            duration_ms=record.duration_ms
        )

    def get_execution_outputs(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get outputs for an execution."""
        return self.output_manager.get_download_urls(execution_id)

    def get_execution_history(
        self,
        user_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get execution history."""
        if user_id:
            records = self.progress_tracker.get_user_executions(user_id, limit)
            return [r.to_dict() for r in records]
        else:
            # Return recent executions (not user-specific)
            records = list(self.progress_tracker._executions.values())
            records.sort(key=lambda r: r.started_at, reverse=True)
            return [r.to_dict() for r in records[:limit]]

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an execution."""
        return self.progress_tracker.cancel_execution(execution_id)

    def retry_execution(
        self,
        execution_id: str
    ) -> Optional[ExecutionResponse]:
        """Retry a failed execution."""
        record = self.progress_tracker.get_execution(execution_id)
        
        if not record:
            return None
        
        if record.status != ExecutionStatus.FAILED:
            return None
        
        # Create new execution based on failed one
        if record.workflow_id:
            request = WorkflowExecutionRequest(
                workflow_id=record.workflow_id,
                document_id=record.document_id,
                workspace_id=record.workspace_id,
                parameters=record.parameters,
                user_id=record.user_id
            )
            return self.execute_workflow(request)
        else:
            request = ExecutionRequest(
                action_id=record.action_id,
                document_id=record.document_id,
                parameters=record.parameters,
                user_id=record.user_id
            )
            return self.execute_action(request)

    def get_templates(self) -> List[Dict[str, Any]]:
        """Get available execution templates."""
        workflows = self.workflow_runner.get_available_workflows()
        
        templates = []
        for workflow in workflows:
            templates.append({
                "template_id": workflow["workflow_id"],
                "name": workflow["name"],
                "description": workflow["description"],
                "workflow_id": workflow["workflow_id"],
                "recommended_for": self._get_recommended_for(workflow["workflow_id"]),
                "output_formats": workflow.get("produces_formats", [OutputFormat.ZIP.value])
            })
        
        return templates

    def _get_recommended_for(self, workflow_id: str) -> List[str]:
        """Get document types recommended for a workflow."""
        recommendations = {
            "invoice_complete": ["invoice"],
            "research_complete": ["research_paper", "book", "lecture_notes"],
            "resume_complete": ["resume"],
            "contract_complete": ["contract", "legal_document"],
            "meeting_complete": ["meeting_notes"],
            "email_complete": ["email"],
            "learning_complete": ["research_paper", "lecture_notes", "book"]
        }
        return recommendations.get(workflow_id, [])

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        stats = self.progress_tracker.get_statistics()
        registry_summary = self.registry.get_summary()
        output_stats = self.output_manager.get_statistics()
        
        return {
            "execution": {
                "total": stats["total_executions"],
                "active": stats["active_executions"],
                "completed_today": stats["completed_executions"],
                "failed_today": stats["failed_executions"],
                "average_duration_ms": stats["average_duration_ms"]
            },
            "registry": {
                "actions": registry_summary["total_actions"],
                "workflows": registry_summary["total_workflows"],
                "categories": len(registry_summary["by_category"]),
                "supported_formats": registry_summary["supported_formats"]
            },
            "output": {
                "total_files": output_stats["total_files"],
                "total_size_bytes": output_stats["total_size_bytes"],
                "output_directory": output_stats["output_directory"]
            }
        }

    def cleanup_old_outputs(self, max_age_hours: int = 24) -> int:
        """Clean up old output files."""
        count = self.progress_tracker.cleanup_old_executions(max_age_hours)
        return count


def get_execution_engine(db: Session) -> ExecutionEngine:
    """Get execution engine instance."""
    return ExecutionEngine(db)
