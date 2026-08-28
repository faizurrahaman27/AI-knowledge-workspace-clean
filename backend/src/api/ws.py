from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.core.security import decode_access_token
from src.core.ws_manager import manager
from src.core.logging import logger
from src.models.user import User
from src.models.workspace import Workspace
from src.services.workspace_service import user_can_access_workspace

router = APIRouter(tags=["Live Collaboration"])


def _authenticate(token: str, db: Session) -> User | None:
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


@router.websocket("/ws/workspace/{workspace_id}")
async def workspace_socket(
    websocket: WebSocket,
    workspace_id: int,
    token: str = Query(...),
):
    """
    Live collaboration channel for a workspace: every connected member
    gets pushed a `chat_message` event the instant anyone in the
    workspace asks a question and gets an answer, plus simple presence
    ("N members online"). Auth is via a `?token=` query param -- browsers
    can't attach custom headers to a WebSocket handshake, so this is the
    standard pattern; the token is short-lived (same access token as
    everywhere else) and never logged.
    """
    db: Session = SessionLocal()

    try:
        user = _authenticate(token, db)
        if not user:
            await websocket.close(code=4401)
            return

        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace or not user_can_access_workspace(db, workspace, user):
            await websocket.close(code=4403)
            return

        await manager.connect(workspace_id, user.id, websocket)

        try:
            while True:
                # We don't currently act on inbound messages (chat is sent
                # via the normal REST /chat/ endpoint, which broadcasts the
                # result here) -- this just keeps the connection open and
                # detects disconnects. A ping/pong or typing-indicator
                # protocol would go here if you extend this.
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(workspace_id, user.id)
            await manager.broadcast_presence(workspace_id)

    except Exception:
        logger.exception("Workspace websocket error (workspace_id=%s)", workspace_id)
    finally:
        db.close()
