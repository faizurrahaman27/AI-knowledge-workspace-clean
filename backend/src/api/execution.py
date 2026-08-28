"""
Execution API

REST API for the AI Execution Layer.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.execution.schemas import (
    ExecutionRequest,
    ExecutionResponse,
    WorkflowExecutionRequest,
    ExecutionHistory,
    ExecutionHistoryResponse,
    TemplatesResponse,
    ExecutionTemplate,
    SystemStatus,
    ExecutionStatusResponse,
)
from src.execution.services.execution_engine import get_execution_engine
from src.core.logging import logger

router = APIRouter(prefix="/execution", tags=["Execution"])


# ============================================================================
# Action Execution
# ============================================================================

@router.post("/run", response_model=ExecutionResponse)
async def execute_action(
    request: ExecutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a single action.
    
    Executes the specified action and returns the result
    with downloadable output files.
    """
    engine = get_execution_engine(db)
    
    # Set user ID
    request.user_id = current_user.id
    
    try:
        result = await engine.execute_action(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Action execution failed")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Workflow Execution
# ============================================================================

@router.post("/workflow", response_model=ExecutionResponse)
async def execute_workflow(
    request: WorkflowExecutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a multi-step workflow.
    
    Executes a complete workflow with multiple steps
    and returns all outputs as a downloadable bundle.
    """
    engine = get_execution_engine(db)
    
    # Set user ID
    request.user_id = current_user.id
    
    try:
        result = await engine.execute_workflow(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Workflow execution failed")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Execution Status
# ============================================================================

@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get execution status.
    
    Returns the current status of an execution including
    progress, steps, and outputs.
    """
    engine = get_execution_engine(db)
    
    result = engine.get_execution(execution_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return result


# ============================================================================
# Execution Outputs
# ============================================================================

@router.get("/{execution_id}/outputs")
async def get_execution_outputs(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get execution outputs.
    
    Returns download URLs for all output files generated
    by the execution.
    """
    engine = get_execution_engine(db)
    
    outputs = engine.get_execution_outputs(execution_id)
    
    return {
        "execution_id": execution_id,
        "outputs": outputs,
        "count": len(outputs)
    }


@router.get("/{execution_id}/outputs/{filename}")
async def download_output(
    execution_id: str,
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download an output file.
    
    Returns the actual file for download.
    """
    from src.execution.services.output_manager import get_output_manager
    
    manager = get_output_manager()
    filepath = manager.get_file_path(execution_id, filename)
    
    if not manager.file_exists(execution_id, filename):
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = manager.get_file_info(execution_id, filename)
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=file_info["content_type"]
    )


# ============================================================================
# Execution History
# ============================================================================

@router.get("/history", response_model=ExecutionHistoryResponse)
async def get_execution_history(
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get execution history.
    
    Returns the history of executions, optionally filtered
    by user or status.
    """
    engine = get_execution_engine(db)
    
    # Use current user if not specified
    if user_id is None:
        user_id = current_user.id
    
    history = engine.get_execution_history(user_id, limit)
    
    # Filter by status if specified
    if status:
        from src.execution.schemas import ExecutionStatus
        try:
            target_status = ExecutionStatus(status)
            history = [h for h in history if h["status"] == target_status.value]
        except ValueError:
            pass
    
    return ExecutionHistoryResponse(
        executions=[
            ExecutionHistory(**h) for h in history
        ],
        total_count=len(history),
        page=1,
        page_size=limit
    )


# ============================================================================
# Execution Control
# ============================================================================

@router.post("/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel an execution.
    
    Cancels a running or queued execution.
    """
    engine = get_execution_engine(db)
    
    success = engine.cancel_execution(execution_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel execution (not found or already completed)"
        )
    
    return {
        "execution_id": execution_id,
        "cancelled": True
    }


@router.post("/{execution_id}/retry", response_model=ExecutionResponse)
async def retry_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retry a failed execution.
    
    Creates and executes a new execution with the same
    parameters as the failed one.
    """
    engine = get_execution_engine(db)
    
    result = engine.retry_execution(execution_id)
    
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Cannot retry execution (not found or not failed)"
        )
    
    return result


# ============================================================================
# Templates
# ============================================================================

@router.get("/templates", response_model=TemplatesResponse)
async def get_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get available execution templates.
    
    Returns all workflow templates that can be executed.
    """
    engine = get_execution_engine(db)
    
    templates = engine.get_templates()
    
    return TemplatesResponse(
        templates=[ExecutionTemplate(**t) for t in templates],
        total_count=len(templates)
    )


# ============================================================================
# Status
# ============================================================================

@router.get("/status", response_model=ExecutionStatusResponse)
async def get_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get execution system status.
    
    Returns statistics about executions, registered actions,
    and output storage.
    """
    engine = get_execution_engine(db)
    
    status = engine.get_system_status()
    
    return ExecutionStatusResponse(
        status=SystemStatus(**status["execution"])
    )


# ============================================================================
# Cleanup
# ============================================================================

@router.post("/cleanup")
async def cleanup_old_outputs(
    max_age_hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Clean up old output files.
    
    Removes execution outputs older than the specified age.
    """
    engine = get_execution_engine(db)
    
    count = engine.cleanup_old_outputs(max_age_hours)
    
    return {
        "cleaned_up": count,
        "message": f"Cleaned up {count} old executions"
    }
