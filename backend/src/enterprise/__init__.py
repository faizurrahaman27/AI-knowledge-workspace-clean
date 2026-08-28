"""
Enterprise Architecture Module

This module provides the foundational infrastructure for enterprise-grade
multi-agent orchestration, including:

- Master Orchestrator: Coordinates agent workflows and task execution
- Agent Registry: Discovers and manages available agents
- Task Dispatcher: Routes tasks to appropriate agents
- Workflow Engine: Defines and executes complex multi-step workflows
- Event System: Extended WebSocket events for real-time progress tracking

All components are designed with SOLID principles and support:
- Plugin-based agent architecture
- Async/await for I/O-bound operations
- Type hints for IDE support
- Extensible event system
"""

from src.enterprise.orchestrator.master import MasterOrchestrator
from src.enterprise.orchestrator.base import BaseAgent, AgentCapability, AgentStatus
from src.enterprise.registry.registry import AgentRegistry
from src.enterprise.dispatcher.task_dispatcher import TaskDispatcher, Task, TaskPriority, TaskStatus
from src.enterprise.workflows.engine import WorkflowEngine, Workflow, WorkflowStep
from src.enterprise.events.manager import EnterpriseEventManager, WorkflowEvent, EventType

__all__ = [
    # Orchestrator
    "MasterOrchestrator",
    "BaseAgent",
    "AgentCapability",
    "AgentStatus",
    # Registry
    "AgentRegistry",
    # Dispatcher
    "TaskDispatcher",
    "Task",
    "TaskPriority",
    "TaskStatus",
    # Workflows
    "WorkflowEngine",
    "Workflow",
    "WorkflowStep",
    # Events
    "EnterpriseEventManager",
    "WorkflowEvent",
    "EventType",
]
