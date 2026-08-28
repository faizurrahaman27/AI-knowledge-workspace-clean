"""
Real-time Event Emitter

Production-grade event system that integrates with WebSocket manager
for real-time streaming to all connected clients.

Features:
- Async event emission
- Event buffering for high-frequency events
- Event batching for efficiency
- Automatic reconnection support
- Multiple event type support
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from src.core.logging import logger


class EventType(str, Enum):
    """Comprehensive event types for all system operations."""
    # Document events
    DOCUMENT_UPLOAD_STARTED = "document:upload:started"
    DOCUMENT_UPLOAD_COMPLETED = "document:upload:completed"
    DOCUMENT_PIPELINE_STARTED = "pipeline:start"
    
    # Pipeline stages
    OCR_STARTED = "ocr:started"
    OCR_COMPLETED = "ocr:completed"
    CLEANING_STARTED = "cleaning:started"
    CLEANING_COMPLETED = "cleaning:completed"
    LANGUAGE_DETECTION_STARTED = "language:detection:started"
    LANGUAGE_DETECTION_COMPLETED = "language:detection:completed"
    LAYOUT_DETECTION_STARTED = "layout:detection:started"
    LAYOUT_DETECTION_COMPLETED = "layout:detection:completed"
    CHUNKING_STARTED = "chunking:started"
    CHUNKING_COMPLETED = "chunking:completed"
    EMBEDDING_STARTED = "embedding:started"
    EMBEDDING_COMPLETED = "embedding:completed"
    ENTITY_EXTRACTION_STARTED = "entity:extraction:started"
    ENTITY_EXTRACTION_COMPLETED = "entity:extraction:completed"
    RELATIONSHIP_EXTRACTION_STARTED = "relationship:extraction:started"
    RELATIONSHIP_EXTRACTION_COMPLETED = "relationship:extraction:completed"
    KNOWLEDGE_GRAPH_STARTED = "knowledge:graph:started"
    KNOWLEDGE_GRAPH_COMPLETED = "knowledge:graph:completed"
    INDEXING_STARTED = "indexing:started"
    INDEXING_COMPLETED = "indexing:completed"
    
    # Document completion
    DOCUMENT_PROCESSED = "document:processed"
    DOCUMENT_ERROR = "document:error"
    
    # Agent events
    AGENT_STARTED = "agent:started"
    AGENT_THINKING = "agent:thinking"
    AGENT_WAITING = "agent:waiting"
    AGENT_RUNNING = "agent:running"
    AGENT_PROGRESS = "agent:progress"
    AGENT_COMPLETED = "agent:completed"
    AGENT_ERROR = "agent:error"
    AGENT_CANCELLED = "agent:cancelled"
    
    # RAG events
    RAG_QUERY_STARTED = "rag:query:started"
    RAG_RETRIEVAL_STARTED = "rag:retrieval:started"
    RAG_RETRIEVAL_COMPLETED = "rag:retrieval:completed"
    RAG_RERANKING_STARTED = "rag:reranking:started"
    RAG_RERANKING_COMPLETED = "rag:reranking:completed"
    RAG_CONTEXT_BUILDING = "rag:context:building"
    RAG_REASONING_STARTED = "rag:reasoning:started"
    RAG_REASONING_COMPLETED = "rag:reasoning:completed"
    RAG_GENERATION_STARTED = "rag:generation:started"
    RAG_STREAMING = "rag:streaming"
    RAG_CITATION_VALIDATION = "rag:citation:validation"
    RAG_COMPLETED = "rag:completed"
    RAG_ERROR = "rag:error"
    
    # Workflow events
    WORKFLOW_STARTED = "workflow:started"
    WORKFLOW_STEP_STARTED = "workflow:step:started"
    WORKFLOW_STEP_COMPLETED = "workflow:step:completed"
    WORKFLOW_PROGRESS = "workflow:progress"
    WORKFLOW_COMPLETED = "workflow:completed"
    WORKFLOW_FAILED = "workflow:failed"
    WORKFLOW_CANCELLED = "workflow:cancelled"
    
    # Execution events
    EXECUTION_STARTED = "execution:started"
    EXECUTION_PROGRESS = "execution:progress"
    EXECUTION_LOG = "execution:log"
    EXECUTION_COMPLETED = "execution:completed"
    EXECUTION_FAILED = "execution:failed"
    EXECUTION_OUTPUT = "execution:output"
    
    # Research events
    RESEARCH_STARTED = "research:started"
    RESEARCH_PLANNING = "research:planning"
    RESEARCH_SEARCHING = "research:searching"
    RESEARCH_VERIFYING = "research:verifying"
    RESEARCH_CONFLICT_DETECTION = "research:conflict:detection"
    RESEARCH_EVIDENCE_RANKING = "research:evidence:ranking"
    RESEARCH_REASONING = "research:reasoning"
    RESEARCH_REPORT_GENERATION = "research:report:generation"
    RESEARCH_NOTEBOOK_CREATION = "research:notebook:creation"
    RESEARCH_COMPLETED = "research:completed"
    
    # Background task events
    TASK_QUEUED = "task:queued"
    TASK_STARTED = "task:started"
    TASK_PROGRESS = "task:progress"
    TASK_COMPLETED = "task:completed"
    TASK_FAILED = "task:failed"
    TASK_CANCELLED = "task:cancelled"
    
    # System events
    SYSTEM_STATUS = "system:status"
    SYSTEM_ERROR = "system:error"
    SYSTEM_WARNING = "system:warning"
    HEALTH_CHECK = "health:check"


@dataclass
class Event:
    """Event structure for all real-time updates."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    workspace_id: Optional[int] = None
    document_id: Optional[int] = None
    user_id: Optional[int] = None
    agent_id: Optional[str] = None
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "type": self.type,
            "timestamp": self.timestamp,
            "workspace_id": self.workspace_id,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "data": self.data,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class EventEmitter:
    """
    Production-grade event emitter for real-time updates.
    
    Features:
    - Async event emission
    - Event buffering for high-frequency events
    - Automatic batching for efficiency
    - Integration with WebSocket manager
    - Event history for replay
    """
    
    def __init__(self, batch_interval: float = 0.1, batch_size: int = 50):
        """
        Initialize the event emitter.
        
        Args:
            batch_interval: Time in seconds between batch flushes
            batch_size: Maximum events per batch
        """
        self._ws_manager = None
        self._event_buffer: List[Event] = []
        self._batch_interval = batch_interval
        self._batch_size = batch_size
        self._flush_task: Optional[asyncio.Task] = None
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._is_running = False
        
    def set_ws_manager(self, ws_manager) -> None:
        """Set the WebSocket connection manager."""
        self._ws_manager = ws_manager
        
    async def start(self) -> None:
        """Start the event emitter."""
        if self._is_running:
            return
        self._is_running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Event emitter started")
        
    async def stop(self) -> None:
        """Stop the event emitter and flush remaining events."""
        self._is_running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush()
        logger.info("Event emitter stopped")
        
    async def _flush_loop(self) -> None:
        """Background loop to flush events periodically."""
        while self._is_running:
            try:
                await asyncio.sleep(self._batch_interval)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")
                
    async def _flush(self) -> None:
        """Flush buffered events to all subscribers."""
        if not self._event_buffer:
            return
            
        events_to_flush = self._event_buffer.copy()
        self._event_buffer.clear()
        
        for event in events_to_flush:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
        
        if self._ws_manager:
            for event in events_to_flush:
                await self._broadcast_event(event)
                
        for event in events_to_flush:
            for callback in self._subscribers.get(event.type, []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in event subscriber: {e}")
                    
    async def _broadcast_event(self, event: Event) -> None:
        """Broadcast an event to all relevant WebSocket clients."""
        if not self._ws_manager:
            return
            
        workspace_id = event.workspace_id
        if workspace_id is None and event.document_id:
            workspace_id = 1
            
        if workspace_id:
            try:
                await self._ws_manager.broadcast(workspace_id, event.to_dict())
            except Exception as e:
                logger.error(f"Error broadcasting event: {e}")
                
    async def emit(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[int] = None,
        document_id: Optional[int] = None,
        user_id: Optional[int] = None,
        agent_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        immediate: bool = False,
    ) -> Event:
        """
        Emit an event.
        
        Args:
            event_type: Type of event
            data: Event data
            workspace_id: Associated workspace
            document_id: Associated document
            user_id: Associated user
            agent_id: Associated agent
            workflow_id: Associated workflow
            execution_id: Associated execution
            immediate: If True, flush immediately (for important events)
            
        Returns:
            The created event
        """
        event = Event(
            type=event_type,
            workspace_id=workspace_id,
            document_id=document_id,
            user_id=user_id,
            agent_id=agent_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            data=data or {},
        )
        
        self._event_buffer.append(event)
        
        if immediate or len(self._event_buffer) >= self._batch_size:
            await self._flush()
            
        return event
        
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe to events of a specific type."""
        self._subscribers[event_type].append(callback)
        
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Unsubscribe from events of a specific type."""
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            
    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Get recent event history."""
        history = self._event_history
        if event_type:
            history = [e for e in history if e.type == event_type]
        return history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get emitter statistics."""
        return {
            "buffer_size": len(self._event_buffer),
            "history_size": len(self._event_history),
            "subscribers": {k: len(v) for k, v in self._subscribers.items()},
            "is_running": self._is_running,
        }


# Global event emitter instance
_event_emitter: Optional[EventEmitter] = None


def get_event_emitter() -> EventEmitter:
    """Get the global event emitter instance."""
    global _event_emitter
    if _event_emitter is None:
        _event_emitter = EventEmitter()
    return _event_emitter


async def emit_event(
    event_type: str,
    data: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Event:
    """Convenience function to emit an event."""
    emitter = get_event_emitter()
    return await emitter.emit(event_type, data, **kwargs)
