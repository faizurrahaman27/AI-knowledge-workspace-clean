"""
Multi-Agent System Module

Autonomous multi-agent orchestration for AI workspace.
"""

from src.multi_agent.models import (
    Agent,
    WorkflowExecution,
    TaskExecution,
    AgentMemory,
    AgentMetrics,
    AgentEvent,
    AgentStatus,
    ExecutionStatus,
    TaskStatus,
    WorkflowStatus,
)

from src.multi_agent.registry.registry import (
    AgentRegistry,
    AgentMetadata,
    AgentCapabilities,
    get_agent_registry,
)

from src.multi_agent.orchestrator.master import (
    MasterOrchestrator,
    WorkflowGoal,
    TaskDefinition,
    ExecutionResult,
)

from src.multi_agent.agents.services import (
    AgentManagerService,
    WorkflowService,
    MemoryService,
    MetricsService,
)

__all__ = [
    # Models
    "Agent",
    "WorkflowExecution",
    "TaskExecution",
    "AgentMemory",
    "AgentMetrics",
    "AgentEvent",
    "AgentStatus",
    "ExecutionStatus",
    "TaskStatus",
    "WorkflowStatus",
    # Registry
    "AgentRegistry",
    "AgentMetadata",
    "AgentCapabilities",
    "get_agent_registry",
    # Orchestrator
    "MasterOrchestrator",
    "WorkflowGoal",
    "TaskDefinition",
    "ExecutionResult",
    # Services
    "AgentManagerService",
    "WorkflowService",
    "MemoryService",
    "MetricsService",
]
