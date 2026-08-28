"""
Progress Tracker

Tracks execution progress and status.
"""

import uuid
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from src.execution.schemas import ExecutionStatus, ExecutionStepStatus
from src.core.logging import logger


class ExecutionEvent(str, Enum):
    """Execution lifecycle events."""
    STARTED = "started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    PROGRESS_UPDATED = "progress_updated"
    OUTPUT_GENERATED = "output_generated"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RESUMED = "resumed"


@dataclass
class ExecutionRecord:
    """Record of an execution."""
    execution_id: str
    action_id: str
    workflow_id: Optional[str] = None
    document_id: Optional[int] = None
    workspace_id: Optional[int] = None
    user_id: Optional[int] = None
    status: ExecutionStatus = ExecutionStatus.QUEUED
    progress: int = 0
    current_step: Optional[str] = None
    steps: List[ExecutionStepStatus] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "action_id": self.action_id,
            "workflow_id": self.workflow_id,
            "document_id": self.document_id,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "progress": self.progress,
            "current_step": self.current_step,
            "steps": [
                {
                    "step_name": s.step_name,
                    "status": s.status.value,
                    "progress": s.progress,
                    "message": s.message,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "output_file": s.output_file
                }
                for s in self.steps
            ],
            "outputs": self.outputs,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "parameters": self.parameters,
            "metadata": self.metadata,
            "logs": self.logs
        }


class ProgressTracker:
    """
    Tracks execution progress and manages execution records.
    
    Features:
    - Real-time progress tracking
    - Step-by-step status
    - Event logging
    - History management
    """

    def __init__(self, max_history: int = 1000):
        """Initialize the progress tracker."""
        self._executions: Dict[str, ExecutionRecord] = {}
        self._user_executions: Dict[int, List[str]] = {}  # user_id -> [execution_ids]
        self._max_history = max_history
        self._event_listeners: List[callable] = []

    def create_execution(
        self,
        action_id: str,
        workflow_id: Optional[str] = None,
        document_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
        user_id: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
        steps: Optional[List[str]] = None
    ) -> str:
        """
        Create a new execution record.
        
        Args:
            action_id: Action being executed
            workflow_id: Workflow ID if part of workflow
            document_id: Source document ID
            workspace_id: Target workspace ID
            user_id: User ID
            parameters: Execution parameters
            steps: List of step names
            
        Returns:
            Execution ID
        """
        execution_id = str(uuid.uuid4())
        
        record = ExecutionRecord(
            execution_id=execution_id,
            action_id=action_id,
            workflow_id=workflow_id,
            document_id=document_id,
            workspace_id=workspace_id,
            user_id=user_id,
            parameters=parameters or {},
            steps=[
                ExecutionStepStatus(
                    step_name=step,
                    status=ExecutionStatus.QUEUED,
                    progress=0
                )
                for step in (steps or ["main"])
            ]
        )
        
        self._executions[execution_id] = record
        
        # Track by user
        if user_id:
            if user_id not in self._user_executions:
                self._user_executions[user_id] = []
            self._user_executions[user_id].append(execution_id)
        
        # Emit event
        self._emit_event(ExecutionEvent.STARTED, execution_id, record.to_dict())
        
        logger.info(f"Created execution: {execution_id} for action: {action_id}")
        
        return execution_id

    def get_execution(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Get execution record by ID."""
        return self._executions.get(execution_id)

    def get_user_executions(
        self,
        user_id: int,
        limit: int = 20,
        status: Optional[ExecutionStatus] = None
    ) -> List[ExecutionRecord]:
        """Get executions for a user."""
        execution_ids = self._user_executions.get(user_id, [])
        
        records = []
        for exec_id in reversed(execution_ids[-limit:]):
            record = self._executions.get(exec_id)
            if record:
                if status is None or record.status == status:
                    records.append(record)
        
        return records

    def update_status(
        self,
        execution_id: str,
        status: ExecutionStatus,
        error: Optional[str] = None
    ) -> None:
        """Update execution status."""
        record = self._executions.get(execution_id)
        if not record:
            return
        
        record.status = status
        
        if error:
            record.error = error
        
        if status == ExecutionStatus.COMPLETED:
            record.completed_at = datetime.utcnow()
            record.duration_ms = int((record.completed_at - record.started_at).total_seconds() * 1000)
            record.progress = 100
            self._emit_event(ExecutionEvent.COMPLETED, execution_id, record.to_dict())
        
        elif status == ExecutionStatus.FAILED:
            record.completed_at = datetime.utcnow()
            record.duration_ms = int((datetime.utcnow() - record.started_at).total_seconds() * 1000)
            self._emit_event(ExecutionEvent.FAILED, execution_id, record.to_dict())
        
        elif status == ExecutionStatus.CANCELLED:
            record.completed_at = datetime.utcnow()
            record.duration_ms = int((datetime.utcnow() - record.started_at).total_seconds() * 1000)
            self._emit_event(ExecutionEvent.CANCELLED, execution_id, record.to_dict())
        
        logger.info(f"Execution {execution_id} status: {status.value}")

    def update_progress(
        self,
        execution_id: str,
        progress: int,
        message: Optional[str] = None
    ) -> None:
        """Update execution progress."""
        record = self._executions.get(execution_id)
        if not record:
            return
        
        record.progress = min(max(progress, 0), 100)
        
        if message:
            self.add_log(execution_id, "progress", message)
        
        self._emit_event(ExecutionEvent.PROGRESS_UPDATED, execution_id, {
            "execution_id": execution_id,
            "progress": progress,
            "message": message
        })

    def start_step(
        self,
        execution_id: str,
        step_name: str
    ) -> None:
        """Mark a step as started."""
        record = self._executions.get(execution_id)
        if not record:
            return
        
        record.current_step = step_name
        record.status = ExecutionStatus.RUNNING
        
        for step in record.steps:
            if step.step_name == step_name:
                step.status = ExecutionStatus.RUNNING
                step.started_at = datetime.utcnow()
                break
        
        self._emit_event(ExecutionEvent.STEP_STARTED, execution_id, {
            "execution_id": execution_id,
            "step_name": step_name
        })

    def complete_step(
        self,
        execution_id: str,
        step_name: str,
        output_file: Optional[str] = None,
        message: Optional[str] = None
    ) -> None:
        """Mark a step as completed."""
        record = self._executions.get(execution_id)
        if not record:
            return
        
        for step in record.steps:
            if step.step_name == step_name:
                step.status = ExecutionStatus.COMPLETED
                step.progress = 100
                step.completed_at = datetime.utcnow()
                if message:
                    step.message = message
                if output_file:
                    step.output_file = output_file
                break
        
        # Calculate overall progress
        completed = sum(1 for s in record.steps if s.status == ExecutionStatus.COMPLETED)
        record.progress = int((completed / len(record.steps)) * 100) if record.steps else 100
        
        self._emit_event(ExecutionEvent.STEP_COMPLETED, execution_id, {
            "execution_id": execution_id,
            "step_name": step_name,
            "output_file": output_file
        })

    def fail_step(
        self,
        execution_id: str,
        step_name: str,
        error: str
    ) -> None:
        """Mark a step as failed."""
        record = self._executions.get(execution_id)
        if not record:
            return
        
        for step in record.steps:
            if step.step_name == step_name:
                step.status = ExecutionStatus.FAILED
                step.message = error
                step.completed_at = datetime.utcnow()
                break
        
        record.status = ExecutionStatus.FAILED
        record.error = error
        record.completed_at = datetime.utcnow()
        
        self._emit_event(ExecutionEvent.STEP_FAILED, execution_id, {
            "execution_id": execution_id,
            "step_name": step_name,
            "error": error
        })

    def add_output(
        self,
        execution_id: str,
        output: Dict[str, Any]
    ) -> None:
        """Add an output artifact."""
        record = self._executions.get(execution_id)
        if not record:
            return
        
        record.outputs.append(output)
        
        self._emit_event(ExecutionEvent.OUTPUT_GENERATED, execution_id, {
            "execution_id": execution_id,
            "output": output
        })

    def add_log(
        self,
        execution_id: str,
        level: str,
        message: str
    ) -> None:
        """Add a log entry."""
        record = self._executions.get(execution_id)
        if not record:
            return
        
        record.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message
        })

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an execution."""
        record = self._executions.get(execution_id)
        if not record:
            return False
        
        if record.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            return False
        
        record.status = ExecutionStatus.CANCELLED
        record.completed_at = datetime.utcnow()
        
        # Cancel all pending steps
        for step in record.steps:
            if step.status == ExecutionStatus.QUEUED:
                step.status = ExecutionStatus.CANCELLED
        
        self._emit_event(ExecutionEvent.CANCELLED, execution_id, record.to_dict())
        
        logger.info(f"Execution cancelled: {execution_id}")
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = len(self._executions)
        active = sum(1 for r in self._executions.values() if r.status in [
            ExecutionStatus.QUEUED, ExecutionStatus.PREPARING, ExecutionStatus.RUNNING
        ])
        completed = sum(1 for r in self._executions.values() if r.status == ExecutionStatus.COMPLETED)
        failed = sum(1 for r in self._executions.values() if r.status == ExecutionStatus.FAILED)
        
        # Calculate average duration for completed executions
        durations = [
            r.duration_ms for r in self._executions.values()
            if r.duration_ms and r.status == ExecutionStatus.COMPLETED
        ]
        avg_duration = sum(durations) // len(durations) if durations else 0
        
        return {
            "total_executions": total,
            "active_executions": active,
            "completed_executions": completed,
            "failed_executions": failed,
            "average_duration_ms": avg_duration
        }

    def cleanup_old_executions(self, max_age_hours: int = 24) -> int:
        """Clean up old completed executions."""
        now = datetime.utcnow()
        to_remove = []
        
        for exec_id, record in self._executions.items():
            if record.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                if record.completed_at:
                    age = (now - record.completed_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(exec_id)
        
        for exec_id in to_remove:
            del self._executions[exec_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old executions")
        return len(to_remove)

    def add_event_listener(self, listener: callable) -> None:
        """Add an event listener."""
        self._event_listeners.append(listener)

    def _emit_event(self, event: ExecutionEvent, execution_id: str, data: Dict[str, Any]) -> None:
        """Emit an event to all listeners."""
        event_data = {
            "event": event.value,
            "execution_id": execution_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        for listener in self._event_listeners:
            try:
                listener(event_data)
            except Exception as e:
                logger.error(f"Event listener error: {e}")


# Global tracker instance
_progress_tracker: Optional[ProgressTracker] = None


def get_progress_tracker() -> ProgressTracker:
    """Get the global progress tracker."""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker
