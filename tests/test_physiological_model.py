import pytest
import numpy as np
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.glucotwin.physiology.metabolic_twin import configure_patient_parameters, run_glucotwin_model

def test_physiological_model_execution():
    static_snapshot = {
        "fasting_glucose": 110.0,
        "bmi": 26.0,
        "hba1c": 6.2
    }
    
    params = configure_patient_parameters(static_snapshot)
    
    init_state = {
        "G": 110.0,
        "X": 0.0,
        "D": 0.0
    }
    
    t, y = run_glucotwin_model(params, init_state, 120.0)
    
    # Check length
    assert len(t) == 121
    assert y.shape == (3, 121)
    
    # Check bounds
    assert np.all(np.isfinite(y))
    assert np.all(y[0] >= 0) # Glucose never negative

def test_sanity_ordering():
    static_snapshot = {
        "fasting_glucose": 100.0,
        "bmi": 25.0,
        "hba1c": 5.5
    }
    params = configure_patient_parameters(static_snapshot)
    
    # No meal
    _, y_none = run_glucotwin_model(params, {"G": 100.0, "X": 0.0, "D": 0.0}, 120.0)
    
    # Moderate meal
    _, y_mod = run_glucotwin_model(params, {"G": 100.0, "X": 0.0, "D": 50000.0}, 120.0)
    
    # Large meal
    _, y_large = run_glucotwin_model(params, {"G": 100.0, "X": 0.0, "D": 100000.0}, 120.0)
    
    g_none_max = y_none[0].max()
    g_mod_max = y_mod[0].max()
    g_large_max = y_large[0].max()
    
    assert g_large_max > g_mod_max > g_none_max
