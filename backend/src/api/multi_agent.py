"""
Multi-Agent System API

REST API for autonomous multi-agent orchestration.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.multi_agent.models import (
    Agent, WorkflowExecution, TaskExecution, WorkflowStatus, AgentStatus
)
from src.multi_agent.agents.services import (
    AgentManagerService, WorkflowService, MemoryService, MetricsService
)
from src.multi_agent.orchestrator.master import MasterOrchestrator, WorkflowGoal
from src.multi_agent.registry.registry import AgentCapabilities

router = APIRouter(prefix="/multi-agent", tags=["Multi-Agent"])


# ============================================================================
# Agent Endpoints
# ============================================================================

@router.post("/agents")
async def register_agent(
    agent_id: str,
    name: str,
    description: str,
    capabilities: Dict[str, bool],
    version: str = "1.0.0",
    priority: int = 5,
    supported_tools: Optional[List[str]] = None,
    db: Session = Depends(get_db),
):
    """Register a new agent."""
    service = AgentManagerService(db)
    
    agent = service.register_agent(
        agent_id=agent_id,
        name=name,
        description=description,
        capabilities=capabilities,
        version=version,
        priority=priority,
        supported_tools=supported_tools
    )
    
    return {"id": agent.id, "agent_id": agent.agent_id, "name": agent.name}


@router.get("/agents")
async def get_agents(db: Session = Depends(get_db)):
    """Get all registered agents."""
    service = AgentManagerService(db)
    agents = service.get_all_agents()
    
    return [
        {
            "id": a.id,
            "agent_id": a.agent_id,
            "name": a.name,
            "description": a.description,
            "version": a.version,
            "capabilities": a.capabilities,
            "status": a.status,
            "health_status": a.health_status
        }
        for a in agents
    ]


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get agent by ID."""
    service = AgentManagerService(db)
    agent = service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "id": agent.id,
        "agent_id": agent.agent_id,
        "name": agent.name,
        "description": agent.description,
        "capabilities": agent.capabilities,
        "supported_tools": agent.supported_tools,
        "priority": agent.priority,
        "status": agent.status,
        "health_status": agent.health_status,
        "last_heartbeat": agent.last_heartbeat
    }


@router.get("/agents/health")
async def get_health_status(db: Session = Depends(get_db)):
    """Get overall agent health status."""
    service = AgentManagerService(db)
    return service.get_health_status()


@router.get("/agents/capabilities")
async def get_agents_by_capability(
    capability: str,
    db: Session = Depends(get_db)
):
    """Get agents by capability."""
    service = AgentManagerService(db)
    agents = service.get_agents_by_capability(capability)
    
    return [
        {
            "agent_id": a.agent_id,
            "name": a.name,
            "description": a.description
        }
        for a in agents
    ]


@router.delete("/agents/{agent_id}")
async def unregister_agent(agent_id: str, db: Session = Depends(get_db)):
    """Unregister an agent."""
    service = AgentManagerService(db)
    
    if not service.unregister_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"status": "unregistered"}


# ============================================================================
# Workflow Endpoints
# ============================================================================

@router.post("/workflows")
async def create_workflow(
    goal: str,
    context: Optional[Dict[str, Any]] = None,
    capabilities_needed: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create and execute a new workflow."""
    orchestrator = MasterOrchestrator(db)
    
    workflow_goal = WorkflowGoal(
        goal=goal,
        context=context,
        capabilities_needed=capabilities_needed or [],
        user_id=current_user.id
    )
    
    result = await orchestrator.execute_workflow(workflow_goal)
    
    return {
        "workflow_id": result.workflow_id,
        "success": result.success,
        "execution_time_ms": result.execution_time_ms,
        "error": result.error_message
    }


@router.get("/workflows")
async def get_workflows(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's workflows."""
    service = WorkflowService(db)
    workflows = service.get_user_workflows(
        current_user.id, status, limit
    )
    
    return [
        {
            "workflow_id": w.workflow_id,
            "title": w.title,
            "goal": w.goal,
            "status": w.status,
            "total_tasks": w.total_tasks,
            "completed_tasks": w.completed_tasks,
            "created_at": w.created_at,
            "completed_at": w.completed_at
        }
        for w in workflows
    ]


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get workflow by ID."""
    service = WorkflowService(db)
    workflow = service.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tasks = service.get_workflow_tasks(workflow_id)
    
    return {
        "workflow_id": workflow.workflow_id,
        "title": workflow.title,
        "goal": workflow.goal,
        "status": workflow.status,
        "total_tasks": workflow.total_tasks,
        "completed_tasks": workflow.completed_tasks,
        "failed_tasks": workflow.failed_tasks,
        "final_result": workflow.final_result,
        "error_message": workflow.error_message,
        "tasks": [
            {
                "task_id": t.task_id,
                "task_name": t.task_name,
                "task_type": t.task_type,
                "status": t.status,
                "depends_on": t.depends_on,
                "output_data": t.output_data,
                "error_message": t.error_message,
                "execution_time_ms": t.execution_time_ms
            }
            for t in tasks
        ],
        "created_at": workflow.created_at,
        "started_at": workflow.started_at,
        "completed_at": workflow.completed_at
    }


@router.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a workflow."""
    service = WorkflowService(db)
    workflow = service.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    service.cancel_workflow(workflow_id)
    
    return {"status": "cancelled"}


# ============================================================================
# Memory Endpoints
# ============================================================================

@router.post("/memory")
async def store_memory(
    key: str,
    value: Any,
    memory_type: str,
    workflow_id: Optional[int] = None,
    task_id: Optional[str] = None,
    scope: str = "workflow",
    db: Session = Depends(get_db),
):
    """Store agent memory."""
    service = MemoryService(db)
    
    memory = service.store(
        key=key,
        value=value,
        memory_type=memory_type,
        workflow_id=workflow_id,
        task_id=task_id,
        scope=scope
    )
    
    return {"id": memory.id, "key": key}


@router.get("/memory")
async def get_memory(
    key: str,
    memory_type: Optional[str] = None,
    workflow_id: Optional[int] = None,
    scope: str = "workflow",
    db: Session = Depends(get_db),
):
    """Get agent memory."""
    service = MemoryService(db)
    
    value = service.get(
        key=key,
        memory_type=memory_type,
        workflow_id=workflow_id,
        scope=scope
    )
    
    if value is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return {"key": key, "value": value}


# ============================================================================
# Metrics Endpoints
# ============================================================================

@router.get("/metrics")
async def get_system_metrics(db: Session = Depends(get_db)):
    """Get overall system metrics."""
    service = MetricsService(db)
    return service.get_system_stats()


@router.get("/metrics/agents/{agent_id}")
async def get_agent_metrics(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """Get metrics for a specific agent."""
    service = AgentManagerService(db)
    service_metrics = MetricsService(db)
    
    agent = service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return service_metrics.get_agent_stats(agent.id)


# ============================================================================
# Execution Endpoints
# ============================================================================

@router.get("/executions")
async def get_recent_executions(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent workflow executions."""
    workflows = db.query(WorkflowExecution).filter(
        WorkflowExecution.user_id == current_user.id
    ).order_by(
        WorkflowExecution.created_at.desc()
    ).limit(limit).all()
    
    return [
        {
            "workflow_id": w.workflow_id,
            "title": w.title,
            "status": w.status,
            "completed_tasks": w.completed_tasks,
            "total_tasks": w.total_tasks,
            "created_at": w.created_at
        }
        for w in workflows
    ]
