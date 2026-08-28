"""
Orchestration API

REST API for the enterprise agent orchestration system.
Exposes agent discovery, workflow execution, and task management.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Any
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.enterprise.orchestrator.base import AgentCapability, AgentContext
from src.enterprise.orchestrator.master import MasterOrchestrator
from src.enterprise.workflows.engine import WorkflowEngine
from src.enterprise.dispatcher.task_dispatcher import TaskPriority
from src.core.logging import logger

router = APIRouter(prefix="/orchestration", tags=["Orchestration"])


# === Request/Response Schemas ===

class TaskSubmitRequest(BaseModel):
    """Submit a task for execution."""
    task_type: str
    capability: str  # AgentCapability value
    payload: dict
    priority: str = "NORMAL"  # CRITICAL, HIGH, NORMAL, LOW, BATCH
    workspace_id: Optional[int] = None
    document_ids: Optional[List[int]] = None


class TaskSubmitResponse(BaseModel):
    """Response for task submission."""
    task_id: str
    status: str
    message: str


class WorkflowExecuteRequest(BaseModel):
    """Execute a workflow."""
    workflow_id: str
    workspace_id: Optional[int] = None
    document_ids: Optional[List[int]] = None
    parameters: Optional[dict] = None


class WorkflowExecuteResponse(BaseModel):
    """Response for workflow execution."""
    workflow_id: str
    execution_id: str
    status: str
    message: str


class AgentInfo(BaseModel):
    """Agent information."""
    agent_id: str
    name: str
    description: str
    capabilities: List[str]
    status: str
    available: bool


class SystemStatus(BaseModel):
    """System status overview."""
    initialized: bool
    total_agents: int
    ready_agents: int
    busy_agents: int
    error_agents: int
    capabilities: dict


# === Routes ===

@router.get("/agents", response_model=List[AgentInfo])
async def list_agents():
    """
    List all registered agents.
    
    Returns agent metadata including capabilities and status.
    """
    try:
        from src.main import orchestrator
        if not orchestrator:
            return []
        
        agents = orchestrator.registry.get_all_agents()
        return [
            AgentInfo(
                agent_id=a.metadata.agent_id,
                name=a.metadata.name,
                description=a.metadata.description,
                capabilities=[c.value for c in a.metadata.capabilities],
                status=a.status.value,
                available=a.is_available
            )
            for a in agents
        ]
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return []


@router.get("/agents/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str):
    """
    Get details for a specific agent.
    """
    try:
        from src.main import orchestrator
        if not orchestrator:
            raise HTTPException(status_code=404, detail="Orchestrator not initialized")
        
        agent = orchestrator.registry.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        return AgentInfo(
            agent_id=agent.metadata.agent_id,
            name=agent.metadata.name,
            description=agent.metadata.description,
            capabilities=[c.value for c in agent.metadata.capabilities],
            status=agent.status.value,
            available=agent.is_available
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capabilities")
async def list_capabilities():
    """
    List all available agent capabilities.
    
    Returns capabilities grouped by category.
    """
    capabilities = {}
    
    for cap in AgentCapability:
        value = cap.value
        category = value.split("_")[0] if "_" in value else "other"
        
        if category not in capabilities:
            capabilities[category] = []
        
        capabilities[category].append({
            "value": value,
            "name": value.replace("_", " ").title()
        })
    
    return {"capabilities": capabilities}


@router.post("/task/submit", response_model=TaskSubmitResponse)
async def submit_task(
    request: TaskSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a task for agent execution.
    
    The task is queued and executed by an appropriate agent
    based on the specified capability.
    """
    try:
        from src.main import orchestrator, task_dispatcher
        
        if not orchestrator or not task_dispatcher:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        # Get priority
        try:
            priority = TaskPriority[request.priority]
        except KeyError:
            priority = TaskPriority.NORMAL
        
        # Submit to dispatcher
        task_id = task_dispatcher.submit(
            task_type=request.task_type,
            payload={
                "user_id": current_user.id,
                "workspace_id": request.workspace_id,
                "document_ids": request.document_ids or [],
                "capability": request.capability,
                "parameters": request.payload
            },
            priority=priority
        )
        
        return TaskSubmitResponse(
            task_id=task_id,
            status="queued",
            message=f"Task queued for execution by {request.capability} agent"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get the status of a submitted task.
    """
    try:
        from src.main import task_dispatcher
        
        if not task_dispatcher:
            raise HTTPException(status_code=503, detail="Dispatcher not initialized")
        
        task = task_dispatcher.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": task.status.value,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": task.result,
            "error": task.error,
            "retry_count": task.retry_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/task/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a pending or running task.
    """
    try:
        from src.main import task_dispatcher
        
        if not task_dispatcher:
            raise HTTPException(status_code=503, detail="Dispatcher not initialized")
        
        if task_dispatcher.cancel(task_id):
            return {"message": f"Task {task_id} cancelled"}
        else:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found or already completed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows")
async def list_workflows():
    """
    List all available workflow templates.
    """
    try:
        from src.main import workflow_engine
        
        if not workflow_engine:
            return {"workflows": []}
        
        return {"workflows": workflow_engine.get_available_workflows()}
        
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        return {"workflows": []}


@router.post("/workflow/execute", response_model=WorkflowExecuteResponse)
async def execute_workflow(
    request: WorkflowExecuteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a workflow with the given parameters.
    
    Workflows run as background tasks and progress can be
    tracked via WebSocket events.
    """
    try:
        from src.main import orchestrator, workflow_engine
        
        if not orchestrator or not workflow_engine:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        workflow = workflow_engine.get_workflow(request.workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow {request.workflow_id} not found")
        
        execution_id = f"exec_{len(orchestrator._active_workflows) + 1}"
        
        # Create context
        context = AgentContext(
            task_id=execution_id,
            user_id=current_user.id,
            workspace_id=request.workspace_id,
            document_ids=request.document_ids or [],
            parameters=request.parameters or {},
            metadata={"workflow_id": request.workflow_id}
        )
        
        # Store workflow info
        orchestrator._active_workflows[execution_id] = {
            "workflow_id": request.workflow_id,
            "user_id": current_user.id,
            "status": "running"
        }
        
        # Execute in background
        async def run_workflow():
            try:
                await workflow_engine.execute(workflow, orchestrator, context)
                orchestrator._active_workflows[execution_id]["status"] = "completed"
            except Exception as e:
                logger.error(f"Workflow execution error: {e}")
                orchestrator._active_workflows[execution_id]["status"] = "failed"
        
        background_tasks.add_task(run_workflow)
        
        return WorkflowExecuteResponse(
            workflow_id=request.workflow_id,
            execution_id=execution_id,
            status="started",
            message="Workflow execution started"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow/{execution_id}/status")
async def get_workflow_status(
    execution_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get the status of a workflow execution.
    """
    try:
        from src.main import orchestrator
        
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        if execution_id not in orchestrator._active_workflows:
            raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
        
        return orchestrator._active_workflows[execution_id]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """
    Get overall system status.
    
    Returns agent counts, capabilities, and health indicators.
    """
    try:
        from src.main import orchestrator, task_dispatcher
        
        if not orchestrator:
            return SystemStatus(
                initialized=False,
                total_agents=0,
                ready_agents=0,
                busy_agents=0,
                error_agents=0,
                capabilities={}
            )
        
        status = orchestrator.get_system_status()
        
        return SystemStatus(
            initialized=status["initialized"],
            total_agents=status["total_agents"],
            ready_agents=status["ready_agents"],
            busy_agents=status["busy_agents"],
            error_agents=status["error_agents"],
            capabilities=status["capabilities"]
        )
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
