"""
Event Stream API

WebSocket endpoint for real-time event streaming to frontend.
This provides the connection that powers the Live Activity Center.
"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.core.security import decode_access_token
from src.core.event_emitter import get_event_emitter, EventEmitter
from src.core.logging import logger
from src.models.user import User
from src.models.workspace import Workspace
from src.services.workspace_service import user_can_access_workspace


router = APIRouter(tags=["Events"])


class EventStreamConnection:
    """Manages a single WebSocket connection for event streaming."""
    
    def __init__(self, websocket: WebSocket, user_id: int, workspace_id: Optional[int] = None):
        self.websocket = websocket
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.subscriptions: set = set()
        self.last_event_id: Optional[str] = None
    
    async def send_event(self, event: dict):
        """Send an event to the client."""
        try:
            await self.websocket.send_json(event)
        except Exception as e:
            logger.error(f"Failed to send event: {e}")
    
    async def send_heartbeat(self):
        """Send a heartbeat to keep connection alive."""
        try:
            await self.websocket.send_json({
                "type": "heartbeat",
                "timestamp": asyncio.get_event_loop().time()
            })
        except Exception:
            pass


class EventStreamManager:
    """Manages all event stream connections."""
    
    def __init__(self):
        self._connections: dict[int, EventStreamConnection] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    async def connect(self, connection: EventStreamConnection):
        """Register a new connection."""
        self._connections[connection.user_id] = connection
        logger.info(f"Event stream connected: user_id={connection.user_id}")
    
    async def disconnect(self, user_id: int):
        """Remove a connection."""
        if user_id in self._connections:
            del self._connections[user_id]
            logger.info(f"Event stream disconnected: user_id={user_id}")
    
    async def broadcast(self, event: dict, workspace_id: Optional[int] = None, user_id: Optional[int] = None):
        """Broadcast an event to matching connections."""
        for conn in self._connections.values():
            # Match by user_id or workspace_id
            if user_id and conn.user_id == user_id:
                await conn.send_event(event)
            elif workspace_id and conn.workspace_id == workspace_id:
                await conn.send_event(event)


# Global event stream manager
event_stream_manager = EventStreamManager()


def _authenticate(token: str, db: Session) -> Optional[User]:
    """Authenticate a user from their token."""
    try:
        payload = decode_access_token(token)
        if payload.get("type") != "access":
            return None
        email = payload.get("sub")
    except Exception:
        return None
    
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return None
    if payload.get("tv") is not None and payload.get("tv") != user.token_version:
        return None
    return user


@router.websocket("/ws/events")
async def event_stream(
    websocket: WebSocket,
    token: str = Query(...),
    workspace_id: Optional[int] = Query(None),
):
    """
    Real-time event stream WebSocket endpoint.
    
    Clients connect here to receive real-time events for:
    - Document processing
    - RAG queries
    - Agent activity
    - Workflow execution
    - Background tasks
    
    Authentication is via token query param.
    Optional workspace_id filters events to that workspace.
    """
    db = SessionLocal()
    
    try:
        # Authenticate
        user = _authenticate(token, db)
        if not user:
            await websocket.close(code=4401)
            return
        
        # Check workspace access if provided
        if workspace_id:
            workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            if not workspace or not user_can_access_workspace(db, workspace, user):
                await websocket.close(code=4403)
                return
        
        # Accept connection
        await websocket.accept()
        
        # Create connection
        connection = EventStreamConnection(websocket, user.id, workspace_id)
        await event_stream_manager.connect(connection)
        
        # Subscribe to event emitter
        event_emitter = get_event_emitter()
        
        async def on_event(event):
            """Handler for incoming events from the event emitter."""
            event_dict = event.to_dict() if hasattr(event, 'to_dict') else event
            
            # Filter by workspace_id if specified
            if workspace_id:
                event_ws = event_dict.get('workspace_id')
                if event_ws and event_ws != workspace_id:
                    return
            
            # Filter by user_id
            event_user = event_dict.get('user_id')
            if event_user and event_user != user.id:
                return
            
            await connection.send_event(event_dict)
        
        # Register subscription
        if event_emitter:
            event_emitter.subscribe("*", on_event)
        
        # Send connection confirmed
        await websocket.send_json({
            "type": "connected",
            "user_id": user.id,
            "workspace_id": workspace_id,
            "message": "Event stream connected"
        })
        
        # Handle incoming messages (for subscription management)
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message.get("type") == "subscribe":
                    # Handle subscription requests
                    event_types = message.get("event_types", ["*"])
                    connection.subscriptions.update(event_types)
                    await websocket.send_json({
                        "type": "subscribed",
                        "event_types": list(connection.subscriptions)
                    })
                elif message.get("type") == "unsubscribe":
                    event_types = message.get("event_types", [])
                    for et in event_types:
                        connection.subscriptions.discard(et)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "event_types": list(connection.subscriptions)
                    })
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await connection.send_heartbeat()
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.exception("Event stream error")
    finally:
        if user:
            await event_stream_manager.disconnect(user.id)
        if event_emitter:
            event_emitter.unsubscribe("*", on_event)
        db.close()


@router.get("/events/history")
async def get_event_history(
    workspace_id: Optional[int] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
):
    """
    Get recent event history.
    
    Returns events from the event emitter's history buffer.
    """
    event_emitter = get_event_emitter()
    
    if not event_emitter:
        return {"events": [], "total": 0}
    
    events = event_emitter.get_history(event_type=event_type, limit=limit)
    
    # Filter by workspace if specified
    if workspace_id:
        events = [e for e in events if e.workspace_id == workspace_id]
    
    return {
        "events": [e.to_dict() if hasattr(e, 'to_dict') else e for e in events],
        "total": len(events)
    }


@router.get("/events/stats")
async def get_event_stats():
    """Get event emitter statistics."""
    event_emitter = get_event_emitter()
    
    if not event_emitter:
        return {
            "status": "not_initialized",
            "connections": 0
        }
    
    stats = event_emitter.get_stats()
    return {
        "status": "running",
        "connections": len(event_stream_manager._connections),
        **stats
    }
