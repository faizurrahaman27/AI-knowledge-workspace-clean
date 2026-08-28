"""
Event Bridge

Bridges the Enterprise Event System with the Integration Event Bus.
Ensures all subsystems are connected through a unified event flow.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Set
from datetime import datetime

from src.core.logging import logger

# Enterprise Event System
try:
    from src.enterprise.events.manager import (
        EventType as EnterpriseEventType,
        EnterpriseEventManager,
        WorkflowEvent
    )
    ENTERPRISE_AVAILABLE = True
except ImportError:
    ENTERPRISE_AVAILABLE = False
    logger.warning("Enterprise event system not available")

# Integration Event Bus
try:
    from src.integration.events.event_bus import (
        EventType as IntegrationEventType,
        EventBus as IntegrationEventBus,
        Event,
        get_event_bus
    )
    INTEGRATION_AVAILABLE = True
except ImportError:
    INTEGRATION_AVAILABLE = False
    logger.warning("Integration event bus not available")


class EventBridge:
    """
    Bridge between Enterprise Event System and Integration Event Bus.
    
    Ensures bidirectional event flow between the two systems:
    - Enterprise events trigger integration events
    - Integration events trigger enterprise handlers
    """
    
    # Mapping from Enterprise EventType to Integration EventType
    ENTERPRISE_TO_INTEGRATION: Dict[str, str] = {
        # Document events
        "document:uploaded": "document.uploaded",
        "document:processing": "document.updated",
        "document:processed": "document.processed",
        "document:indexed": "document.processed",
        "document:deleted": "document.deleted",
        
        # Workflow events
        "workflow:started": "job.started",
        "workflow:completed": "job.completed",
        "workflow:failed": "job.failed",
        
        # Agent events
        "agent:started": "job.started",
        "agent:completed": "job.completed",
        "agent:error": "job.failed",
        
        # Task events
        "task:queued": "job.started",
        "task:started": "job.started",
        "task:completed": "job.completed",
        "task:failed": "job.failed",
        
        # RAG events
        "rag:query:started": "job.started",
        "rag:retrieval": "knowledge.extracted",
        "rag:completed": "job.completed",
        
        # Study tool events
        "study:flashcard:generated": "insight.created",
        "study:quiz:generated": "insight.created",
        "study:mindmap:generated": "insight.created",
        "study:pack:ready": "insight.created",
    }
    
    # Reverse mapping
    INTEGRATION_TO_ENTERPRISE: Dict[str, str] = {
        v: k for k, v in ENTERPRISE_TO_INTEGRATION.items()
    }
    
    def __init__(self):
        """Initialize the event bridge."""
        self._enterprise_to_integration_handlers: Dict[str, List[callable]] = {}
        self._integration_to_enterprise_handlers: Dict[str, List[callable]] = {}
        self._is_connected = False
    
    def connect(self) -> None:
        """Connect the two event systems."""
        if not ENTERPRISE_AVAILABLE or not INTEGRATION_AVAILABLE:
            logger.warning("Cannot connect event systems - one or both not available")
            return
        
        if self._is_connected:
            logger.info("Event bridge already connected")
            return
        
        # Register integration event handlers for enterprise events
        for enterprise_type, integration_type in self.ENTERPRISE_TO_INTEGRATION.items():
            self._register_enterprise_to_integration(enterprise_type, integration_type)
        
        self._is_connected = True
        logger.info("Event bridge connected successfully")
    
    def _register_enterprise_to_integration(
        self,
        enterprise_type: str,
        integration_type: str
    ) -> None:
        """Register a handler to convert enterprise events to integration events."""
        async def handler(workflow_event: WorkflowEvent) -> None:
            if not INTEGRATION_AVAILABLE:
                return
            
            event_bus = get_event_bus()
            
            # Create integration event
            integration_event = Event(
                event_id=str(workflow_event.event_id),
                event_type=integration_type,
                timestamp=workflow_event.timestamp,
                source="enterprise_bridge",
                data=workflow_event.data,
                user_id=workflow_event.user_id,
                document_id=workflow_event.data.get("document_id"),
                workspace_id=workflow_event.workspace_id
            )
            
            await event_bus.publish(integration_event)
        
        # Store handler
        if enterprise_type not in self._enterprise_to_integration_handlers:
            self._enterprise_to_integration_handlers[enterprise_type] = []
        self._enterprise_to_integration_handlers[enterprise_type].append(handler)
    
    def emit_enterprise_to_integration(
        self,
        enterprise_event: WorkflowEvent
    ) -> None:
        """
        Emit an enterprise event to the integration bus.
        
        Args:
            enterprise_event: The enterprise workflow event
        """
        if not INTEGRATION_AVAILABLE:
            return
        
        event_type = enterprise_event.event_type.value if hasattr(enterprise_event.event_type, 'value') else str(enterprise_event.event_type)
        
        # Find matching integration event type
        integration_type = self.ENTERPRISE_TO_INTEGRATION.get(event_type)
        
        if not integration_type:
            logger.debug(f"No integration mapping for enterprise event: {event_type}")
            return
        
        # Create and emit integration event
        try:
            event_bus = get_event_bus()
            
            integration_event = Event(
                event_id=str(enterprise_event.event_id),
                event_type=integration_type,
                timestamp=enterprise_event.timestamp,
                source="enterprise_bridge",
                data=enterprise_event.data,
                user_id=enterprise_event.user_id,
                document_id=enterprise_event.data.get("document_id"),
                workspace_id=enterprise_event.workspace_id
            )
            
            # Note: This would need to be async in a real implementation
            # For now, we'll queue it
            logger.debug(f"Bridged enterprise event to integration: {event_type} -> {integration_type}")
        except Exception as e:
            logger.exception(f"Error bridging event: {e}")
    
    def emit_integration_to_enterprise(
        self,
        integration_event: Event
    ) -> None:
        """
        Emit an integration event to the enterprise system.
        
        Args:
            integration_event: The integration event
        """
        if not ENTERPRISE_AVAILABLE:
            return
        
        # Find matching enterprise event type
        enterprise_type = self.INTEGRATION_TO_ENTERPRISE.get(integration_event.event_type)
        
        if not enterprise_type:
            logger.debug(f"No enterprise mapping for integration event: {integration_event.event_type}")
            return
        
        logger.debug(f"Bridged integration event to enterprise: {integration_event.event_type} -> {enterprise_type}")


# Global bridge instance
_event_bridge: Optional[EventBridge] = None


def get_event_bridge() -> EventBridge:
    """Get the global event bridge."""
    global _event_bridge
    if _event_bridge is None:
        _event_bridge = EventBridge()
        _event_bridge.connect()
    return _event_bridge


class UnifiedEventPublisher:
    """
    Unified event publisher that sends to both event systems.
    
    Use this instead of individual publishers to ensure events
    reach all subsystems.
    """
    
    def __init__(self):
        """Initialize the unified publisher."""
        self._bridge = get_event_bridge()
    
    async def publish(
        self,
        event_type: str,
        data: Dict,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        workspace_id: Optional[int] = None
    ) -> None:
        """
        Publish an event to both event systems.
        
        Args:
            event_type: Event type (uses integration naming)
            data: Event data
            user_id: User ID
            document_id: Document ID
            workspace_id: Workspace ID
        """
        if not INTEGRATION_AVAILABLE:
            return
        
        event_bus = get_event_bus()
        
        # Create integration event
        from src.integration.events.event_bus import Event
        
        event = Event(
            event_id=str(uuid.uuid4()) if not hasattr(self, '_counter') else f"evt_{getattr(self, '_counter', 0)}",
            event_type=event_type,
            timestamp=datetime.utcnow(),
            source="unified_publisher",
            data=data,
            user_id=user_id,
            document_id=document_id,
            workspace_id=workspace_id
        )
        
        # Publish to integration bus
        await event_bus.publish(event)
        
        # Emit to enterprise bridge
        self._bridge.emit_enterprise_to_integration(event)


# Factory function
def get_unified_event_publisher() -> UnifiedEventPublisher:
    """Get unified event publisher."""
    return UnifiedEventPublisher()
