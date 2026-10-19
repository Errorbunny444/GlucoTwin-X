# GlucoTwin-X

GlucoTwin-X is a personalized, multimodal Metabolic Digital Twin developed to provide continuous patient state monitoring, predictive ML forecasting, and mechanistic scenario simulation for Type-2 Diabetes management.

## The Problem
Traditional health dashboards present a static, retrospective view of a patient. They do not intuitively explain *why* metabolic risks are developing, nor do they allow researchers to test immediate hypothetical interventions against the patient's exact metabolic footprint.

## The Solution
GlucoTwin-X fuses synthetic electronic health records (EHR) with high-density dynamic wearable data (CGM, heart rate, physical activity, and macronutrient intake) to create a Continuously Updating Digital Twin. 

## Key Innovation
GlucoTwin-X introduces a **Hybrid Architecture**:
1. **Data-Driven Predictor**: An XGBoost ML pipeline continuously predicts glucose levels 120 minutes into the future using temporal multi-modal features.
2. **Mechanistic Simulator**: A physiological ODE model (representing the Minimal Glucose-Insulin Model) that allows explicit "What-If" testing of alternative meals and activities against the baseline ML forecast.

## Dataset
- **Static EHR**: 14 synthetic composite patients generated via Synthea with explicit T2D diagnoses.
- **Dynamic Data**: ~11 days of continuous 1-minute CGM, meals, and wearable telemetry sourced from the validated CGMacros dataset, dynamically mapped to the static cohorts.

## ML Performance
The forecasting model was rigorously validated via GroupKFold and strict temporal holdout testing to prevent data leakage:
- **Regression Forecast (+120m)**: ~29.75 mg/dL Mean Absolute Error (MAE).
- **High-Glucose Event Classifier**: AUROC ~0.916.
- **Explainability**: SHAP (SHapley Additive exPlanations) isolates real-time contributing drivers for every single prediction.

## Digital Twin Capabilities
- **Real-Time State & Forecasting**: Dynamic updates streaming via WebSockets.
- **Explainable AI (XAI)**: Understand the "Why" behind risk transitions.
- **What-If Physiological Simulation**: Test the immediate future.
- **Doctor Dashboard**: A robust React + Vite interface.
- **3D Visualization**: A Unity-based interactive visualization mirroring the backend metabolic alert states.

## Demo
Please refer to [DEMO.md](DEMO.md) for the exact command-line instructions to launch the FastAPI backend, React frontend, and Unity 3D visualizer.

## Limitations
- **Cohort Size**: Dynamic temporal modeling relies on a subset of 14 unique Type-2 Diabetes participants.
- **EHR Fusion**: Static EHR features were synthetically joined using LOINC-based demographic matching rules.
- **Simplified Physiology**: The What-If simulation relies on a heavily simplified, 3-state ODE representation of metabolism. It generates symbolic mathematical trajectories, not clinical guarantees.
- **MATLAB Licensing**: Due to execution environment constraints, the ODE simulation uses a Python RK45 numerical surrogate rather than the originally intended MATLAB/Simulink compiled environment.
- **Disclaimer**: This is a strictly non-clinical research prototype. It must not be used for diagnosis or treatment recommendations.
