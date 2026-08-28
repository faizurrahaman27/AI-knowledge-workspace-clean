"""
Master Orchestrator

Central orchestrator for multi-agent workflow execution.
"""

import uuid
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from src.multi_agent.models import (
    WorkflowExecution,
    TaskExecution,
    AgentEvent,
    WorkflowStatus,
    TaskStatus,
)
from src.multi_agent.registry.registry import (
    AgentRegistry,
    get_agent_registry,
    AgentMetadata,
)
from src.core.logging import logger


@dataclass
class WorkflowGoal:
    """User goal for workflow."""

    goal: str
    user_id: int

    context: Optional[Dict[str, Any]] = None
    capabilities_needed: List[str] = field(default_factory=list)


@dataclass
class TaskDefinition:
    """Task definition for workflow."""
    task_id: str
    task_name: str
    task_type: str
    capabilities: List[str]
    depends_on: List[str] = field(default_factory=list)
    input_data: Dict[str, Any] = field(default_factory=dict)
    is_parallel: bool = True
    priority: int = 5
    fallback_capabilities: List[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Result of workflow execution."""
    success: bool
    workflow_id: str
    final_result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    task_results: Dict[str, Any]
    execution_time_ms: int


class MasterOrchestrator:
    """
    Master orchestrator for multi-agent execution.
    
    Responsibilities:
    - Understand user goals
    - Plan workflow (DAG)
    - Select agents based on capabilities
    - Execute tasks (parallel + sequential)
    - Handle failures and retries
    - Aggregate results
    - Broadcast workflow state
    """
    
    def __init__(
        self,
        db: Session,
        registry: Optional[AgentRegistry] = None,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize the master orchestrator.
        
        Args:
            db: Database session
            registry: Agent registry (uses global if not provided)
            progress_callback: Callback for progress updates
        """
        self.db = db
        self.registry = registry or get_agent_registry()
        self.progress_callback = progress_callback
    
    async def execute_workflow(
        self,
        goal: WorkflowGoal
    ) -> ExecutionResult:
        """
        Execute a complete workflow from goal.
        
        Args:
            goal: User goal
            
        Returns:
            ExecutionResult with workflow results
        """
        start_time = datetime.utcnow()
        workflow_id = str(uuid.uuid4())
        
        logger.info(f"Starting workflow {workflow_id}: {goal.goal}")
        self._emit_progress("planning", 0.0, "Planning workflow...")
        
        try:
            # 1. Plan the workflow
            tasks = self._plan_workflow(goal)
            
            # 2. Create workflow execution record
            workflow = self._create_workflow_execution(workflow_id, goal, tasks)
            
            # 3. Execute the DAG
            self._emit_progress("executing", 0.1, f"Executing {len(tasks)} tasks...")
            
            results = await self._execute_dag(workflow, tasks)
            
            # 4. Aggregate results
            final_result = self._aggregate_results(results)
            
            # 5. Complete workflow
            workflow.status = WorkflowStatus.COMPLETED.value
            workflow.completed_at = datetime.utcnow()
            workflow.total_tasks = len(tasks)
            workflow.completed_tasks = sum(1 for r in results.values() if r.get("status") == "completed")
            workflow.final_result = final_result
            self.db.commit()
            
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            logger.info(f"Workflow {workflow_id} completed in {execution_time}ms")
            self._emit_progress("completed", 1.0, "Workflow completed")
            
            return ExecutionResult(
                success=True,
                workflow_id=workflow_id,
                final_result=final_result,
                error_message=None,
                task_results=results,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.exception(f"Workflow {workflow_id} failed")
            
            # Update workflow as failed
            workflow = self.db.query(WorkflowExecution).filter(
                WorkflowExecution.workflow_id == workflow_id
            ).first()
            
            if workflow:
                workflow.status = WorkflowStatus.FAILED.value
                workflow.error_message = str(e)
                workflow.completed_at = datetime.utcnow()
                self.db.commit()
            
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return ExecutionResult(
                success=False,
                workflow_id=workflow_id,
                final_result=None,
                error_message=str(e),
                task_results={},
                execution_time_ms=execution_time
            )
    
    def _plan_workflow(self, goal: WorkflowGoal) -> List[TaskDefinition]:
        """
        Plan workflow from goal.
        
        Uses LLM or template to decompose goal into tasks.
        """
        # Template-based planning (simple)
        tasks = []
        
        # Analyze goal for needed capabilities
        goal_lower = goal.goal.lower()
        capabilities_needed = set(goal.capabilities_needed or [])
        
        # Auto-detect capabilities from goal
        if any(word in goal_lower for word in ["research", "study", "learn", "understand", "explain"]):
            capabilities_needed.add("research")
        
        if any(word in goal_lower for word in ["math", "calculate", "equation", "formula", "derive", "prove"]):
            capabilities_needed.add("math")
        
        if any(word in goal_lower for word in ["notebook", "note", "write", "document", "summarize"]):
            capabilities_needed.add("notebook")
        
        if any(word in goal_lower for word in ["search", "find", "web", "github"]):
            capabilities_needed.add("web_search")
        
        if any(word in goal_lower for word in ["flashcard", "quiz", "test", "exam"]):
            capabilities_needed.add("flashcard_generation")
        
        # Create tasks based on capabilities
        task_id = str(uuid.uuid4())[:8]
        
        if "research" in capabilities_needed:
            tasks.append(TaskDefinition(
                task_id=f"research_{task_id}",
                task_name="Research Task",
                task_type="research",
                capabilities=["research"],
                input_data={"goal": goal.goal, "context": goal.context},
                priority=1
            ))
        
        if "math" in capabilities_needed:
            math_task_id = f"math_{task_id}"
            tasks.append(TaskDefinition(
                task_id=math_task_id,
                task_name="Math Analysis",
                task_type="math",
                capabilities=["math"],
                depends_on=[f"research_{task_id}"] if "research" in capabilities_needed else [],
                input_data={"goal": goal.goal, "context": goal.context},
                priority=2
            ))
        
        if "notebook" in capabilities_needed:
            tasks.append(TaskDefinition(
                task_id=f"notebook_{task_id}",
                task_name="Notebook Creation",
                task_type="notebook",
                capabilities=["notebook"],
                depends_on=[f"research_{task_id}", f"math_{task_id}"] if len(tasks) > 1 else [],
                input_data={"goal": goal.goal},
                priority=3
            ))
        
        # Default task if no specific capabilities detected
        if not tasks:
            tasks.append(TaskDefinition(
                task_id=f"general_{task_id}",
                task_name="General Task",
                task_type="general",
                capabilities=["research", "notebook"],
                input_data={"goal": goal.goal, "context": goal.context},
                priority=1
            ))
        
        return tasks
    
    def _create_workflow_execution(
        self,
        workflow_id: str,
        goal: WorkflowGoal,
        tasks: List[TaskDefinition]
    ) -> WorkflowExecution:
        """Create workflow execution record."""
        # Build execution plan (DAG)
        execution_plan = {
            "tasks": [
                {
                    "task_id": t.task_id,
                    "task_name": t.task_name,
                    "depends_on": t.depends_on,
                    "capabilities": t.capabilities,
                    "is_parallel": t.is_parallel
                }
                for t in tasks
            ]
        }
        
        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            title=goal.goal[:100],
            user_id=goal.user_id,
            goal=goal.goal,
            context=goal.context,
            execution_plan=execution_plan,
            status=WorkflowStatus.RUNNING.value,
            total_tasks=len(tasks),
            started_at=datetime.utcnow()
        )
        
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        
        # Create task executions
        for i, task_def in enumerate(tasks):
            task_exec = TaskExecution(
                workflow_id=workflow.id,
                task_id=task_def.task_id,
                task_name=task_def.task_name,
                task_type=task_def.task_type,
                depends_on=task_def.depends_on,
                input_data=task_def.input_data,
                is_parallel=task_def.is_parallel,
                status=TaskStatus.PENDING.value,
                execution_order=i,
                max_retries=3,
                created_at=datetime.utcnow()
            )
            self.db.add(task_exec)
        
        self.db.commit()
        
        return workflow
    
    async def _execute_dag(
        self,
        workflow: WorkflowExecution,
        tasks: List[TaskDefinition]
    ) -> Dict[str, Any]:
        """Execute tasks in DAG order."""
        results = {}
        completed_tasks = set()
        
        # Get task executions from database
        task_execs = {
            te.task_id: te for te in 
            self.db.query(TaskExecution).filter(
                TaskExecution.workflow_id == workflow.id
            ).all()
        }
        
        while len(completed_tasks) < len(tasks):
            # Find tasks ready to execute
            ready_tasks = [
                t for t in tasks
                if t.task_id not in completed_tasks
                and all(dep in completed_tasks for dep in t.depends_on)
            ]
            
            if not ready_tasks:
                # Deadlock or all completed
                break
            
            # Execute ready tasks (parallel if possible)
            batch = [t for t in ready_tasks if t.is_parallel] if ready_tasks else [ready_tasks[0]]
            
            for task_def in batch:
                result = await self._execute_task(
                    workflow.id,
                    task_def,
                    task_execs[task_def.task_id],
                    results
                )
                results[task_def.task_id] = result
                completed_tasks.add(task_def.task_id)
                
                progress = len(completed_tasks) / len(tasks)
                self._emit_progress("executing", progress, f"Task {task_def.task_name} completed")
        
        return results
    
    async def _execute_task(
        self,
        workflow_id: int,
        task_def: TaskDefinition,
        task_exec: TaskExecution,
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single task."""
        # Find best agent
        agent = self.registry.find_best(task_def.capabilities)
        
        if not agent:
            # Try fallback capabilities
            for cap in task_def.fallback_capabilities:
                agent = self.registry.find_best([cap])
                if agent:
                    break
        
        if not agent:
            return {
                "status": "failed",
                "error": f"No agent available for capabilities: {task_def.capabilities}"
            }
        
        # Update task status
        task_exec.agent_id = agent.id
        task_exec.status = TaskStatus.RUNNING.value
        task_exec.started_at = datetime.utcnow()
        self.db.commit()
        
        # Log event
        self._log_event(workflow_id, task_def.task_id, "AgentInvoked", {
            "agent_id": agent.agent_id,
            "agent_name": agent.name
        })
        
        self._emit_progress(
            task_def.task_type,
            0.0,
            f"{agent.name} executing..."
        )
        
        try:
            # Execute with agent (simulated)
            result = await self._call_agent(agent, task_def, previous_results)
            
            # Update task as completed
            task_exec.status = TaskStatus.COMPLETED.value
            task_exec.output_data = result
            task_exec.completed_at = datetime.utcnow()
            task_exec.execution_time_ms = int(
                (task_exec.completed_at - task_exec.started_at).total_seconds() * 1000
            )
            self.db.commit()
            
            # Log event
            self._log_event(workflow_id, task_def.task_id, "TaskCompleted", {
                "agent_id": agent.agent_id
            })
            
            return {
                "status": "completed",
                "result": result,
                "agent_id": agent.agent_id,
                "execution_time_ms": task_exec.execution_time_ms
            }
            
        except Exception as e:
            logger.exception(f"Task {task_def.task_id} failed")
            
            # Handle retry
            if task_exec.retry_count < task_exec.max_retries:
                task_exec.retry_count += 1
                task_exec.status = TaskStatus.PENDING.value
                self.db.commit()
                return await self._execute_task(
                    workflow_id, task_def, task_exec, previous_results
                )
            
            # Mark as failed
            task_exec.status = TaskStatus.FAILED.value
            task_exec.error_message = str(e)
            task_exec.completed_at = datetime.utcnow()
            self.db.commit()
            
            return {
                "status": "failed",
                "error": str(e),
                "agent_id": agent.agent_id,
                "retries": task_exec.retry_count
            }
    
    async def _call_agent(
        self,
        agent: AgentMetadata,
        task: TaskDefinition,
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call an agent to execute a task."""
        # This would integrate with actual agent implementations
        # For now, return simulated result
        
        return {
            "task_type": task.task_type,
            "agent": agent.name,
            "result": f"Executed {task.task_name}",
            "summary": f"Completed {task.task_type} analysis"
        }
    
    def _aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate task results into final workflow result."""
        completed = [r for r in results.values() if r.get("status") == "completed"]
        failed = [r for r in results.values() if r.get("status") == "failed"]
        
        return {
            "total_tasks": len(results),
            "completed_tasks": len(completed),
            "failed_tasks": len(failed),
            "task_results": results,
            "success": len(failed) == 0
        }
    
    def _log_event(
        self,
        workflow_id: int,
        task_id: str,
        event_type: str,
        data: Optional[Dict] = None
    ) -> None:
        """Log an agent event."""
        event = AgentEvent(
            workflow_id=workflow_id,
            task_id=task_id,
            event_type=event_type,
            data=data,
            actor_type="system"
        )
        self.db.add(event)
        self.db.commit()
    
    def _emit_progress(
        self,
        stage: str,
        progress: float,
        message: str
    ) -> None:
        """Emit progress update."""
        if self.progress_callback:
            self.progress_callback(stage, progress, message)
        
        logger.info(f"[Orchestrator] {stage}: {message} ({progress:.0%})")
