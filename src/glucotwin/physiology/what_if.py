from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from .metabolic_twin import run_glucotwin_model, configure_patient_parameters

WHAT_IF_DISCLAIMER = "Simulated research scenario based on a simplified physiological model. Not a clinical recommendation or treatment prediction."
GLUCOSE_THRESHOLD_MGDL = 180.0

@dataclass
class WhatIfScenario:
    name: str
    carbs_g: float = 0.0
    activity_level: str = "low" # "low", "moderate", "high"
    meal_time_offset_min: float = 0.0 # Future feature
    simulation_duration_min: float = 120.0

def run_what_if_scenarios(twin_snapshot: Dict[str, Any], scenarios: List[WhatIfScenario]) -> Dict[str, Any]:
    """
    Run multiple what-if scenarios from a starting twin state.
    baseline scenario is automatically appended as "Baseline" with 0g carbs, low activity.
    """
    static = twin_snapshot.get("static", {})
    dynamic = twin_snapshot.get("dynamic", {})
    
    current_glucose = dynamic.get("current_glucose")
    if current_glucose is None:
        raise ValueError("Cannot run what-if simulation: current_glucose is unknown.")
        
    base_params = configure_patient_parameters(static)
    
    # Internal state proxy
    init_state = {
        "G": current_glucose,
        "X": 0.0,
        "D": 0.0
    }
    
    # Baseline Scenario
    baseline_scenario = WhatIfScenario(name="Baseline")
    all_scenarios = [baseline_scenario] + scenarios
    
    results = []
    baseline_glucose_120m = None
    baseline_trajectory = None
    
    for scen in all_scenarios:
        # Apply activity modifier
        p = base_params.copy()
        if scen.activity_level == "moderate":
            p['Sg'] *= 1.5
        elif scen.activity_level == "high":
            p['Sg'] *= 2.0
            
        # Define state with meal
        scen_state = init_state.copy()
        scen_state["D"] += scen.carbs_g * 1000.0 # convert g to mg
        
        t, y = run_glucotwin_model(p, scen_state, scen.simulation_duration_min)
        glucose_trajectory = y[0]
        
        peak_g = float(np.max(glucose_trajectory))
        time_to_peak = float(t[np.argmax(glucose_trajectory)])
        g_120m = float(glucose_trajectory[-1])
        crosses_threshold = peak_g > GLUCOSE_THRESHOLD_MGDL
        
        if scen.name == "Baseline":
            baseline_glucose_120m = g_120m
            baseline_trajectory = glucose_trajectory
            delta = 0.0
        else:
            delta = float(g_120m - baseline_glucose_120m)
            
        results.append({
            "name": scen.name,
            "peak_glucose": peak_g,
            "time_to_peak_min": time_to_peak,
            "glucose_120m": g_120m,
            "delta_vs_baseline_120m": delta,
            "simulated_threshold_crossing": crosses_threshold,
            "trajectory": glucose_trajectory.tolist(),
            "time": t.tolist()
        })
        
    return {
        "twin_id": twin_snapshot.get("twin_id", "Unknown"),
        "timestamp": twin_snapshot.get("timestamp"),
        "disclaimer": WHAT_IF_DISCLAIMER,
        "scenarios": results
    }
