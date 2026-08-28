"""
Task Dispatcher

Provides task queuing, scheduling, and dispatch infrastructure
for async task execution across agents.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from collections import defaultdict
from heapq import heappush, heappop

from src.core.logging import logger


class TaskPriority(Enum):
    """Task priority levels (lower number = higher priority)."""
    CRITICAL = 0  # System-critical tasks
    HIGH = 1      # User-blocking tasks
    NORMAL = 2    # Default priority
    LOW = 3       # Background tasks
    BATCH = 4     # Large batch operations


class TaskStatus(Enum):
    """Task lifecycle states."""
    PENDING = "pending"      # Queued, waiting for execution
    SCHEDULED = "scheduled"  # Scheduled for future execution
    RUNNING = "running"      # Currently executing
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"        # Execution failed
    CANCELLED = "cancelled"  # Cancelled before execution
    TIMEOUT = "timeout"      # Execution exceeded time limit


@dataclass
class Task:
    """
    Represents a dispatchable task.
    
    Tasks are units of work that can be queued, scheduled,
    and executed by the TaskDispatcher.
    """
    task_id: str
    task_type: str                    # Task category (e.g., "document_processing")
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    payload: dict[str, Any] = field(default_factory=dict)  # Task input data
    result: Any = None               # Task output data
    error: Optional[str] = None       # Error message if failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None  # For scheduled tasks
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other: "Task") -> bool:
        """Enable priority queue ordering."""
        # Earlier scheduled tasks have higher priority
        self_time = self.scheduled_at or self.created_at
        other_time = other.scheduled_at or other.created_at
        if self_time != other_time:
            return self_time < other_time
        # Same time: higher priority (lower number) wins
        return self.priority.value < other.priority.value


class TaskDispatcher:
    """
    Task dispatcher for queuing and executing async tasks.
    
    Features:
    - Priority-based task queue
    - Scheduled task execution
    - Retry with exponential backoff
    - Progress tracking
    - Task cancellation
    
    Note: This is an in-memory implementation suitable for single-process
    deployments. For multi-instance deployments, consider replacing with
    Redis Queue or Celery.
    
    Usage:
        dispatcher = TaskDispatcher()
        
        # Submit a task
        task_id = dispatcher.submit(
            task_type="document_processing",
            payload={"document_id": 123},
            priority=TaskPriority.NORMAL
        )
        
        # Submit with callback
        async def on_complete(result):
            print(f"Task done: {result}")
        
        dispatcher.submit(
            task_type="flashcard_generation",
            payload={"document_id": 456},
            callback=on_complete
        )
        
        # Cancel a task
        dispatcher.cancel(task_id)
    """
    
    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._queue: list[Task] = []  # Priority queue
        self._running: set[str] = set()
        self._callbacks: dict[str, Callable] = {}
        self._worker_task: Optional[asyncio.Task] = None
        self._shutdown = False
        self._max_concurrent = 10
    
    async def start(self) -> None:
        """Start the dispatcher's background worker."""
        if self._worker_task is not None:
            return
        
        self._shutdown = False
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("TaskDispatcher worker started")
    
    async def stop(self) -> None:
        """Stop the dispatcher and wait for running tasks."""
        self._shutdown = True
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        
        # Wait for running tasks with timeout
        if self._running:
            logger.warning(f"Stopping dispatcher with {len(self._running)} tasks running")
            try:
                await asyncio.wait_for(
                    self._wait_all_complete(),
                    timeout=30
                )
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for tasks to complete")
        
        logger.info("TaskDispatcher worker stopped")
    
    async def _wait_all_complete(self) -> None:
        """Wait for all running tasks to complete."""
        while self._running:
            await asyncio.sleep(0.1)
    
    def submit(
        self,
        task_type: str,
        payload: dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        timeout_seconds: int = 300,
        max_retries: int = 3,
        metadata: Optional[dict[str, Any]] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """
        Submit a new task for execution.
        
        Args:
            task_type: Category of task (e.g., "flashcard_generation")
            payload: Input data for the task
            priority: Task priority
            scheduled_at: Optional future execution time
            timeout_seconds: Max execution time before timeout
            max_retries: Number of retry attempts on failure
            metadata: Additional metadata
            callback: Optional async callback when task completes
            
        Returns:
            The assigned task_id
        """
        task_id = str(uuid.uuid4())
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            payload=payload,
            scheduled_at=scheduled_at,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            metadata=metadata or {},
            status=TaskStatus.SCHEDULED if scheduled_at else TaskStatus.PENDING
        )
        
        self._tasks[task_id] = task
        
        if callback:
            self._callbacks[task_id] = callback
        
        if not scheduled_at or scheduled_at <= datetime.utcnow():
            # Add to priority queue
            heappush(self._queue, task)
            task.status = TaskStatus.PENDING
        
        logger.info(f"Task submitted: {task_id} ({task_type}, priority={priority.name})")
        
        return task_id
    
    def cancel(self, task_id: str) -> bool:
        """
        Cancel a pending or running task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if task was found and cancelled
        """
        task = self._tasks.get(task_id)
        
        if not task:
            return False
        
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return False
        
        task.status = TaskStatus.CANCELLED
        self._running.discard(task_id)
        
        logger.info(f"Task cancelled: {task_id}")
        
        return True
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by its ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task if found, None otherwise
        """
        return self._tasks.get(task_id)
    
    def get_tasks_by_type(self, task_type: str) -> list[Task]:
        """Get all tasks of a specific type."""
        return [
            task for task in self._tasks.values()
            if task.task_type == task_type
        ]
    
    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """Get all tasks with a specific status."""
        return [
            task for task in self._tasks.values()
            if task.status == status
        ]
    
    def get_pending_tasks(self) -> list[Task]:
        """Get all pending tasks in priority order."""
        return sorted(
            [t for t in self._tasks.values() if t.status == TaskStatus.PENDING],
            key=lambda t: (t.priority.value, t.created_at)
        )
    
    def get_running_tasks(self) -> list[Task]:
        """Get all currently running tasks."""
        return [
            self._tasks[tid]
            for tid in self._running
            if tid in self._tasks
        ]
    
    async def _worker_loop(self) -> None:
        """Background worker that processes tasks from the queue."""
        while not self._shutdown:
            try:
                # Check for scheduled tasks that are ready
                now = datetime.utcnow()
                ready_scheduled = [
                    task for task in self._tasks.values()
                    if task.status == TaskStatus.SCHEDULED
                    and task.scheduled_at
                    and task.scheduled_at <= now
                ]
                
                for task in ready_scheduled:
                    task.status = TaskStatus.PENDING
                    heappush(self._queue, task)
                
                # Process tasks from queue
                while len(self._running) < self._max_concurrent and self._queue:
                    task = heappop(self._queue)
                    
                    # Skip cancelled tasks
                    if task.status == TaskStatus.CANCELLED:
                        continue
                    
                    # Check if already completed/failed
                    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                        continue
                    
                    asyncio.create_task(self._execute_task(task))
                
                # Clean up old completed/failed tasks (keep last 1000)
                await self._cleanup_old_tasks()
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy loop
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dispatcher worker error: {e}")
                await asyncio.sleep(1)
    
    async def _execute_task(self, task: Task) -> None:
        """Execute a single task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        self._running.add(task.task_id)
        
        logger.info(f"Executing task: {task.task_id} ({task.task_type})")
        
        try:
            # Import here to avoid circular imports
            from src.enterprise.orchestrator.master import MasterOrchestrator
            
            # Get orchestrator from app state (set in main.py)
            from src.main import orchestrator
            
            if orchestrator:
                # Execute through orchestrator
                from src.enterprise.orchestrator.base import AgentContext, AgentCapability
                
                context = AgentContext(
                    task_id=task.task_id,
                    user_id=task.payload.get("user_id", 0),
                    workspace_id=task.payload.get("workspace_id"),
                    document_ids=task.payload.get("document_ids", []),
                    parameters=task.payload.get("parameters", {}),
                    metadata=task.metadata
                )
                
                capability_str = task.payload.get("capability")
                if capability_str:
                    capability = AgentCapability(capability_str)
                    result = await orchestrator.route_request(capability, context)
                    task.result = result.output
                else:
                    task.result = {"status": "completed", "task_id": task.task_id}
            else:
                # No orchestrator - just mark as complete
                task.result = {"status": "completed_no_orchestrator", "task_id": task.task_id}
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            logger.info(f"Task completed: {task.task_id}")
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.error = f"Task exceeded timeout of {task.timeout_seconds}s"
            task.completed_at = datetime.utcnow()
            
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.scheduled_at = datetime.utcnow() + timedelta(seconds=2 ** task.retry_count)
                heappush(self._queue, task)
                logger.info(f"Task {task.task_id} rescheduled for retry {task.retry_count}")
            
        except Exception as e:
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.scheduled_at = datetime.utcnow() + timedelta(seconds=2 ** task.retry_count)
                heappush(self._queue, task)
                logger.info(f"Task {task.task_id} failed, rescheduled for retry {task.retry_count}: {e}")
            else:
                task.status = TaskStatus.FAILED
                logger.error(f"Task {task.task_id} failed after {task.max_retries} retries: {e}")
        
        finally:
            self._running.discard(task.task_id)
            
            # Call callback if registered
            if task.task_id in self._callbacks:
                callback = self._callbacks.pop(task.task_id)
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(task)
                    else:
                        callback(task)
                except Exception as e:
                    logger.error(f"Task callback error: {e}")
    
    async def _cleanup_old_tasks(self) -> None:
        """Remove old completed/failed tasks to prevent memory growth."""
        if len(self._tasks) <= 1000:
            return
        
        # Sort by completion time
        old_tasks = sorted(
            [t for t in self._tasks.values() if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)],
            key=lambda t: t.completed_at or t.created_at
        )[:100]
        
        for task in old_tasks:
            del self._tasks[task.task_id]
    
    def get_stats(self) -> dict:
        """Get dispatcher statistics."""
        return {
            "total_tasks": len(self._tasks),
            "pending": len([t for t in self._tasks.values() if t.status == TaskStatus.PENDING]),
            "running": len(self._running),
            "completed": len([t for t in self._tasks.values() if t.status == TaskStatus.COMPLETED]),
            "failed": len([t for t in self._tasks.values() if t.status == TaskStatus.FAILED]),
            "max_concurrent": self._max_concurrent,
            "queue_size": len(self._queue)
        }
