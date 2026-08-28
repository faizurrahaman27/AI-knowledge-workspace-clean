"""
Research API

REST API for Research Operating System.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.research.models import ResearchProject, ResearchTask, ResearchEvidence
from src.research.planner_service import ResearchPlannerService
from src.research.evidence_service import EvidenceService
from src.research.conflict_service import ConflictDetectionService
from src.research.synthesis_service import SynthesisService
from src.research.report_service import ReportGenerationService

router = APIRouter(prefix="/research", tags=["Research"])


# ============================================================================
# Project Endpoints
# ============================================================================

@router.post("/projects")
async def create_project(
    title: str,
    description: Optional[str] = None,
    objective: Optional[str] = None,
    scope: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new research project."""
    service = ResearchPlannerService(db)
    
    project = service.create_project(
        user_id=current_user.id,
        title=title,
        description=description,
        objective=objective,
        scope=scope,
        keywords=keywords,
        tags=tags
    )
    
    return {"id": project.id, "title": project.title, "status": project.status}


@router.get("/projects")
async def get_projects(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's research projects."""
    service = ResearchPlannerService(db)
    
    projects = service.get_projects(current_user.id, status, limit)
    
    return [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "status": p.status,
            "progress_percentage": p.progress_percentage,
            "total_tasks": p.total_tasks,
            "completed_tasks": p.completed_tasks,
            "evidence_count": p.evidence_count,
            "created_at": p.created_at,
            "updated_at": p.updated_at
        }
        for p in projects
    ]


@router.get("/projects/{project_id}")
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a research project."""
    service = ResearchPlannerService(db)
    
    project = service.get_project(project_id, current_user.id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "objective": project.objective,
        "scope": project.scope,
        "status": project.status,
        "progress_percentage": project.progress_percentage,
        "total_tasks": project.total_tasks,
        "completed_tasks": project.completed_tasks,
        "evidence_count": project.evidence_count,
        "overall_confidence": project.overall_confidence,
        "keywords": project.keywords,
        "tags": project.tags,
        "created_at": project.created_at,
        "started_at": project.started_at,
        "completed_at": project.completed_at
    }


# ============================================================================
# Plan Endpoints
# ============================================================================

@router.post("/projects/{project_id}/plan")
async def generate_plan(
    project_id: int,
    research_goal: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a research plan."""
    service = ResearchPlannerService(db)
    
    # Verify project ownership
    project = service.get_project(project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    plan = service.generate_plan(project_id, research_goal)
    
    return {
        "id": plan.id,
        "research_goal": plan.research_goal,
        "objectives": plan.objectives,
        "research_questions": plan.research_questions,
        "subtasks": plan.subtasks,
        "estimated_complexity": plan.estimated_complexity,
        "estimated_duration_hours": plan.estimated_duration_hours
    }


# ============================================================================
# Task Endpoints
# ============================================================================

@router.get("/projects/{project_id}/tasks")
async def get_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get tasks for a project."""
    tasks = db.query(ResearchTask).filter(
        ResearchTask.project_id == project_id
    ).all()
    
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "task_type": t.task_type,
            "status": t.status,
            "priority": t.priority,
            "parent_task_id": t.parent_task_id,
            "findings": t.findings,
            "created_at": t.created_at
        }
        for t in tasks
    ]


@router.post("/tasks/{task_id}/decompose")
async def decompose_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Decompose a task into subtasks."""
    service = ResearchPlannerService(db)
    
    subtasks = service.decompose_task(task_id)
    
    return [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "task_type": s.task_type,
            "priority": s.priority,
            "parent_task_id": s.parent_task_id
        }
        for s in subtasks
    ]


@router.put("/tasks/{task_id}/status")
async def update_task_status(
    task_id: int,
    status: str,
    findings: Optional[dict] = None,
    blockers: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update task status."""
    service = ResearchPlannerService(db)
    
    task = service.update_task_status(task_id, status, findings, blockers)
    
    return {"id": task.id, "status": task.status}


# ============================================================================
# Evidence Endpoints
# ============================================================================

@router.post("/evidence")
async def add_evidence(
    project_id: int,
    title: str,
    content: str,
    source_type: str,
    source_url: Optional[str] = None,
    source_name: Optional[str] = None,
    author: Optional[str] = None,
    summary: Optional[str] = None,
    task_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add evidence to a project."""
    service = EvidenceService(db)
    
    evidence = service.add_evidence(
        project_id=project_id,
        title=title,
        content=content,
        source_type=source_type,
        source_url=source_url,
        source_name=source_name,
        author=author,
        summary=summary,
        task_id=task_id
    )
    
    return {"id": evidence.id, "title": evidence.title, "overall_score": evidence.overall_score}


@router.get("/projects/{project_id}/evidence")
async def get_evidence(
    project_id: int,
    task_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get evidence for a project."""
    query = db.query(ResearchEvidence).filter(
        ResearchEvidence.project_id == project_id
    )
    
    if task_id:
        query = query.filter(ResearchEvidence.task_id == task_id)
    
    evidence_list = query.order_by(
        ResearchEvidence.overall_score.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": e.id,
            "title": e.title,
            "summary": e.summary,
            "source_type": e.source_type,
            "source_name": e.source_name,
            "authority_score": e.authority_score,
            "overall_score": e.overall_score,
            "validation_confidence": e.validation_confidence,
            "is_validated": e.is_validated,
            "created_at": e.created_at
        }
        for e in evidence_list
    ]


@router.get("/evidence/{evidence_id}/confidence")
async def get_confidence_breakdown(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get confidence breakdown for evidence."""
    service = EvidenceService(db)
    
    return service.get_confidence_breakdown(evidence_id)


# ============================================================================
# Conflict Endpoints
# ============================================================================

@router.post("/projects/{project_id}/detect-conflicts")
async def detect_conflicts(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detect conflicts in a project."""
    service = ConflictDetectionService(db)
    
    conflicts = service.detect_conflicts(project_id)
    
    return {
        "count": len(conflicts),
        "conflicts": [
            {
                "id": c.id,
                "conflict_type": c.conflict_type,
                "description": c.description,
                "resolution_status": c.resolution_status
            }
            for c in conflicts
        ]
    }


@router.get("/projects/{project_id}/conflicts")
async def get_conflicts(
    project_id: int,
    conflict_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get conflicts for a project."""
    service = ConflictDetectionService(db)
    
    conflicts = service.get_conflicts(project_id, conflict_type)
    
    return [
        {
            "id": c.id,
            "conflict_type": c.conflict_type,
            "description": c.description,
            "evidence_a_id": c.evidence_a_id,
            "evidence_b_id": c.evidence_b_id,
            "resolution_status": c.resolution_status,
            "resolution_notes": c.resolution_notes
        }
        for c in conflicts
    ]


@router.get("/projects/{project_id}/conflict-stats")
async def get_conflict_statistics(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get conflict statistics."""
    service = ConflictDetectionService(db)
    
    return service.get_conflict_statistics(project_id)


# ============================================================================
# Report Endpoints
# ============================================================================

@router.post("/projects/{project_id}/reports")
async def generate_report(
    project_id: int,
    report_type: str = "comprehensive",
    title: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a research report."""
    service = ReportGenerationService(db)
    
    report = service.generate_report(project_id, report_type, title)
    
    return {
        "id": report.id,
        "title": report.title,
        "report_type": report.report_type,
        "research_confidence": report.research_confidence,
        "generated_at": report.generated_at
    }


@router.get("/projects/{project_id}/reports")
async def get_reports(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get reports for a project."""
    service = ReportGenerationService(db)
    
    reports = service.get_reports_for_project(project_id)
    
    return [
        {
            "id": r.id,
            "title": r.title,
            "report_type": r.report_type,
            "research_confidence": r.research_confidence,
            "generated_at": r.generated_at
        }
        for r in reports
    ]


@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a report."""
    service = ReportGenerationService(db)
    
    report = service.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "id": report.id,
        "title": report.title,
        "report_type": report.report_type,
        "executive_summary": report.executive_summary,
        "technical_summary": report.technical_summary,
        "beginner_explanation": report.beginner_explanation,
        "pros_cons": report.pros_cons,
        "consensus": report.consensus,
        "disagreements": report.disagreements,
        "open_questions": report.open_questions,
        "key_findings": report.key_findings,
        "research_confidence": report.research_confidence,
        "references": report.references,
        "generated_at": report.generated_at
    }


@router.get("/reports/{report_id}/export/markdown")
async def export_report_markdown(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export report as Markdown."""
    service = ReportGenerationService(db)
    
    return {"content": service.export_as_markdown(report_id)}


@router.get("/reports/{report_id}/export/html")
async def export_report_html(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export report as HTML."""
    service = ReportGenerationService(db)
    
    return {"content": service.export_as_html(report_id)}


# ============================================================================
# Synthesis Endpoints
# ============================================================================

@router.post("/projects/{project_id}/synthesize")
async def synthesize(
    project_id: int,
    goal: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Synthesize research findings."""
    service = SynthesisService(db)
    
    synthesis = service.synthesize(project_id, goal)
    
    return synthesis
