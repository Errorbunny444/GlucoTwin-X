# Digital Twin Engine

## Purpose
The Digital Twin Engine is the core runtime component of GlucoTwin-X. It maintains a continuously evolving virtual state for each patient, mimicking a live data stream. By absorbing raw wearable data chronologically, the Engine remembers recent physiology, infers the future via trained ML models, and tracks risk state over time.

## Static State
Each Twin retains a `StaticTwinState` populated from `twin_static_profiles.csv`. This context acts as the patient's identity and baseline physiology. While not used by the short-horizon dynamic models, the static state grounds the Twin for later physiological modelling, explainability, and UI presentations.

## Dynamic State
The Engine updates its `DynamicTwinState` using a continuous stream of events (CGM readings, meals, activity, heart rate). This state drives feature generation by tracking:
- Current glucose levels and trends
- Rolling carbohydrate exposures
- Activity history

## Predictive State
Every 5 minutes, the Engine constructs a feature vector using the identical logic from the model training phase. It then invokes the final XGBoost regressors and classifiers to output a `PredictionState`, which includes:
- Predicted +120m glucose
- Lower and upper 90% empirical bounds
- High-glucose event probability
- Risk threshold evaluation

## Warm-Up
A Digital Twin requires a sufficient history buffer (180 minutes) to construct valid time-series lag features. During this period, the Twin is in a `warming_up` state. Predictions are only produced when `prediction_ready` flips to `true`, preventing zero-padded feature vectors from emitting unreliable forecasts.

## Prediction Cadence
The Engine is designed to run inference every 5 patient-minutes. This corresponds exactly to the 5-minute grid spacing used during Phase 2 model training, ensuring optimal feature fidelity.

## Replay Mode
The `TwinReplay` system supports time-series simulation by replaying historical CGMacros records chronologically. This is crucial for competition demonstration, as it behaves exactly like a live, connected IoT wearable data stream.

## Risk State
Risk is quantified into simple clinical applications:
- **NORMAL**: High-glucose probability < 0.45
- **HIGH RISK**: High-glucose probability >= 0.45

The Engine records transitions between these states, allowing UI components (like Unity or React) to trigger actionable alerts.

## Ground-Truth Demo Comparison
In Replay Mode, the Engine provides a parallel "future-peeking" evaluation for demo purposes. It compares what the Digital Twin predicted at `t` versus what actually occurred at `t + 120m`. Importantly, the future actual glucose is never exposed to the prediction feature pipeline, preserving strict causal boundaries and preventing data leakage.

## Architectural Boundary
The Digital Twin Engine exclusively owns state, historical buffers, feature parity, and inference. It exposes a simple API (`update`, `predict`, `get_snapshot`) to keep the predictive core isolated from HTTP routes (FastAPI), complex physiological solvers (MATLAB/Simulink), and 3D visualization (Unity). Historical replay mimics a live patient data stream for competition demonstration.
