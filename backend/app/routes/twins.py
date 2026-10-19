from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any

from backend.app.services.twin_service import twin_service

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
def list_twins():
    return twin_service.list_twins()

@router.get("/{twin_id}")
def get_snapshot(twin_id: str):
    try:
        return twin_service.get_snapshot(twin_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{twin_id}/glucose")
def get_glucose(twin_id: str, minutes: int = 180):
    try:
        return twin_service.get_glucose(twin_id, minutes)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{twin_id}/predictions")
def get_predictions(twin_id: str):
    try:
        return twin_service.get_predictions(twin_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{twin_id}/explanation")
def get_explanation(twin_id: str):
    try:
        res = twin_service.get_explanation(twin_id)
        if "error" in res:
            raise HTTPException(status_code=400, detail=res["error"])
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.websocket("/{twin_id}/ws")
async def twin_websocket(websocket: WebSocket, twin_id: str):
    await twin_service.connect_ws(twin_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming message if any
    except WebSocketDisconnect:
        twin_service.disconnect_ws(twin_id, websocket)
