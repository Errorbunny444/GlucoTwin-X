# Physiological Twin

## Purpose
The Physiological Twin provides a mechanistic, interpretable glucose–insulin simulation that runs parallel to the ML Predictive Twin. While XGBoost excels at empirical forecasting from historical patterns, the physiological model allows for counterfactual scenario simulation (What-If analysis) governed by biological boundaries.

**CRITICAL LIMITATION**: This is a simplified educational/research physiological model, not a validated clinical simulator. It is not intended for medical advice or automated insulin dosing.

## Model Structure
The model is a reduced-order differential equation system inspired by the Bergman Minimal Model, capturing the core dynamics of meal absorption and glucose disposal.

### States (ODEs)
1. **G (Blood Glucose)**: Represents the concentration of glucose in the blood (mg/dL).
2. **X (Effective Insulin Action)**: Represents the latent effect of insulin on promoting glucose disposal (1/min). Since continuous insulin assays are unavailable, this acts as a dynamic proxy driven by elevated glucose.
3. **D (Gut Carbohydrate Compartment)**: Represents the unabsorbed carbohydrate mass in the digestive system (mg).

## Inputs & Parameters
The simulation requires an initial state (`G`, `X`, `D`) and patient-specific parameters.

### Patient Personalization
Parameters are derived deterministically from the patient's `StaticTwinState`:
- **Baseline Glucose (`Gb`)**: Taken from fasting glucose EHR records.
- **Insulin Sensitivity Proxy (`Si`)**: Nominally set, but penalized by elevated BMI and HbA1c.
- **Volume of Distribution (`Vg`)**: Estimated via BMI and standardized height assumptions.

## Execution
Due to licensing constraints, the original `MATLAB/Simulink` files (`simulink/*.m`) cannot execute in the headless CI pipeline. A Python RK45 solver (`src/glucotwin/physiology/metabolic_twin.py`) executing the identical ODEs is used as a surrogate to generate the simulation artifacts.

## Complementing the ML Twin
The models remain separate and serve different purposes:
- **ML Twin (XGBoost)**: Answers "What is likely to happen in the next 120 minutes based on recent data?" (Forecasting mode).
- **Physiological Twin (Simulink/ODE)**: Answers "What would happen if the patient ate 50g of carbs right now?" (What-If mode).

## Integration Contract for Later Phases
Future phases (FastAPI, React, Unity) will consume a unified JSON response:
```json
{
  "prediction": {...},
  "explanation": {...},
  "physiology": {
    "trajectory_120m": [...],
    "model_status": "..."
  }
}
```
