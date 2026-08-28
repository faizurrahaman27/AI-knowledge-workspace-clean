"""
Event Bus System

Central event bus for connecting all subsystems.
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Core event types for the autonomous system."""
    # Document events
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_UPDATED = "document.updated"
    DOCUMENT_DELETED = "document.deleted"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_MERGED = "document.merged"
    DOCUMENT_ARCHIVED = "document.archived"
    
    # Knowledge events
    KNOWLEDGE_EXTRACTED = "knowledge.extracted"
    ENTITIES_DISCOVERED = "entities.discovered"
    RELATIONSHIPS_DISCOVERED = "relationships.discovered"
    KNOWLEDGE_VALIDATED = "knowledge.validated"
    KNOWLEDGE_UPDATED = "knowledge.updated"
    
    # Graph events
    GRAPH_UPDATED = "graph.updated"
    NODE_CREATED = "graph.node.created"
    EDGE_CREATED = "graph.edge.created"
    DUPLICATE_DETECTED = "graph.duplicate.detected"
    
    # Notebook events
    NOTEBOOK_CREATED = "notebook.created"
    NOTEBOOK_UPDATED = "notebook.updated"
    NOTEBOOK_GENERATED = "notebook.generated"
    NOTEBOOK_LINKED = "notebook.linked"
    
    # Learning events
    LEARNING_PATH_CREATED = "learning.path.created"
    LEARNING_PATH_UPDATED = "learning.path.updated"
    PROGRESS_UPDATED = "learning.progress.updated"
    MASTERY_ACHIEVED = "learning.mastery.achieved"
    
    # Insight events
    INSIGHT_CREATED = "insight.created"
    INSIGHT_UPDATED = "insight.updated"
    GAP_DETECTED = "insight.gap.detected"
    
    # Memory events
    MEMORY_STORED = "memory.stored"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_CONSOLIDATED = "memory.consolidated"
    
    # Workspace events
    WORKSPACE_IMPORTED = "workspace.imported"
    WORKSPACE_EXPORTED = "workspace.exported"
    WORKSPACE_ANALYZED = "workspace.analyzed"
    WORKSPACE_STATS_UPDATED = "workspace.stats.updated"
    
    # Language events
    LANGUAGE_DETECTED = "language.detected"
    TRANSLATION_COMPLETED = "language.translated"
    
    # Background events
    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    
    # Validation events
    VALIDATION_COMPLETED = "validation.completed"
    VALIDATION_FAILED = "validation.failed"
    
    # Recommendation events
    RECOMMENDATION_GENERATED = "recommendation.generated"
    RECOMMENDATION_ACCEPTED = "recommendation.accepted"
    
    # Collection events
    COLLECTION_CREATED = "collection.created"
    COLLECTION_UPDATED = "collection.updated"
    COLLECTION_MERGED = "collection.merged"


@dataclass
class Event:
    """Core event structure."""
    event_id: str
    event_type: str
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    user_id: Optional[int] = None
    document_id: Optional[int] = None
    workspace_id: Optional[int] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data,
            "user_id": self.user_id,
            "document_id": self.document_id,
            "workspace_id": self.workspace_id,
            "correlation_id": self.correlation_id
        }


class EventBus:
    """
    Central event bus for the autonomous system.
    
    Features:
    - Pub/Sub messaging
    - Event filtering
    - Async event handling
    - Event persistence
    - Dead letter queue
    - Event correlation
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._handlers: Dict[str, Callable] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._processing_tasks: Set[asyncio.Task] = set()
        self._dead_letter_queue: List[Event] = []
        
    def subscribe(self, event_type: str, handler: Callable) -> str:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Event type to subscribe to
            handler: Async callback function
            
        Returns:
            Subscription ID
        """
        subscription_id = str(uuid.uuid4())
        self._subscribers[event_type].append(handler)
        logger.info(f"Subscribed to {event_type} with ID {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, event_type: str, subscription_id: str) -> bool:
        """Unsubscribe from an event type."""
        # Note: In production, track subscription_id per handler
        if event_type in self._subscribers:
            logger.info(f"Unsubscribed from {event_type}")
            return True
        return False
    
    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event: Event to publish
        """
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        logger.info(f"Publishing event: {event.event_type}")
        
        # Get subscribers for this event type
        handlers = self._subscribers.get(event.event_type, [])
        
        # Also notify wildcard subscribers
        handlers.extend(self._subscribers.get("*", []))
        
        # Execute handlers asynchronously
        for handler in handlers:
            task = asyncio.create_task(self._safe_handle(handler, event))
            self._processing_tasks.add(task)
            task.add_done_callback(self._processing_tasks.discard)
    
    async def _safe_handle(self, handler: Callable, event: Event) -> None:
        """Safely handle an event."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.exception(f"Error handling event {event.event_id}: {e}")
            self._dead_letter_queue.append(event)
    
    def register_handler(self, event_type: str, handler: Callable) -> None:
        """Register a handler for an event type."""
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for {event_type}")
    
    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get event history."""
        if event_type:
            return [e for e in self._event_history if e.event_type == event_type][-limit:]
        return self._event_history[-limit:]
    
    def get_dead_letters(self) -> List[Event]:
        """Get events that failed processing."""
        return self._dead_letter_queue.copy()
    
    def clear_dead_letters(self) -> int:
        """Clear dead letter queue and return count."""
        count = len(self._dead_letter_queue)
        self._dead_letter_queue.clear()
        return count


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


class EventPublisher:
    """Helper class for publishing events."""
    
    def __init__(self, source: str = "system"):
        """Initialize publisher."""
        self.source = source
        self.event_bus = get_event_bus()
    
    async def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
        correlation_id: Optional[str] = None
    ) -> Event:
        """Publish an event."""
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.utcnow(),
            source=self.source,
            data=data,
            user_id=user_id,
            document_id=document_id,
            workspace_id=workspace_id,
            correlation_id=correlation_id or str(uuid.uuid4())
        )
        
        await self.event_bus.publish(event)
        return event


# Factory function
def create_publisher(source: str = "system") -> EventPublisher:
    """Create an event publisher."""
    return EventPublisher(source)
