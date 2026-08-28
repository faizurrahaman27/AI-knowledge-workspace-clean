"""
AI Execution Layer

Transforms AI Knowledge Workspace from "AI that understands work"
into "AI that finishes work."

Modules:
- Execution Registry: Plugin architecture for actions
- Action Executor: Executes individual actions
- Workflow Runner: Executes multi-step workflows
- File Generator: Generates output files
- Export Service: Manages export operations
- Progress Tracker: Tracks execution progress
- Output Manager: Manages output artifacts
- Execution Engine: Central orchestrator
"""

from src.execution.schemas import (
    # Enums
    ExecutionStatus,
    OutputFormat,
    ActionType,
    # Requests/Responses
    ExecutionRequest,
    ExecutionResponse,
    WorkflowExecutionRequest,
    ExecutionHistory,
    ExecutionHistoryResponse,
    TemplatesResponse,
    ExecutionTemplate,
    SystemStatus,
    ExecutionStatusResponse,
    # Internal
    ExecutionStepStatus,
    OutputArtifact,
    OutputBundle,
    ActionDefinition,
    WorkflowDefinition,
)

from src.execution.services.execution_engine import (
    ExecutionEngine,
    get_execution_engine,
)

from src.execution.services.execution_registry import (
    ExecutionRegistry,
    get_execution_registry,
)

from src.execution.services.progress_tracker import (
    ProgressTracker,
    get_progress_tracker,
)

from src.execution.services.action_executor import (
    ActionExecutor,
    get_action_executor,
)

from src.execution.services.workflow_runner import (
    WorkflowRunner,
    get_workflow_runner,
)

from src.execution.services.file_generator import (
    FileGenerator,
)

from src.execution.services.export_service import (
    ExportService,
    get_export_service,
)

from src.execution.services.output_manager import (
    OutputManager,
    get_output_manager,
)

__all__ = [
    # Enums
    "ExecutionStatus",
    "OutputFormat",
    "ActionType",
    # Requests/Responses
    "ExecutionRequest",
    "ExecutionResponse",
    "WorkflowExecutionRequest",
    "ExecutionHistory",
    "ExecutionHistoryResponse",
    "TemplatesResponse",
    "ExecutionTemplate",
    "SystemStatus",
    "ExecutionStatusResponse",
    # Internal
    "ExecutionStepStatus",
    "OutputArtifact",
    "OutputBundle",
    "ActionDefinition",
    "WorkflowDefinition",
    # Services
    "ExecutionEngine",
    "get_execution_engine",
    "ExecutionRegistry",
    "get_execution_registry",
    "ProgressTracker",
    "get_progress_tracker",
    "ActionExecutor",
    "get_action_executor",
    "WorkflowRunner",
    "get_workflow_runner",
    "FileGenerator",
    "ExportService",
    "get_export_service",
    "OutputManager",
    "get_output_manager",
]
