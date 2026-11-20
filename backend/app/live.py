"""Live classroom sync over WebSockets: one room per class code, teacher + students."""
import asyncio
from collections import defaultdict

from fastapi import WebSocket


class Room:
    def __init__(self):
        self.teachers: set[WebSocket] = set()
        self.students: dict[WebSocket, str] = {}


class LiveHub:
    def __init__(self):
        self.rooms: dict[str, Room] = defaultdict(Room)
        self.lock = asyncio.Lock()

    async def join(self, code: str, ws: WebSocket, role: str, name: str = ""):
        async with self.lock:
            room = self.rooms[code]
            if role == "teacher":
                room.teachers.add(ws)
            else:
                room.students[ws] = name
        await self.presence(code)

    async def leave(self, code: str, ws: WebSocket):
        async with self.lock:
            room = self.rooms.get(code)
            if not room:
                return
            room.teachers.discard(ws)
            room.students.pop(ws, None)
            if not room.teachers and not room.students:
                self.rooms.pop(code, None)
        await self.presence(code)

    async def _send(self, targets, message: dict):
        for ws in list(targets):
            try:
                await ws.send_json(message)
            except Exception:
                pass  # a dropped socket is removed by its own disconnect handler

    async def to_all(self, code: str, message: dict):
        room = self.rooms.get(code)
        if room:
            await self._send([*room.teachers, *room.students], message)

    async def to_teachers(self, code: str, message: dict):
        room = self.rooms.get(code)
        if room:
            await self._send(room.teachers, message)

    async def presence(self, code: str):
        room = self.rooms.get(code)
        if room:
            await self.to_teachers(code, {"type": "presence", "students": sorted(room.students.values())})


hub = LiveHub()
