import numpy as np
from scipy.integrate import solve_ivp
from typing import Dict, Any, Tuple

def configure_patient_parameters(static_snapshot: Dict[str, Any]) -> Dict[str, float]:
    """
    Derive physiological parameters from static twin state.
    Python equivalent of configure_patient_parameters.m
    """
    p = {}
    
    fasting = static_snapshot.get('fasting_glucose', 100.0)
    p['Gb'] = fasting if fasting > 0 else 100.0
    
    bmi = max(20.0, static_snapshot.get('bmi', 25.0))
    hba1c = max(5.0, static_snapshot.get('hba1c', 5.5))
    
    Si_nominal = 0.001
    bmi_factor = max(0.5, 25.0 / bmi)
    hba1c_factor = max(0.5, 5.5 / hba1c)
    p['Si'] = Si_nominal * bmi_factor * hba1c_factor
    
    p['Sg'] = 0.015
    p['p2'] = 0.02
    p['k_abs'] = 0.03
    
    weight_kg = bmi * (1.7**2)
    p['Vg'] = weight_kg * 0.15 * 10
    
    p['f'] = 0.8
    
    return p

def glucotwin_odes(t: float, y: np.ndarray, p: Dict[str, float]) -> np.ndarray:
    G, X, D = y
    
    Ra = (p['f'] * p['k_abs'] * D) / p['Vg']
    
    dG_dt = -(p['Sg'] + X) * G + p['Sg'] * p['Gb'] + Ra
    
    I_sec = max(0, p['Si'] * (G - p['Gb']))
    dX_dt = -p['p2'] * X + p['p2'] * I_sec
    
    dD_dt = -p['k_abs'] * D
    
    return np.array([dG_dt, dX_dt, dD_dt])

def run_glucotwin_model(params: Dict[str, float], initial_state: Dict[str, float], duration_min: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Solves the simplified ODE minimal model.
    Python equivalent of run_glucotwin_model.m
    """
    tspan = (0.0, duration_min)
    y0 = np.array([initial_state['G'], initial_state['X'], initial_state['D']])
    
    # Evaluate every minute
    t_eval = np.arange(0, duration_min + 1, 1.0)
    
    sol = solve_ivp(
        fun=lambda t, y: glucotwin_odes(t, y, params),
        t_span=tspan,
        y0=y0,
        t_eval=t_eval,
        method='RK45'
    )
    
    return sol.t, sol.y
