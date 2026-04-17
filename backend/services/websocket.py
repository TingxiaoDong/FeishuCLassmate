"""
WebSocket connection manager for real-time updates.
"""
import json
from typing import Dict, Set
from fastapi import WebSocket
import asyncio


class ConnectionManager:
    """Manages WebSocket connections for real-time robot updates."""

    def __init__(self):
        self._active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "robot_updates"):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if channel not in self._active_connections:
            self._active_connections[channel] = set()
        self._active_connections[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str = "robot_updates"):
        """Remove a WebSocket connection."""
        if channel in self._active_connections:
            self._active_connections[channel].discard(websocket)

    async def broadcast(self, message: dict, channel: str = "robot_updates"):
        """Broadcast message to all connections in a channel."""
        if channel not in self._active_connections:
            return
        dead_connections = set()
        for connection in self._active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)
        # Clean up dead connections
        for dead in dead_connections:
            self._active_connections[channel].discard(dead)

    async def send_personal(self, message: dict, websocket: WebSocket):
        """Send message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass

    @property
    def connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self._active_connections.values())


# Singleton instance
manager = ConnectionManager()
