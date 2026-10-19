# Explainable AI (SHAP)

## Purpose
The Explainable AI module demystifies the black-box nature of the XGBoost regression and classification models. It answers "Why is the Digital Twin predicting this?" by quantifying the exact contribution of each dynamic feature to the final prediction.

## Implementation Details
- **SHAP (SHapley Additive exPlanations)** is used via the `TreeExplainer`, which is highly optimized for XGBoost and computes exact marginal contributions mathematically grounded in cooperative game theory.
- The explainer is lazy-loaded by the `DigitalTwinEngine` only when `explain_current_prediction()` is called, preventing unnecessary overhead during real-time 1-minute streaming updates.

## Local vs Global Explanations
1. **Local Explanations**: Generated on-demand for a specific Twin state. Returns the top 5 driving features that increase or decrease the predicted glucose and risk probability.
2. **Global Explanations**: A summary of feature importance across a representative cohort sample (e.g., 2000 events) mapping the average impact of features on the model outputs. Found in `artifacts/plots/explainability/`.

## Feature Groups and Human-Readable Labels
Raw ML features (e.g., `carbohydrate_last_120m`) are mapped to human-readable concepts ("Carbs last 2 hours") and categorized into clinical groups:
- **CGM**: Glucose values, trends, variability
- **Meal**: Carbohydrate, protein, fat, and fiber exposures
- **Activity**: Activity calories
- **Heart Rate**: Continuous HR and variability
- **Circadian**: Time of day encoding

## Separation: ML Drivers vs. EHR Context
**Critical Scientific Distinction:** 
The XGBoost dynamic model does **not** directly ingest static EHR variables (e.g., Hypertension, Age) to prevent overfitting on the small 14-subject cohort. Therefore, SHAP will **never** claim that "Hypertension increased this prediction." 

Instead, the explainability output explicitly separates:
1. **Prediction Drivers (ML)**: What dynamic features mathematical drove the prediction (e.g., recent carbohydrates).
2. **Clinical Context (EHR)**: The patient's background physiological profile (e.g., HbA1c 6.5%, BMI 26.9).
