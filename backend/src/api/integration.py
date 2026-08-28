"""
Integration API

REST API for autonomous integration layer.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.integration.events.event_bus import get_event_bus, EventType
from src.integration.pipeline.master_pipeline import get_master_pipeline
from src.integration.orchestrator.workspace_orchestrator import get_workspace_orchestrator

router = APIRouter(prefix="/integration", tags=["Integration"])


# ============================================================================
# Event Bus Endpoints
# ============================================================================

@router.get("/events")
async def get_event_history(
    event_type: Optional[str] = None,
    limit: int = 100,
):
    """Get event history."""
    event_bus = get_event_bus()
    
    events = event_bus.get_history(event_type, limit)
    
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


@router.get("/events/dead-letters")
async def get_dead_letters():
    """Get failed events."""
    event_bus = get_event_bus()
    
    dead_letters = event_bus.get_dead_letters()
    
    return {
        "dead_letters": [e.to_dict() for e in dead_letters],
        "count": len(dead_letters)
    }


@router.post("/events/dead-letters/clear")
async def clear_dead_letters():
    """Clear dead letter queue."""
    event_bus = get_event_bus()
    
    count = event_bus.clear_dead_letters()
    
    return {"cleared_count": count}


# ============================================================================
# Pipeline Endpoints
# ============================================================================

@router.post("/pipeline/process/{document_id}")
async def process_document(
    document_id: int,
    workspace_id: int,
    file_path: str,
    content_type: str = "application/pdf",
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process document through master pipeline."""
    pipeline = get_master_pipeline(db)
    
    # Run pipeline
    context = await pipeline.process(
        document_id=document_id,
        user_id=current_user.id,
        workspace_id=workspace_id,
        file_path=file_path,
        content_type=content_type
    )
    
    return {
        "document_id": context.document_id,
        "stages_completed": len([r for r in context.results.values() if r.success]),
        "total_duration_ms": sum(r.duration_ms for r in context.results.values()),
        "current_stage": context.current_stage,
        "results": {
            stage: {
                "success": result.success,
                "duration_ms": result.duration_ms,
                "error": result.error,
                "warnings": result.warnings
            }
            for stage, result in context.results.items()
        }
    }


@router.get("/pipeline/stages")
async def get_pipeline_stages():
    """Get list of pipeline stages."""
    from src.integration.pipeline.master_pipeline import ProcessingStage
    
    return {
        "stages": [
            {"name": stage.value, "order": i}
            for i, stage in enumerate(ProcessingStage)
        ]
    }


# ============================================================================
# Workspace Orchestrator Endpoints
# ============================================================================

@router.get("/orchestrator/health")
async def get_workspace_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get workspace health metrics."""
    orchestrator = get_workspace_orchestrator(db)
    
    metrics = await orchestrator.calculate_health_metrics(current_user.id)
    
    return {
        "knowledge_coverage": metrics.knowledge_coverage,
        "relationship_density": metrics.relationship_density,
        "graph_connectivity": metrics.graph_connectivity,
        "duplicate_rate": metrics.duplicate_rate,
        "validation_success_rate": metrics.validation_success_rate,
        "language_distribution": metrics.language_distribution,
        "notebook_coverage": metrics.notebook_coverage,
        "learning_progress": metrics.learning_progress,
        "workspace_completeness": metrics.workspace_completeness,
        "knowledge_freshness": metrics.knowledge_freshness
    }


@router.post("/orchestrator/workspace/{workspace_id}/initialize")
async def initialize_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initialize workspace for autonomous operations."""
    orchestrator = get_workspace_orchestrator(db)
    
    result = await orchestrator.initialize_workspace(current_user.id, workspace_id)
    
    return result


@router.post("/orchestrator/workspace/{workspace_id}/export")
async def export_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export workspace for backup."""
    orchestrator = get_workspace_orchestrator(db)
    
    result = await orchestrator.export_workspace(current_user.id, workspace_id)
    
    return result


@router.post("/orchestrator/workspace/import")
async def import_workspace(
    import_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import workspace from backup."""
    orchestrator = get_workspace_orchestrator(db)
    
    result = await orchestrator.import_workspace(current_user.id, import_data)
    
    return result


# ============================================================================
# Task Endpoints
# ============================================================================

@router.post("/orchestrator/tasks/{task_type}/trigger")
async def trigger_orchestrator_task(
    task_type: str,
    data: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger an orchestrator task."""
    from src.integration.orchestrator.workspace_orchestrator import OrchestratorTask
    
    try:
        task = OrchestratorTask(task_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {task_type}")
    
    orchestrator = get_workspace_orchestrator(db)
    
    # Queue the task
    task_handler = orchestrator._task_registry.get(task)
    
    if task_handler:
        result = await task_handler(current_user.id, data or {})
    else:
        result = {"task_triggered": True, "task_type": task_type}
    
    return {
        "task_type": task_type,
        "triggered": True,
        "result": result
    }


# ============================================================================
# Observability Endpoints
# ============================================================================

@router.get("/observability/metrics")
async def get_observability_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get observability metrics."""
    from src.autonomous.models import BackgroundJob
    
    # Get job statistics
    total_jobs = db.query(BackgroundJob).filter(
        BackgroundJob.user_id == current_user.id
    ).count()
    
    completed_jobs = db.query(BackgroundJob).filter(
        BackgroundJob.user_id == current_user.id,
        BackgroundJob.status == "completed"
    ).count()
    
    failed_jobs = db.query(BackgroundJob).filter(
        BackgroundJob.user_id == current_user.id,
        BackgroundJob.status == "failed"
    ).count()
    
    running_jobs = db.query(BackgroundJob).filter(
        BackgroundJob.user_id == current_user.id,
        BackgroundJob.status == "running"
    ).count()
    
    pending_jobs = db.query(BackgroundJob).filter(
        BackgroundJob.user_id == current_user.id,
        BackgroundJob.status == "pending"
    ).count()
    
    # Get event statistics
    event_bus = get_event_bus()
    recent_events = event_bus.get_history(limit=1000)
    dead_letters = event_bus.get_dead_letters()
    
    return {
        "jobs": {
            "total": total_jobs,
            "completed": completed_jobs,
            "failed": failed_jobs,
            "running": running_jobs,
            "pending": pending_jobs,
            "success_rate": completed_jobs / total_jobs if total_jobs > 0 else 0
        },
        "events": {
            "recent_count": len(recent_events),
            "dead_letters_count": len(dead_letters)
        }
    }


@router.get("/observability/pipeline/status")
async def get_pipeline_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current pipeline processing status."""
    from src.autonomous.models import BackgroundJob
    
    # Get active processing jobs
    processing_jobs = db.query(BackgroundJob).filter(
        BackgroundJob.user_id == current_user.id,
        BackgroundJob.status.in_(["pending", "running"])
    ).order_by(
        BackgroundJob.priority,
        BackgroundJob.created_at
    ).limit(10).all()
    
    return {
        "active_jobs": [
            {
                "job_id": j.job_id,
                "job_type": j.job_type,
                "status": j.status,
                "progress": j.progress,
                "current_step": j.current_step
            }
            for j in processing_jobs
        ],
        "active_count": len(processing_jobs)
    }
