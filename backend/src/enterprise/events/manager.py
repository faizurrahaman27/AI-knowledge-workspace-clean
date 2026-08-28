"""
Enterprise Event Manager

Extended event system for WebSocket real-time communication.
Supports workflow states, progress tracking, and multi-client updates.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Callable, Awaitable
from collections import defaultdict

from src.core.logging import logger


class EventType(Enum):
    """
    Comprehensive event types for all application states.
    
    Organized by category:
    - Workflow: Multi-step workflow events
    - Agent: Individual agent lifecycle events
    - Task: Task queue events
    - Document: Document processing events
    - RAG: Retrieval and generation events
    - Collaboration: Real-time collaboration events
    - System: System-level events
    """
    # Workflow events
    WORKFLOW_STARTED = "workflow:started"
    WORKFLOW_STEP_STARTED = "workflow:step:started"
    WORKFLOW_STEP_COMPLETED = "workflow:step:completed"
    WORKFLOW_COMPLETED = "workflow:completed"
    WORKFLOW_FAILED = "workflow:failed"
    WORKFLOW_PROGRESS = "workflow:progress"
    WORKFLOW_CANCELLED = "workflow:cancelled"
    
    # Agent events
    AGENT_STARTED = "agent:started"
    AGENT_COMPLETED = "agent:completed"
    AGENT_ERROR = "agent:error"
    AGENT_PROGRESS = "agent:progress"
    
    # Task events
    TASK_QUEUED = "task:queued"
    TASK_STARTED = "task:started"
    TASK_PROGRESS = "task:progress"
    TASK_COMPLETED = "task:completed"
    TASK_FAILED = "task:failed"
    TASK_CANCELLED = "task:cancelled"
    
    # Document events
    DOCUMENT_UPLOADED = "document:uploaded"
    DOCUMENT_PROCESSING = "document:processing"
    DOCUMENT_PROCESSED = "document:processed"
    DOCUMENT_INDEXED = "document:indexed"
    DOCUMENT_DELETED = "document:deleted"
    
    # RAG events
    RAG_QUERY_STARTED = "rag:query:started"
    RAG_RETRIEVAL = "rag:retrieval"
    RAG_RERANKING = "rag:reranking"
    RAG_GENERATION = "rag:generation"
    RAG_COMPLETED = "rag:completed"
    
    # Study tool events
    FLASHCARD_GENERATED = "study:flashcard:generated"
    QUIZ_GENERATED = "study:quiz:generated"
    MINDMAP_GENERATED = "study:mindmap:generated"
    STUDY_PACK_READY = "study:pack:ready"
    
    # Collaboration events (extends existing WebSocket events)
    USER_JOINED = "collab:user:joined"
    USER_LEFT = "collab:user:left"
    PRESENCE_UPDATE = "collab:presence"
    CHAT_MESSAGE = "collab:chat:message"
    ANNOTATION_CREATED = "collab:annotation:created"
    
    # Research events
    RESEARCH_STARTED = "research:started"
    RESEARCH_PROGRESS = "research:progress"
    RESEARCH_COMPLETED = "research:completed"
    SOURCES_FOUND = "research:sources:found"
    
    # Job hunting events
    JOB_SEARCH_STARTED = "jobs:search:started"
    JOB_MATCH_FOUND = "jobs:match:found"
    JOB_SEARCH_COMPLETED = "jobs:search:completed"
    
    # Exam events
    EXAM_GENERATED = "exam:generated"
    EXAM_SUBMITTED = "exam:submitted"
    EXAM_GRADED = "exam:graded"
    
    # Video events
    VIDEO_PROCESSING = "video:processing"
    VIDEO_TRANSCRIBED = "video:transcribed"
    VIDEO_SUMMARIZED = "video:summarized"
    
    # Math events
    MATH_PROBLEM_SOLVING = "math:solving"
    MATH_STEP_EXPLAINED = "math:step:explained"
    
    # System events
    SYSTEM_STATUS = "system:status"
    SYSTEM_ERROR = "system:error"
    SYSTEM_WARNING = "system:warning"
    HEALTH_CHECK = "health:check"


@dataclass
class WorkflowEvent:
    """
    Standardized event structure for all enterprise events.
    
    All events follow this structure for consistency and easy parsing.
    """
    event_type: EventType
    workflow_id: str = ""                    # Associated workflow (if any)
    task_id: str = ""                        # Associated task (if any)
    agent_id: str = ""                        # Associated agent (if any)
    user_id: int = 0                         # Associated user
    workspace_id: Optional[int] = None        # Associated workspace
    data: dict[str, Any] = field(default_factory=dict)  # Event-specific data
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> dict:
        """Convert event to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "type": self.event_type.value,
            "workflow_id": self.workflow_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowEvent":
        """Create event from dictionary."""
        return cls(
            event_type=EventType(data["type"]),
            workflow_id=data.get("workflow_id", ""),
            task_id=data.get("task_id", ""),
            agent_id=data.get("agent_id", ""),
            user_id=data.get("user_id", 0),
            workspace_id=data.get("workspace_id"),
            data=data.get("data", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            event_id=data.get("event_id", str(uuid.uuid4()))
        )


class EventFilter:
    """Filter for subscribing to specific events."""
    
    def __init__(
        self,
        user_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
        event_types: Optional[list[EventType]] = None,
        workflow_ids: Optional[list[str]] = None
    ):
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.event_types = set(event_types) if event_types else None
        self.workflow_ids = set(workflow_ids) if workflow_ids else None
    
    def matches(self, event: WorkflowEvent) -> bool:
        """Check if an event matches this filter."""
        # Check user
        if self.user_id and event.user_id != self.user_id:
            return False
        
        # Check workspace
        if self.workspace_id and event.workspace_id != self.workspace_id:
            return False
        
        # Check event types
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        # Check workflow IDs
        if self.workflow_ids and event.workflow_id not in self.workflow_ids:
            return False
        
        return True


class EnterpriseEventManager:
    """
    Central event manager for enterprise WebSocket events.
    
    Features:
    - Event broadcasting to WebSocket clients
    - Event filtering and subscription
    - Event history (for replay)
    - Integration with existing WS manager
    
    Usage:
        event_manager = EnterpriseEventManager()
        
        # Subscribe to events
        event_manager.subscribe(
            user_id=123,
            filter=EventFilter(event_types=[EventType.RAG_COMPLETED])
        )
        
        # Emit an event
        await event_manager.emit(WorkflowEvent(
            event_type=EventType.WORKFLOW_STARTED,
            user_id=123,
            data={"workflow_id": "abc"}
        ))
    """
    
    def __init__(self):
        # user_id -> list of EventFilters
        self._subscriptions: dict[int, list[EventFilter]] = defaultdict(list)
        # user_id -> asyncio.Queue for new events
        self._queues: dict[int, asyncio.Queue] = {}
        # Recent events for history (last 1000)
        self._event_history: list[WorkflowEvent] = []
        self._max_history = 1000
        # External WebSocket manager integration
        self._ws_manager = None
    
    def set_ws_manager(self, ws_manager) -> None:
        """
        Set the WebSocket connection manager for broadcasting.
        
        Args:
            ws_manager: The WorkspaceConnectionManager instance
        """
        self._ws_manager = ws_manager
    
    def subscribe(
        self,
        user_id: int,
        filter: Optional[EventFilter] = None,
        queue: Optional[asyncio.Queue] = None
    ) -> str:
        """
        Subscribe a user to receive events.
        
        Args:
            user_id: The user ID to subscribe
            filter: Optional filter for specific events
            queue: Optional asyncio.Queue to receive events
            
        Returns:
            Subscription ID
        """
        if filter is None:
            filter = EventFilter(user_id=user_id)
        else:
            # Ensure user_id matches
            filter = EventFilter(
                user_id=user_id,
                workspace_id=filter.workspace_id,
                event_types=list(filter.event_types) if filter.event_types else None,
                workflow_ids=list(filter.workflow_ids) if filter.workflow_ids else None
            )
        
        self._subscriptions[user_id].append(filter)
        
        if queue:
            self._queues[user_id] = queue
        
        sub_id = str(uuid.uuid4())
        logger.debug(f"User {user_id} subscribed to events (filter: {[f.event_types for f in self._subscriptions[user_id]]})")
        
        return sub_id
    
    def unsubscribe(self, user_id: int, filter: Optional[EventFilter] = None) -> None:
        """
        Unsubscribe a user from events.
        
        Args:
            user_id: The user ID to unsubscribe
            filter: Optional specific filter to remove (removes all if None)
        """
        if filter is None:
            self._subscriptions.pop(user_id, None)
            self._queues.pop(user_id, None)
        else:
            subs = self._subscriptions.get(user_id, [])
            if filter in subs:
                subs.remove(filter)
        logger.debug(f"User {user_id} unsubscribed from events")
    
    async def emit(self, event: WorkflowEvent) -> None:
        """
        Emit an event to all matching subscribers.
        
        Args:
            event: The event to emit
        """
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Find matching subscriptions
        matching_users = set()
        
        for user_id, filters in self._subscriptions.items():
            # Check user ID match first (fast path)
            if any(f.user_id == event.user_id for f in filters):
                matching_users.add(user_id)
            elif any(f.user_id is None for f in filters):
                # Global subscription for this user
                matching_users.add(user_id)
        
        # Deliver to matching users
        for user_id in matching_users:
            # Check detailed filters
            for filter_obj in self._subscriptions[user_id]:
                if filter_obj.matches(event):
                    # Deliver to user's queue if they have one
                    if user_id in self._queues:
                        try:
                            await asyncio.wait_for(
                                self._queues[user_id].put(event),
                                timeout=1
                            )
                        except asyncio.TimeoutError:
                            logger.warning(f"Event queue full for user {user_id}")
                    
                    # Also broadcast via WebSocket if workspace-scoped
                    if event.workspace_id and self._ws_manager:
                        try:
                            await self._ws_manager.broadcast(event.workspace_id, event.to_dict())
                        except Exception as e:
                            logger.error(f"Failed to broadcast event to workspace {event.workspace_id}: {e}")
                    
                    break  # Only deliver once per user
        
        logger.debug(f"Emitted event: {event.event_type.value} (workflow={event.workflow_id}, matches={len(matching_users)})")
    
    def get_event_history(
        self,
        user_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
        event_types: Optional[list[EventType]] = None,
        limit: int = 100
    ) -> list[WorkflowEvent]:
        """
        Get recent events from history.
        
        Args:
            user_id: Filter by user
            workspace_id: Filter by workspace
            event_types: Filter by event types
            limit: Maximum events to return
            
        Returns:
            List of matching events
        """
        events = self._event_history
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if workspace_id:
            events = [e for e in events if e.workspace_id == workspace_id]
        
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        
        return events[-limit:]
    
    def create_progress_event(
        self,
        event_type: EventType,
        workflow_id: str,
        user_id: int,
        progress_percent: float,
        message: str,
        **kwargs
    ) -> WorkflowEvent:
        """
        Create a standardized progress event.
        
        Args:
            event_type: Event type (should be a progress variant)
            workflow_id: Associated workflow
            user_id: User ID
            progress_percent: 0-100 progress value
            message: Human-readable progress message
            **kwargs: Additional data
            
        Returns:
            WorkflowEvent with progress data
        """
        return WorkflowEvent(
            event_type=event_type,
            workflow_id=workflow_id,
            user_id=user_id,
            data={
                "progress": min(100, max(0, progress_percent)),
                "message": message,
                **kwargs
            }
        )
    
    def create_error_event(
        self,
        workflow_id: str,
        user_id: int,
        error: str,
        recoverable: bool = True,
        **kwargs
    ) -> WorkflowEvent:
        """
        Create a standardized error event.
        
        Args:
            workflow_id: Associated workflow
            user_id: User ID
            error: Error message
            recoverable: Whether the error can be retried
            **kwargs: Additional data
            
        Returns:
            WorkflowEvent with error data
        """
        return WorkflowEvent(
            event_type=EventType.WORKFLOW_FAILED,
            workflow_id=workflow_id,
            user_id=user_id,
            data={
                "error": error,
                "recoverable": recoverable,
                **kwargs
            }
        )
    
    def get_stats(self) -> dict:
        """Get event manager statistics."""
        return {
            "total_subscriptions": sum(len(s) for s in self._subscriptions.values()),
            "active_users": len(self._subscriptions),
            "event_history_size": len(self._event_history),
            "max_history": self._max_history
        }
