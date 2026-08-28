"""
Autonomous System API

REST API for Knowledge Graph, Notebooks, Learning Paths, Insights, and Background Workers.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.autonomous.models import KnowledgeNode, IntelligentNotebook, LearningPath, KnowledgeInsight, BackgroundJob
from src.autonomous.services import (
    KnowledgeGraphService,
    IntelligentNotebookService,
    LearningPathService,
    InsightService,
    BackgroundWorker
)

router = APIRouter(prefix="/autonomous", tags=["Autonomous"])


# ============================================================================
# Knowledge Graph Endpoints
# ============================================================================

@router.get("/graph/stats")
async def get_graph_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get knowledge graph statistics."""
    service = KnowledgeGraphService(db)
    
    return service.get_graph_statistics(current_user.id)


@router.get("/graph/nodes")
async def get_nodes(
    entity_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get knowledge nodes."""
    query = db.query(KnowledgeNode).filter(
        KnowledgeNode.user_id == current_user.id
    )
    
    if entity_type:
        query = query.filter(KnowledgeNode.entity_type == entity_type)
    
    nodes = query.order_by(
        KnowledgeNode.importance_score.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": n.node_id,
            "name": n.name,
            "entity_type": n.entity_type,
            "description": n.description,
            "confidence": n.confidence_score,
            "importance": n.importance_score,
            "connections": n.in_degree + n.out_degree
        }
        for n in nodes
    ]


@router.get("/graph/nodes/{node_id}")
async def get_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get node details."""
    node = db.query(KnowledgeNode).filter(
        KnowledgeNode.id == node_id,
        KnowledgeNode.user_id == current_user.id
    ).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    return {
        "id": node.node_id,
        "name": node.name,
        "entity_type": node.entity_type,
        "description": node.description,
        "aliases": node.aliases,
        "confidence": node.confidence_score,
        "importance": node.importance_score,
        "in_degree": node.in_degree,
        "out_degree": node.out_degree,
        "first_seen": node.first_seen_at,
        "last_updated": node.last_updated_at
    }


@router.get("/graph/subgraph/{node_id}")
async def get_subgraph(
    node_id: int,
    depth: int = 2,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get subgraph around a node."""
    # Verify ownership
    node = db.query(KnowledgeNode).filter(
        KnowledgeNode.id == node_id,
        KnowledgeNode.user_id == current_user.id
    ).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    service = KnowledgeGraphService(db)
    
    return service.get_subgraph(node_id, depth)


@router.get("/graph/path")
async def find_path(
    source: str,
    target: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Find shortest path between nodes."""
    service = KnowledgeGraphService(db)
    
    path = service.find_shortest_path(source, target, current_user.id)
    
    if not path:
        return {"path": None, "message": "No path found"}
    
    return {"path": path}


@router.get("/graph/connected/{node_id}")
async def get_connected(
    node_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get connected nodes."""
    service = KnowledgeGraphService(db)
    
    return service.get_connected_concepts(node_id, limit)


@router.post("/graph/build/{document_id}")
async def build_graph(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Build knowledge graph from document."""
    service = KnowledgeGraphService(db)
    
    result = service.build_from_entities(document_id, current_user.id)
    
    return result


# ============================================================================
# Intelligent Notebook Endpoints
# ============================================================================

@router.post("/notebooks")
async def create_notebook(
    title: str,
    description: Optional[str] = None,
    document_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an intelligent notebook."""
    service = IntelligentNotebookService(db)
    
    notebook = service.create_notebook(
        user_id=current_user.id,
        title=title,
        description=description,
        document_ids=document_ids
    )
    
    return {
        "id": notebook.notebook_id,
        "title": notebook.title,
        "created_at": notebook.created_at
    }


@router.get("/notebooks")
async def get_notebooks(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's notebooks."""
    service = IntelligentNotebookService(db)
    
    notebooks = service.get_user_notebooks(current_user.id, limit)
    
    return [
        {
            "id": n.notebook_id,
            "title": n.title,
            "description": n.description,
            "document_count": n.document_count,
            "knowledge_confidence": n.knowledge_confidence,
            "updated_at": n.updated_at
        }
        for n in notebooks
    ]


@router.get("/notebooks/{notebook_id}")
async def get_notebook(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get notebook details."""
    service = IntelligentNotebookService(db)
    
    notebook = service.get_notebook(notebook_id)
    
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    
    if notebook.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Generate insights
    insights = service.generate_notebook_insights(notebook_id)
    
    return {
        "id": notebook.notebook_id,
        "title": notebook.title,
        "description": notebook.description,
        "auto_summary": notebook.auto_summary,
        "auto_timeline": notebook.auto_timeline,
        "auto_concept_map": notebook.auto_concept_map,
        "document_count": notebook.document_count,
        "concept_count": notebook.concept_count,
        "entity_count": notebook.entity_count,
        "question_count": notebook.question_count,
        "flashcard_count": notebook.flashcard_count,
        "knowledge_confidence": notebook.knowledge_confidence,
        "insights": insights,
        "updated_at": notebook.updated_at
    }


@router.post("/notebooks/{notebook_id}/documents/{document_id}")
async def add_document_to_notebook(
    notebook_id: str,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add document to notebook."""
    service = IntelligentNotebookService(db)
    
    notebook = service.add_document(notebook_id, document_id)
    
    return {"document_count": notebook.document_count}


@router.post("/notebooks/{notebook_id}/generate")
async def generate_notebook_content(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate notebook content (timeline, concept map)."""
    service = IntelligentNotebookService(db)
    
    # Generate timeline
    timeline = service.generate_timeline(notebook_id)
    
    # Generate concept map
    concept_map = service.generate_concept_map(notebook_id)
    
    # Update notebook
    service.update_notebook_content(
        notebook_id,
        auto_timeline=timeline,
        auto_concept_map=concept_map
    )
    
    return {
        "timeline_generated": len(timeline),
        "concept_map_nodes": len(concept_map.get("nodes", []))
    }


# ============================================================================
# Learning Path Endpoints
# ============================================================================

@router.post("/learning-paths")
async def create_learning_path(
    topic: str,
    title: Optional[str] = None,
    document_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a learning path."""
    service = LearningPathService(db)
    
    path = service.create_learning_path(
        user_id=current_user.id,
        topic=topic,
        title=title,
        document_ids=document_ids
    )
    
    return {
        "id": path.path_id,
        "title": path.title,
        "topic": path.topic,
        "created_at": path.created_at
    }


@router.get("/learning-paths")
async def get_learning_paths(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's learning paths."""
    paths = db.query(LearningPath).filter(
        LearningPath.user_id == current_user.id
    ).all()
    
    return [
        {
            "id": p.path_id,
            "title": p.title,
            "topic": p.topic,
            "completion_percentage": p.completion_percentage,
            "total_estimated_hours": p.total_estimated_hours,
            "updated_at": p.updated_at
        }
        for p in paths
    ]


@router.get("/learning-paths/{path_id}")
async def get_learning_path(
    path_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get learning path details."""
    service = LearningPathService(db)
    
    path = service.get_path(path_id)
    
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    
    if path.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "id": path.path_id,
        "title": path.title,
        "topic": path.topic,
        "description": path.description,
        "steps": path.steps,
        "prerequisites": path.prerequisites,
        "completion_percentage": path.completion_percentage,
        "current_step": path.current_step,
        "total_estimated_hours": path.total_estimated_hours,
        "recommended_documents": path.recommended_documents
    }


@router.post("/learning-paths/{path_id}/generate")
async def generate_learning_steps(
    path_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate learning steps for path."""
    service = LearningPathService(db)
    
    path = service.generate_steps(path_id)
    
    return {
        "steps_generated": len(path.steps or [])
    }


@router.put("/learning-paths/{path_id}/progress")
async def update_learning_progress(
    path_id: str,
    completed_step: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update learning path progress."""
    service = LearningPathService(db)
    
    path = service.update_progress(path_id, completed_step)
    
    return {
        "completion_percentage": path.completion_percentage,
        "current_step": path.current_step
    }


# ============================================================================
# Insights Endpoints
# ============================================================================

@router.get("/insights")
async def get_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get knowledge insights."""
    service = InsightService(db)
    
    insights = service.generate_insights(current_user.id)
    
    return [
        {
            "id": i.insight_id,
            "type": i.insight_type,
            "title": i.title,
            "description": i.description,
            "importance": i.importance_score,
            "created_at": i.created_at
        }
        for i in insights
    ]


# ============================================================================
# Background Jobs Endpoints
# ============================================================================

@router.get("/jobs")
async def get_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's background jobs."""
    service = BackgroundWorker(db)
    
    jobs = service.get_user_jobs(current_user.id, status, limit)
    
    return [
        {
            "id": j.job_id,
            "type": j.job_type,
            "name": j.job_name,
            "status": j.status,
            "progress": j.progress,
            "current_step": j.current_step,
            "created_at": j.created_at,
            "completed_at": j.completed_at
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get job details."""
    service = BackgroundWorker(db)
    
    job = service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "id": job.job_id,
        "type": job.job_type,
        "name": job.job_name,
        "target_type": job.target_type,
        "target_id": job.target_id,
        "status": job.status,
        "progress": job.progress,
        "current_step": job.current_step,
        "output_data": job.output_data,
        "error_message": job.error_message,
        "retry_count": job.retry_count,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at
    }


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry a failed job."""
    service = BackgroundWorker(db)
    
    job = service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    job = service.retry_job(job_id)
    
    return {"status": job.status, "retry_count": job.retry_count}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a job."""
    service = BackgroundWorker(db)
    
    job = service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    job = service.cancel_job(job_id)
    
    return {"status": job.status}
