from fastapi import WebSocket
from typing import List
import json


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[ws] client connected. total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[ws] client disconnected. total: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: dict):
        message = json.dumps({"type": event_type, "data": data})
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)

        # clean up dead connections
        for d in dead:
            self.disconnect(d)

    async def broadcast_agent_event(self, event: str, app_name: str, details: dict = {}):
        await self.broadcast("agent_event", {
            "event": event,
            "app_name": app_name,
            "details": details,
        })

    async def broadcast_metric(self, app_id: str, app_name: str, metric: dict):
        await self.broadcast("metric_update", {
            "app_id": app_id,
            "app_name": app_name,
            "metric": metric,
        })

    async def broadcast_health(self, app_id: str, app_name: str, is_healthy: bool, message: str = ""):
        await self.broadcast("health_update", {
            "app_id": app_id,
            "app_name": app_name,
            "is_healthy": is_healthy,
            "message": message,
        })

    async def broadcast_approval_request(self, thread_id: str, incident_data: dict):
        await self.broadcast("approval_request", {
            "thread_id": thread_id,
            "incident": incident_data,
        })


# single instance used across the app
ws_manager = WebSocketManager()