from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    data_ready: bool
    version: str = "1.0.0"

class TwinSummary(BaseModel):
    twin_id: str
    health_group: str
    age: float
    gender: str
    bmi: float
    hba1c: float
    data_duration_days: float
    completeness: float
    demo_role: Optional[str] = None

class WhatIfRequest(BaseModel):
    carbs_g: float = Field(..., ge=0, le=120)
    activity_level: str = Field(..., pattern="^(low|moderate|high)$")

class ReplayStartRequest(BaseModel):
    speed: float = 1.0
    start_position: Optional[str] = None
