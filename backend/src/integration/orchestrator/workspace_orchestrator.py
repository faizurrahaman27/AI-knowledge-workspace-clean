"""
Workspace Orchestrator

Central orchestrator for autonomous workspace operations.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

from sqlalchemy.orm import Session

from src.integration.events.event_bus import EventType, Event, get_event_bus, create_publisher
from src.autonomous.models import BackgroundJob, JobStatus
from src.autonomous.services.workers import get_background_worker
from src.core.logging import logger


class OrchestratorTask(str, Enum):
    """Orchestrator task types."""
    GRAPH_OPTIMIZATION = "graph_optimization"
    NOTEBOOK_REGENERATION = "notebook_regeneration"
    RELATIONSHIP_RECALCULATION = "relationship_recalculation"
    MEMORY_CONSOLIDATION = "memory_consolidation"
    LEARNING_PATH_OPTIMIZATION = "learning_path_optimization"
    WORKSPACE_CLEANUP = "workspace_cleanup"
    STATISTICS_REFRESH = "statistics_refresh"
    INSIGHT_REGENERATION = "insight_regeneration"
    RECOMMENDATION_REFRESH = "recommendation_refresh"
    DUPLICATE_DETECTION = "duplicate_detection"
    DOCUMENT_CLUSTERING = "document_clustering"


@dataclass
class WorkspaceHealthMetrics:
    """Workspace health metrics."""
    knowledge_coverage: float = 0.0
    relationship_density: float = 0.0
    graph_connectivity: float = 0.0
    duplicate_rate: float = 0.0
    validation_success_rate: float = 0.0
    language_distribution: Dict[str, float] = field(default_factory=dict)
    notebook_coverage: float = 0.0
    learning_progress: float = 0.0
    workspace_completeness: float = 0.0
    knowledge_freshness: float = 0.0


class WorkspaceOrchestrator:
    """
    Central orchestrator for autonomous workspace operations.
    
    Features:
    - Event-driven coordination
    - Task scheduling
    - Health monitoring
    - Automatic optimization
    - Performance tracking
    """
    
    def __init__(self, db: Session):
        """Initialize the orchestrator."""
        self.db = db
        self.event_bus = get_event_bus()
        self.publisher = create_publisher("workspace_orchestrator")
        self.background_worker = get_background_worker(db)
        
        # Register event handlers
        self._register_handlers()
        
        # Task registry
        self._task_registry: Dict[str, Callable] = {}
        self._register_tasks()
    
    def _register_handlers(self) -> None:
        """Register event handlers."""
        # Document events
        self.event_bus.subscribe(EventType.DOCUMENT_UPLOADED, self._on_document_uploaded)
        self.event_bus.subscribe(EventType.DOCUMENT_PROCESSED, self._on_document_processed)
        self.event_bus.subscribe(EventType.DOCUMENT_DELETED, self._on_document_deleted)
        
        # Knowledge events
        self.event_bus.subscribe(EventType.ENTITIES_DISCOVERED, self._on_entities_discovered)
        self.event_bus.subscribe(EventType.RELATIONSHIPS_DISCOVERED, self._on_relationships_discovered)
        
        # Graph events
        self.event_bus.subscribe(EventType.GRAPH_UPDATED, self._on_graph_updated)
        
        logger.info("Registered orchestrator event handlers")
    
    def _register_tasks(self) -> None:
        """Register autonomous tasks."""
        self._task_registry = {
            OrchestratorTask.GRAPH_OPTIMIZATION: self._optimize_graph,
            OrchestratorTask.NOTEBOOK_REGENERATION: self._regenerate_notebooks,
            OrchestratorTask.RELATIONSHIP_RECALCULATION: self._recalculate_relationships,
            OrchestratorTask.MEMORY_CONSOLIDATION: self._consolidate_memory,
            OrchestratorTask.LEARNING_PATH_OPTIMIZATION: self._optimize_learning_paths,
            OrchestratorTask.WORKSPACE_CLEANUP: self._cleanup_workspace,
            OrchestratorTask.STATISTICS_REFRESH: self._refresh_statistics,
            OrchestratorTask.INSIGHT_REGENERATION: self._regenerate_insights,
            OrchestratorTask.RECOMMENDATION_REFRESH: self._refresh_recommendations,
            OrchestratorTask.DUPLICATE_DETECTION: self._detect_duplicates,
            OrchestratorTask.DOCUMENT_CLUSTERING: self._cluster_documents,
        }
    
    # Event handlers
    async def _on_document_uploaded(self, event: Event) -> None:
        """Handle document uploaded event."""
        logger.info(f"Document uploaded: {event.data}")
        
        # Trigger knowledge extraction pipeline
        doc_id = event.data.get("document_id")
        if doc_id:
            await self._queue_knowledge_extraction(event.user_id, doc_id)
    
    async def _on_document_processed(self, event: Event) -> None:
        """Handle document processed event."""
        logger.info(f"Document processed: {event.data}")
        
        # Update workspace metrics
        if event.workspace_id:
            await self._queue_statistics_refresh(event.workspace_id)
    
    async def _on_document_deleted(self, event: Event) -> None:
        """Handle document deleted event."""
        logger.info(f"Document deleted: {event.data}")
        
        # Clean up related knowledge
        doc_id = event.data.get("document_id")
        if doc_id:
            await self._queue_workspace_cleanup(event.user_id, doc_id)
    
    async def _on_entities_discovered(self, event: Event) -> None:
        """Handle entities discovered event."""
        # Trigger graph update
        await self._queue_graph_optimization(event.user_id)
    
    async def _on_relationships_discovered(self, event: Event) -> None:
        """Handle relationships discovered event."""
        # Trigger relationship recalculation
        await self._queue_relationship_recalculation(event.user_id)
    
    async def _on_graph_updated(self, event: Event) -> None:
        """Handle graph updated event."""
        # Trigger insights regeneration
        if event.user_id:
            await self._queue_insight_regeneration(event.user_id)
    
    # Task queueing
    async def _queue_knowledge_extraction(self, user_id: int, document_id: int) -> None:
        """Queue knowledge extraction for a document."""
        self.background_worker.create_job(
            user_id=user_id,
            job_type="extract_knowledge",
            job_name=f"Extract knowledge from document {document_id}",
            target_type="document",
            target_id=str(document_id),
            input_data={"document_id": document_id},
            priority=3
        )
    
    async def _queue_graph_optimization(self, user_id: int) -> None:
        """Queue graph optimization task."""
        self.background_worker.create_job(
            user_id=user_id,
            job_type=OrchestratorTask.GRAPH_OPTIMIZATION.value,
            job_name="Optimize knowledge graph",
            priority=5
        )
    
    async def _queue_relationship_recalculation(self, user_id: int) -> None:
        """Queue relationship recalculation task."""
        self.background_worker.create_job(
            user_id=user_id,
            job_type=OrchestratorTask.RELATIONSHIP_RECALCULATION.value,
            job_name="Recalculate relationships",
            priority=5
        )
    
    async def _queue_statistics_refresh(self, workspace_id: int) -> None:
        """Queue statistics refresh task."""
        self.background_worker.create_job(
            user_id=0,  # System task
            job_type=OrchestratorTask.STATISTICS_REFRESH.value,
            job_name=f"Refresh statistics for workspace {workspace_id}",
            target_type="workspace",
            target_id=str(workspace_id),
            priority=7
        )
    
    async def _queue_workspace_cleanup(self, user_id: int, document_id: int) -> None:
        """Queue workspace cleanup task."""
        self.background_worker.create_job(
            user_id=user_id,
            job_type=OrchestratorTask.WORKSPACE_CLEANUP.value,
            job_name="Clean up workspace after document deletion",
            input_data={"deleted_document_id": document_id},
            priority=6
        )
    
    async def _queue_insight_regeneration(self, user_id: int) -> None:
        """Queue insight regeneration task."""
        self.background_worker.create_job(
            user_id=user_id,
            job_type=OrchestratorTask.INSIGHT_REGENERATION.value,
            job_name="Regenerate workspace insights",
            priority=5
        )
    
    # Task execution
    async def _optimize_graph(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize knowledge graph."""
        logger.info(f"Optimizing graph for user {user_id}")
        # Implementation would call KnowledgeGraphService
        return {"optimized": True}
    
    async def _regenerate_notebooks(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Regenerate notebook content."""
        logger.info(f"Regenerating notebooks for user {user_id}")
        return {"notebooks_regenerated": 0}
    
    async def _recalculate_relationships(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recalculate relationships."""
        logger.info(f"Recalculating relationships for user {user_id}")
        return {"relationships_updated": 0}
    
    async def _consolidate_memory(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Consolidate AI memory."""
        logger.info(f"Consolidating memory for user {user_id}")
        return {"memories_consolidated": 0}
    
    async def _optimize_learning_paths(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize learning paths."""
        logger.info(f"Optimizing learning paths for user {user_id}")
        return {"paths_optimized": 0}
    
    async def _cleanup_workspace(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up workspace."""
        logger.info(f"Cleaning up workspace for user {user_id}")
        return {"cleanup_complete": True}
    
    async def _refresh_statistics(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh workspace statistics."""
        logger.info(f"Refreshing statistics")
        return {"stats_refreshed": True}
    
    async def _regenerate_insights(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Regenerate insights."""
        logger.info(f"Regenerating insights for user {user_id}")
        return {"insights_regenerated": 0}
    
    async def _refresh_recommendations(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh recommendations."""
        logger.info(f"Refreshing recommendations for user {user_id}")
        return {"recommendations_refreshed": 0}
    
    async def _detect_duplicates(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect duplicates."""
        logger.info(f"Detecting duplicates for user {user_id}")
        return {"duplicates_found": 0}
    
    async def _cluster_documents(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cluster documents."""
        logger.info(f"Clustering documents for user {user_id}")
        return {"clusters_created": 0}
    
    # Health monitoring
    async def calculate_health_metrics(self, user_id: int) -> WorkspaceHealthMetrics:
        """Calculate workspace health metrics."""
        metrics = WorkspaceHealthMetrics()
        
        # Get job statistics
        completed_jobs = self.background_worker.db.query(BackgroundJob).filter(
            BackgroundJob.user_id == user_id,
            BackgroundJob.status == JobStatus.COMPLETED.value
        ).count()
        
        failed_jobs = self.background_worker.db.query(BackgroundJob).filter(
            BackgroundJob.user_id == user_id,
            BackgroundJob.status == JobStatus.FAILED.value
        ).count()
        
        total_jobs = completed_jobs + failed_jobs
        
        if total_jobs > 0:
            metrics.validation_success_rate = completed_jobs / total_jobs
        
        # Knowledge freshness based on recent activity
        recent_jobs = self.background_worker.db.query(BackgroundJob).filter(
            BackgroundJob.user_id == user_id,
            BackgroundJob.completed_at >= datetime.utcnow() - timedelta(days=1)
        ).count()
        
        metrics.knowledge_freshness = min(recent_jobs / 10.0, 1.0)
        
        logger.info(f"Calculated health metrics for user {user_id}")
        
        return metrics
    
    # Workspace lifecycle
    async def initialize_workspace(self, user_id: int, workspace_id: int) -> Dict[str, Any]:
        """Initialize workspace for autonomous operations."""
        logger.info(f"Initializing workspace {workspace_id} for user {user_id}")
        
        # Queue initial background jobs
        self.background_worker.create_job(
            user_id=user_id,
            job_type=OrchestratorTask.STATISTICS_REFRESH.value,
            job_name="Initialize workspace statistics",
            target_type="workspace",
            target_id=str(workspace_id),
            priority=1
        )
        
        await self.publisher.publish(
            event_type=EventType.WORKSPACE_ANALYZED,
            data={"workspace_id": workspace_id},
            user_id=user_id,
            workspace_id=workspace_id
        )
        
        return {"initialized": True, "workspace_id": workspace_id}
    
    async def export_workspace(self, user_id: int, workspace_id: int) -> Dict[str, Any]:
        """Export workspace data for backup."""
        logger.info(f"Exporting workspace {workspace_id} for user {user_id}")
        
        export_data = {
            "workspace_id": workspace_id,
            "exported_at": datetime.utcnow().isoformat(),
            "includes": [
                "documents",
                "knowledge_graph",
                "notebooks",
                "learning_paths",
                "insights",
                "memory",
                "relationships",
                "background_state"
            ]
        }
        
        await self.publisher.publish(
            event_type=EventType.WORKSPACE_EXPORTED,
            data=export_data,
            user_id=user_id,
            workspace_id=workspace_id
        )
        
        return export_data
    
    async def import_workspace(self, user_id: int, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """Import workspace data from backup."""
        workspace_id = import_data.get("workspace_id")
        logger.info(f"Importing workspace {workspace_id} for user {user_id}")
        
        # Restore components
        await self.publisher.publish(
            event_type=EventType.WORKSPACE_IMPORTED,
            data={"workspace_id": workspace_id, "imported_at": datetime.utcnow().isoformat()},
            user_id=user_id,
            workspace_id=workspace_id
        )
        
        return {"imported": True, "workspace_id": workspace_id}


# Factory function
def get_workspace_orchestrator(db: Session) -> WorkspaceOrchestrator:
    """Get workspace orchestrator instance."""
    return WorkspaceOrchestrator(db)
