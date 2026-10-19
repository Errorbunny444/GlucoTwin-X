import pytest
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.glucotwin.twin.engine import DigitalTwinEngine
from src.glucotwin.features.glucose_forecasting import build_patient_features

@pytest.fixture
def mock_engine():
    # We rely on DT-01 being present in twin_static_profiles.csv
    return DigitalTwinEngine("DT-01")

def test_initialization(mock_engine):
    assert mock_engine.twin_id == "DT-01"
    assert mock_engine.static_state.age > 0
    assert mock_engine.is_prediction_ready() == False

def test_invalid_initialization():
    with pytest.raises(ValueError):
        DigitalTwinEngine("INVALID-TWIN")

def test_warmup(mock_engine):
    # Not ready initially
    assert not mock_engine.is_prediction_ready()
    # Add a single cgm
    mock_engine.update(datetime(2020, 1, 1, 10, 0), glucose=100.0)
    assert not mock_engine.is_prediction_ready()
    
    # Add cgm 120 mins later
    mock_engine.update(datetime(2020, 1, 1, 12, 0), glucose=110.0)
    assert mock_engine.is_prediction_ready()

def test_inference_and_risk(mock_engine):
    start = datetime(2020, 1, 1, 10, 0)
    for i in range(25):
        # 0 to 120 mins
        ts = start + pd.Timedelta(minutes=5 * i)
        mock_engine.update(ts, glucose=100.0 + i)
        
    assert mock_engine.is_prediction_ready()
    
    pred = mock_engine.predict()
    assert pred is not None
    assert 0 <= pred.high_glucose_probability <= 1
    assert pred.predicted_glucose_120m > 0
    
    if pred.high_glucose_probability >= pred.alert_threshold:
        assert pred.high_glucose_risk == True
    else:
        assert pred.high_glucose_risk == False

def test_feature_parity():
    # This checks that the batch feature logic produces the exact same vector as the online feature logic
    engine = DigitalTwinEngine("DT-01")
    start = datetime(2020, 1, 1, 10, 0)
    cgm_events = []
    
    # 180 mins history + 130 mins future
    for i in range(63): 
        ts = start + pd.Timedelta(minutes=5 * i)
        cgm_events.append({'timestamp': ts, 'glucose': 100.0 + i})
        
    # The online engine only sees up to 180 mins
    eval_ts = start + pd.Timedelta(minutes=5 * 36)
    
    for ev in cgm_events[:37]:
        engine.update(ev['timestamp'], glucose=ev['glucose'])
        
    df_cgm = pd.DataFrame(cgm_events)
    
    # Batch builder
    df_batch = build_patient_features("DT-01", df_cgm, pd.DataFrame(), pd.DataFrame(), engine.df_static, is_online=False)
    
    # Online builder
    # We pass only the history up to eval_ts
    df_cgm_online = pd.DataFrame(cgm_events[:37])
    df_online = build_patient_features("DT-01", df_cgm_online, pd.DataFrame(), pd.DataFrame(), engine.df_static, is_online=True, online_timestamp=eval_ts)
    
    # They should match at the eval_ts
    batch_row = df_batch[df_batch['prediction_timestamp'] == eval_ts]
    online_row = df_online[df_online['prediction_timestamp'] == eval_ts]
    
    # Check that required features match
    for col in engine.features_order:
        batch_val = batch_row.iloc[0][col]
        online_val = online_row.iloc[0][col]
        
        if pd.isna(batch_val) and pd.isna(online_val):
            continue
            
        assert abs(batch_val - online_val) < 1e-6, f"Mismatch on {col}: Batch={batch_val}, Online={online_val}"
