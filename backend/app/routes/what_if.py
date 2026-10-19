from fastapi import APIRouter, HTTPException
from backend.app.schemas import WhatIfRequest
from backend.app.services.twin_service import twin_service

router = APIRouter()

@router.post("/{twin_id}/what-if")
def run_what_if(twin_id: str, req: WhatIfRequest):
    try:
        return twin_service.run_what_if(twin_id, req.carbs_g, req.activity_level)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
