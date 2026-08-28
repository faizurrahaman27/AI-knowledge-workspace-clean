"""
Execution Schemas

Pydantic schemas for the AI Execution Layer.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class ExecutionStatus(str, Enum):
    """Execution status."""
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class OutputFormat(str, Enum):
    """Output file formats."""
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    CSV = "csv"
    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"
    ZIP = "zip"


class ActionType(str, Enum):
    """Types of executable actions."""
    GENERATE = "generate"
    EXTRACT = "extract"
    ANALYZE = "analyze"
    TRANSFORM = "transform"
    EXPORT = "export"
    COMMUNICATE = "communicate"


# ============================================================================
# Execution Request/Response
# ============================================================================

class ExecutionRequest(BaseModel):
    """Request to execute an action."""
    action_id: str = Field(..., description="Action to execute")
    document_id: Optional[int] = Field(None, description="Source document")
    workspace_id: Optional[int] = Field(None, description="Target workspace")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    output_format: Optional[OutputFormat] = Field(None, description="Desired output format")
    language: Optional[str] = Field("en", description="Output language")
    user_id: Optional[int] = Field(None, description="User ID")


class WorkflowExecutionRequest(BaseModel):
    """Request to execute a workflow."""
    workflow_id: str = Field(..., description="Workflow template ID")
    document_id: Optional[int] = Field(None, description="Source document")
    workspace_id: Optional[int] = Field(None, description="Target workspace")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Workflow parameters")
    output_format: Optional[OutputFormat] = Field(OutputFormat.ZIP, description="Output format")
    language: Optional[str] = Field("en", description="Output language")
    user_id: Optional[int] = Field(None, description="User ID")


class ExecutionStepStatus(BaseModel):
    """Status of an execution step."""
    step_name: str
    status: ExecutionStatus
    progress: int = Field(ge=0, le=100, default=0)
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_file: Optional[str] = None


class ExecutionResponse(BaseModel):
    """Response from execution."""
    execution_id: str
    action_id: str
    status: ExecutionStatus
    progress: int = Field(ge=0, le=100, default=0)
    current_step: Optional[str] = None
    steps: List[ExecutionStepStatus] = Field(default_factory=list)
    outputs: List["OutputArtifact"] = Field(default_factory=list)
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


# ============================================================================
# Output Management
# ============================================================================

class OutputArtifact(BaseModel):
    """An output file artifact."""
    filename: str
    format: OutputFormat
    size_bytes: Optional[int] = None
    path: Optional[str] = None
    url: Optional[str] = None
    download_url: Optional[str] = None
    content_type: str = "application/octet-stream"
    is_primary: bool = False


class OutputBundle(BaseModel):
    """Bundle of output artifacts."""
    execution_id: str
    artifacts: List[OutputArtifact] = Field(default_factory=list)
    primary_artifact: Optional[OutputArtifact] = None
    zip_url: Optional[str] = None
    total_size_bytes: int = 0


# ============================================================================
# Execution Registry
# ============================================================================

class ActionDefinition(BaseModel):
    """Definition of an executable action."""
    action_id: str
    name: str
    description: str
    action_type: ActionType
    category: str
    supported_formats: List[OutputFormat] = Field(default_factory=list)
    supported_document_types: List[str] = Field(default_factory=list)
    required_parameters: Dict[str, Any] = Field(default_factory=dict)
    estimated_duration_seconds: int = 60
    tags: List[str] = Field(default_factory=list)


class WorkflowDefinition(BaseModel):
    """Definition of an executable workflow."""
    workflow_id: str
    name: str
    description: str
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_duration_seconds: int = 300
    produces_formats: List[OutputFormat] = Field(default_factory=list)


# ============================================================================
# Execution History
# ============================================================================

class ExecutionHistory(BaseModel):
    """Execution history entry."""
    execution_id: str
    action_id: str
    workflow_id: Optional[str] = None
    status: ExecutionStatus
    progress: int
    document_id: Optional[int] = None
    workspace_id: Optional[int] = None
    output_format: Optional[OutputFormat] = None
    outputs_count: int = 0
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class ExecutionHistoryResponse(BaseModel):
    """Response with execution history."""
    executions: List[ExecutionHistory] = Field(default_factory=list)
    total_count: int
    page: int = 1
    page_size: int = 20


# ============================================================================
# Execution Templates
# ============================================================================

class ExecutionTemplate(BaseModel):
    """Template for common execution patterns."""
    template_id: str
    name: str
    description: str
    workflow_id: str
    recommended_for: List[str] = Field(default_factory=list)
    output_formats: List[OutputFormat] = Field(default_factory=list)


class TemplatesResponse(BaseModel):
    """Response with available templates."""
    templates: List[ExecutionTemplate] = Field(default_factory=list)
    total_count: int


# ============================================================================
# Execution Status Response
# ============================================================================

class SystemStatus(BaseModel):
    """Overall execution system status."""
    total_executions: int
    active_executions: int
    completed_today: int
    failed_today: int
    average_duration_ms: int
    supported_formats: List[str]
    registered_actions: int
    registered_workflows: int


class ExecutionStatusResponse(BaseModel):
    """Response with execution status."""
    status: SystemStatus


# Update forward references
ExecutionResponse.model_rebuild()
