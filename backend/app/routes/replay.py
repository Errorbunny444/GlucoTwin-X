from fastapi import APIRouter, HTTPException
from backend.app.schemas import ReplayStartRequest
from backend.app.services.twin_service import twin_service

router = APIRouter()

@router.post("/{twin_id}/replay/start")
async def start_replay(twin_id: str, req: ReplayStartRequest):
    try:
        return await twin_service.start_replay(twin_id, req.speed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{twin_id}/replay/stop")
async def stop_replay(twin_id: str):
    try:
        return await twin_service.stop_replay(twin_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{twin_id}/replay/status")
def replay_status(twin_id: str):
    return twin_service.replay_status(twin_id)
