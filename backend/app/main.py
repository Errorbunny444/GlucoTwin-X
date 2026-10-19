from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import time

from backend.app.routes import twins, what_if, replay
from backend.app.schemas import HealthResponse
from backend.app.services.twin_service import twin_service

app = FastAPI(
    title="GlucoTwin-X Digital Twin API",
    description="Research and competition prototype. Not intended for clinical diagnosis or treatment.",
    version="1.0.0"
)

# CORS configuration
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(twins.router, prefix="/api/twins", tags=["twins"])
app.include_router(what_if.router, prefix="/api/twins", tags=["what_if"])
app.include_router(replay.router, prefix="/api/twins", tags=["replay"])

@app.websocket("/ws/twins/{twin_id}")
async def root_twin_websocket(websocket: WebSocket, twin_id: str):
    await twin_service.connect_ws(twin_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        twin_service.disconnect_ws(twin_id, websocket)

@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health_check():
    return HealthResponse(
        status="ok",
        models_loaded=True,
        data_ready=True
    )
