from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Code Graph API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


from app.api.projects import router as projects_router
app.include_router(projects_router)

from app.api.graph import router as graph_router
app.include_router(graph_router)

from fastapi import WebSocket, WebSocketDisconnect
from app.ws.indexing import notifier

@app.websocket("/ws/projects/{project_id}/status")
async def ws_indexing_status(websocket: WebSocket, project_id: str):
    await websocket.accept()
    async def send(msg: dict):
        await websocket.send_json(msg)
    notifier.register(project_id, send)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        notifier.unregister(project_id)
