import pytest
import json
import numpy as np
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.glucotwin.physiology.what_if import WhatIfScenario, run_what_if_scenarios, WHAT_IF_DISCLAIMER

@pytest.fixture
def dummy_snapshot():
    return {
        "twin_id": "TEST-01",
        "timestamp": "2020-03-14T09:03:00",
        "static": {
            "fasting_glucose": 100.0,
            "bmi": 25.0,
            "hba1c": 5.5
        },
        "dynamic": {
            "current_glucose": 100.0
        }
    }

def test_what_if_basic_execution(dummy_snapshot):
    scenarios = [
        WhatIfScenario(name="Zero Carb", carbs_g=0.0)
    ]
    res = run_what_if_scenarios(dummy_snapshot, scenarios)
    
    assert res['twin_id'] == "TEST-01"
    assert res['disclaimer'] == WHAT_IF_DISCLAIMER
    assert len(res['scenarios']) == 2 # Baseline + Zero Carb
    
    # Baseline vs Zero Carb should be identical
    base = res['scenarios'][0]
    zc = res['scenarios'][1]
    
    assert base['name'] == "Baseline"
    assert zc['name'] == "Zero Carb"
    
    assert abs(base['peak_glucose'] - zc['peak_glucose']) < 1e-4
    assert abs(base['glucose_120m'] - zc['glucose_120m']) < 1e-4
    assert len(base['trajectory']) == 121

def test_what_if_ordering(dummy_snapshot):
    scenarios = [
        WhatIfScenario(name="30g", carbs_g=30.0),
        WhatIfScenario(name="60g", carbs_g=60.0),
        WhatIfScenario(name="60g_act", carbs_g=60.0, activity_level="moderate")
    ]
    res = run_what_if_scenarios(dummy_snapshot, scenarios)
    
    base = res['scenarios'][0]
    s30 = res['scenarios'][1]
    s60 = res['scenarios'][2]
    s60_act = res['scenarios'][3]
    
    # Check bounded response
    assert base['peak_glucose'] < s30['peak_glucose'] < s60['peak_glucose']
    assert s60_act['peak_glucose'] < s60['peak_glucose']
    
    # Check no negative glucose
    for s in res['scenarios']:
        assert all(g >= 0 for g in s['trajectory'])
        assert not any(np.isnan(s['trajectory']))
        assert not any(np.isinf(s['trajectory']))

def test_mutation_protection(dummy_snapshot):
    import copy
    orig = copy.deepcopy(dummy_snapshot)
    run_what_if_scenarios(dummy_snapshot, [WhatIfScenario("test", 50)])
    assert dummy_snapshot == orig # ensure dict not modified in place
