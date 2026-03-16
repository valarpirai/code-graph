# app/ws/indexing.py
from typing import Callable, Awaitable
from pydantic import BaseModel

class IndexingEvent(BaseModel):
    status: str       # "indexing" | "done" | "error"
    progress: float   # 0.0 – 1.0
    message: str

SendFn = Callable[[dict], Awaitable[None]]

class IndexingNotifier:
    """Tracks active WebSocket connections per project and broadcasts events."""
    def __init__(self):
        self._listeners: dict[str, list[SendFn]] = {}

    def register(self, project_id: str, send_fn: SendFn) -> None:
        self._listeners.setdefault(project_id, []).append(send_fn)

    def unregister(self, project_id: str) -> None:
        self._listeners.pop(project_id, None)

    async def notify(self, project_id: str, event: IndexingEvent) -> None:
        fns = self._listeners.get(project_id, [])
        for fn in fns:
            await fn(event.model_dump())

# Singleton used by FastAPI app
notifier = IndexingNotifier()
