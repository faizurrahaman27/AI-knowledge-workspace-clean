"""
Integration Module

Autonomous Integration & Activation Layer.

This module connects all subsystems through:
- Event Bus
- Master Ingestion Pipeline
- Workspace Orchestrator
"""

from src.integration.events import (
    EventBus,
    EventType,
    Event,
    EventPublisher,
    get_event_bus,
    create_publisher,
    EventBridge,
    UnifiedEventPublisher,
    get_event_bridge,
    get_unified_event_publisher,
)

from src.integration.pipeline import (
    MasterIngestionPipeline,
    ProcessingStage,
    ProcessingResult,
    PipelineContext,
    get_master_pipeline,
)

from src.integration.orchestrator import (
    WorkspaceOrchestrator,
    OrchestratorTask,
    WorkspaceHealthMetrics,
    get_workspace_orchestrator,
)

__all__ = [
    # Events
    "EventBus",
    "EventType",
    "Event",
    "EventPublisher",
    "get_event_bus",
    "create_publisher",
    "EventBridge",
    "UnifiedEventPublisher",
    "get_event_bridge",
    "get_unified_event_publisher",
    # Pipeline
    "MasterIngestionPipeline",
    "ProcessingStage",
    "ProcessingResult",
    "PipelineContext",
    "get_master_pipeline",
    # Orchestrator
    "WorkspaceOrchestrator",
    "OrchestratorTask",
    "WorkspaceHealthMetrics",
    "get_workspace_orchestrator",
]
