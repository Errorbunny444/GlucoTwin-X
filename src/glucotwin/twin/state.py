from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import pandas as pd
from datetime import datetime

@dataclass
class StaticTwinState:
    twin_id: str
    age: float
    gender: str
    bmi: float
    hba1c: float
    fasting_glucose: float
    fasting_insulin: float
    cholesterol: float
    hdl: float
    ldl: float
    triglycerides: float
    ehr_has_hypertension: float
    ehr_has_dyslipidemia: float
    ehr_has_diabetes_medication: float
    ehr_has_insulin: float

@dataclass
class DynamicTwinState:
    current_timestamp: datetime
    current_glucose: Optional[float] = None
    glucose_trend: Optional[str] = None
    heart_rate: Optional[float] = None
    minutes_since_last_meal: Optional[float] = None
    recent_carbs_120m: Optional[float] = None

@dataclass
class PredictionState:
    prediction_timestamp: datetime
    predicted_glucose_120m: float
    lower_90: float
    upper_90: float
    high_glucose_probability: float
    high_glucose_risk: bool
    alert_threshold: float

@dataclass
class DigitalTwinState:
    twin_id: str
    timestamp: datetime
    status: str
    prediction_ready: bool
    static: StaticTwinState
    dynamic: DynamicTwinState
    prediction: Optional[PredictionState] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = {
            "twin_id": self.twin_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "prediction_ready": self.prediction_ready,
            "static": {k: v for k, v in self.static.__dict__.items() if k != 'twin_id'},
            "dynamic": {
                "current_timestamp": self.dynamic.current_timestamp.isoformat(),
                "current_glucose": self.dynamic.current_glucose,
                "glucose_trend": self.dynamic.glucose_trend,
                "heart_rate": self.dynamic.heart_rate,
                "minutes_since_last_meal": self.dynamic.minutes_since_last_meal,
                "recent_carbs_120m": self.dynamic.recent_carbs_120m
            }
        }
        if self.prediction:
            d["prediction"] = {
                "prediction_timestamp": self.prediction.prediction_timestamp.isoformat(),
                "predicted_glucose_120m": float(self.prediction.predicted_glucose_120m),
                "lower_90": float(self.prediction.lower_90),
                "upper_90": float(self.prediction.upper_90),
                "high_glucose_probability": float(self.prediction.high_glucose_probability),
                "high_glucose_risk": bool(self.prediction.high_glucose_risk),
                "alert_threshold": float(self.prediction.alert_threshold)
            }
        else:
            d["prediction"] = None
        return d
