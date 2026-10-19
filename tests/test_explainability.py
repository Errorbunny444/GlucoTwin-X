import pytest
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.glucotwin.twin.engine import DigitalTwinEngine

def test_explainability_loads_and_explains():
    engine = DigitalTwinEngine("DT-01")
    
    # Warm up engine
    start = datetime(2020, 1, 1, 10, 0)
    for i in range(37):
        ts = start + pd.Timedelta(minutes=5 * i)
        engine.update(ts, glucose=100.0 + i)
        
    assert engine.is_prediction_ready()
    engine.predict()
    
    explanation = engine.explain_current_prediction()
    
    assert explanation is not None
    assert "glucose_forecast_drivers" in explanation
    assert "risk_drivers" in explanation
    assert "clinical_context" in explanation
    
    # Check length
    assert len(explanation["glucose_forecast_drivers"]) == 5
    assert len(explanation["risk_drivers"]) == 5
    
    # Verify exact feature fields
    driver = explanation["glucose_forecast_drivers"][0]
    assert "feature" in driver
    assert "label" in driver
    assert "contribution" in driver
    assert "direction" in driver
    assert "group" in driver
    
    # Check that the model doesn't output targets
    for d in explanation["glucose_forecast_drivers"]:
        assert "target" not in d["feature"]
