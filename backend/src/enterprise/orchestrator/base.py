"""
Base Agent Classes

Abstract base classes for all agents in the enterprise architecture.
Provides common interface for agent capabilities, status tracking,
and lifecycle management.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class AgentStatus(Enum):
    """Agent lifecycle states."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    DISABLED = "disabled"


class AgentCapability(Enum):
    """Standard agent capabilities for discovery and routing."""
    # Document processing
    PDF_PROCESSING = "pdf_processing"
    WEB_EXTRACTION = "web_extraction"
    GITHUB_INTEGRATION = "github_integration"
    OCR_PROCESSING = "ocr_processing"
    VIDEO_TRANSCRIPTION = "video_transcription"
    
    # RAG capabilities
    SEMANTIC_SEARCH = "semantic_search"
    DOCUMENT_SUMMARIZATION = "document_summarization"
    QUESTION_ANSWERING = "question_answering"
    MULTI_DOCUMENT_REASONING = "multi_document_reasoning"
    
    # Study tools
    FLASHCARD_GENERATION = "flashcard_generation"
    QUIZ_GENERATION = "quiz_generation"
    MINDMAP_GENERATION = "mindmap_generation"
    SPACED_REPETITION = "spaced_repetition"
    
    # Research capabilities
    RESEARCH_SYNTHESIS = "research_synthesis"
    SOURCE_CITATION = "source_citation"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    LITERATURE_REVIEW = "literature_review"
    
    # Content creation
    ESSAY_WRITING = "essay_writing"
    NOTES_GENERATION = "notes_generation"
    EXAM_PREPARATION = "exam_preparation"
    JOB_APPLICATION = "job_application"
    
    # Math & Science
    MATH_SOLVING = "math_solving"
    CODE_GENERATION = "code_generation"
    DATA_ANALYSIS = "data_analysis"
    
    # Workflow orchestration
    TASK_PLANNING = "task_planning"
    WORKFLOW_EXECUTION = "workflow_execution"
    AGENT_COORDINATION = "agent_coordination"


@dataclass
class AgentMetadata:
    """Metadata describing an agent's identity and configuration."""
    agent_id: str
    name: str
    description: str
    version: str
    capabilities: list[AgentCapability]
    max_concurrent_tasks: int = 5
    timeout_seconds: int = 300
    requires_api_keys: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    documentation_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentContext:
    """Execution context passed to agents for each task."""
    task_id: str
    user_id: int
    workspace_id: Optional[int] = None
    document_ids: list[int] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    trace_enabled: bool = True


@dataclass
class AgentResult:
    """Result from agent execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: int = 0
    steps_executed: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Agents are specialized components that perform specific tasks.
    They are discovered and coordinated by the MasterOrchestrator.
    
    Usage:
        class MyAgent(BaseAgent):
            @property
            def metadata(self) -> AgentMetadata:
                return AgentMetadata(
                    agent_id="my_agent",
                    name="My Agent",
                    description="Does something useful",
                    capabilities=[AgentCapability.SEMANTIC_SEARCH],
                )
            
            async def execute(self, context: AgentContext) -> AgentResult:
                # Implementation
                pass
    """
    
    def __init__(self):
        self._status = AgentStatus.IDLE
        self._last_error: Optional[str] = None
        self._active_tasks: int = 0
    
    @property
    @abstractmethod
    def metadata(self) -> AgentMetadata:
        """Return agent metadata for discovery and registration."""
        pass
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent's main task.
        
        Args:
            context: Execution context with task details
            
        Returns:
            AgentResult with output, artifacts, and execution trace
        """
        pass
    
    async def initialize(self) -> None:
        """
        Initialize the agent (e.g., load models, establish connections).
        Called once before the agent is used.
        """
        self._status = AgentStatus.INITIALIZING
        # Default implementation does nothing
        # Override to add initialization logic
        self._status = AgentStatus.READY
    
    async def shutdown(self) -> None:
        """
        Graceful shutdown (e.g., release resources, save state).
        Called when the application is shutting down.
        """
        self._status = AgentStatus.DISABLED
    
    @property
    def status(self) -> AgentStatus:
        """Current agent status."""
        return self._status
    
    @property
    def is_available(self) -> bool:
        """Check if agent can accept new tasks."""
        if self._status not in (AgentStatus.READY, AgentStatus.BUSY):
            return False
        return self._active_tasks < self.metadata.max_concurrent_tasks
    
    @property
    def last_error(self) -> Optional[str]:
        """Last error encountered by the agent."""
        return self._last_error
    
    def _mark_busy(self) -> None:
        """Mark agent as processing a task."""
        self._active_tasks += 1
        if self._active_tasks == 1:
            self._status = AgentStatus.BUSY
    
    def _mark_idle(self) -> None:
        """Mark agent as available for new tasks."""
        self._active_tasks = max(0, self._active_tasks - 1)
        if self._active_tasks == 0 and self._status == AgentStatus.BUSY:
            self._status = AgentStatus.READY
    
    def _set_error(self, error: str) -> None:
        """Record an error state."""
        self._last_error = error
        self._status = AgentStatus.ERROR
    
    def reset_error(self) -> None:
        """Clear error state and return to ready."""
        self._last_error = None
        if self._status == AgentStatus.ERROR:
            self._status = AgentStatus.READY
