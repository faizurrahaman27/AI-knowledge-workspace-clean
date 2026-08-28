"""
Real-time layer for workspace collaboration: broadcasts new chat turns to
every member currently connected to that workspace, and tracks a simple
presence count ("N members online").

Honest scope note: this is an in-memory, single-process connection
registry. It works correctly for exactly the deployment this project
ships with (one backend process/container). If you ever run multiple
backend instances behind a load balancer, connections on instance A won't
see broadcasts triggered on instance B -- you'd need a shared pub/sub
(Redis, etc.) to fan out across processes. That's a real, known limit,
not an oversight; called out here and in the README rather than silently
breaking in a scaled deployment.
"""

import json

from fastapi import WebSocket


class WorkspaceConnectionManager:
    def __init__(self):
        # workspace_id -> {user_id: WebSocket}
        self._connections: dict[int, dict[int, WebSocket]] = {}

    async def connect(self, workspace_id: int, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self._connections.setdefault(workspace_id, {})[user_id] = websocket
        await self.broadcast_presence(workspace_id)

    def disconnect(self, workspace_id: int, user_id: int):
        room = self._connections.get(workspace_id)
        if room and user_id in room:
            del room[user_id]
            if not room:
                del self._connections[workspace_id]

    def online_count(self, workspace_id: int) -> int:
        return len(self._connections.get(workspace_id, {}))

    async def broadcast(self, workspace_id: int, payload: dict):
        room = self._connections.get(workspace_id, {})
        dead = []
        for user_id, ws in room.items():
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(user_id)
        for user_id in dead:
            self.disconnect(workspace_id, user_id)

    async def broadcast_presence(self, workspace_id: int):
        await self.broadcast(
            workspace_id,
            {"type": "presence", "online": self.online_count(workspace_id)},
        )


# Process-wide singleton -- see the module docstring for the
# single-process scope limitation.
manager = WorkspaceConnectionManager()
