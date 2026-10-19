# GlucoTwin-X: Competition Pitch & Presentation Deck

---

## Slide 1: Title & Hook
**Title**: **GlucoTwin-X: A Personalized Hybrid Metabolic Digital Twin for Type-2 Diabetes**  
**Subtitle**: Bridging Continuous Wearable Forecasting, Mechanistic Simulation, and Real-Time Explainability  
**Team**: **Van Der Linde Gang**  
**Members**: **1. Aryan Ranadive, 2. Shubham Sukhadare**  
**Audience**: Healthcare AI Judges, Clinical Evaluators, Biomedical Engineers  

> *"What if a clinician could look 2 hours into a diabetic patient's metabolic future—understand exactly why a glucose spike will happen, test hypothetical interventions before they occur, and watch the patient's physiology respond in real time?"*

---

## Slide 2: The Clinical Problem
### The Reactive Trap in Diabetes Management
- **422M+ People Worldwide** live with diabetes; Type-2 Diabetes accounts for over 90% of cases.
- **Traditional Continuous Glucose Monitors (CGMs)** are **retrospective**: they show what has already happened or give reactive alarms when hyperglycemia (>180 mg/dL) is already underway.
- **The "Black Box" Dilemma**: Existing AI predictors output numbers without physiological context or explanation, failing clinician trust.
- **No Counterfactual Reasoning**: Current clinical dashboards cannot answer: *"What would happen to this patient if they ate 40g of carbs right now versus going for a 30-minute walk?"*

---

## Slide 3: The Solution — GlucoTwin-X
### A Multimodal, Continuously Updating Digital Twin
GlucoTwin-X is an end-to-end Metabolic Digital Twin integrating:
1. **Static Clinical Context (EHR)**: Demographics, HbA1c, baseline labs, and medications from Synthea.
2. **Dynamic Streaming Telemetry**: 1-minute high-resolution CGM, macronutrient meal logs, step counts, and heart rate from the clinical CGMacros cohort.
3. **Hybrid AI Engine**: Combines statistical machine learning (predictive forecasting) with biophysical differential equations (counterfactual simulation).
4. **Physician Cockpit & 3D Twin**: Live React dashboard synchronized with an interactive 3D anatomical metabolic visualization.

---

## Slide 4: Hybrid System Architecture
```
┌────────────────────────────────────────────────────────┐
│               MULTIMODAL DATA STREAMS                  │
│   Synthea Static EHR   +   CGMacros 1-Min Wearables    │
└──────────────────────────┬─────────────────────────────┘
                           │ 5-Min Feature Pipeline
                           ▼
┌────────────────────────────────────────────────────────┐
│                 DIGITAL TWIN ENGINE                    │
│   Online Buffer • Feature Parity • State Machine       │
└────────────┬─────────────────────────────┬─────────────┘
             │                             │
    ┌────────▼────────┐           ┌────────▼────────┐
    │  ML PREDICTION  │           │  PHYSIOLOGICAL  │
    │  (XGBoost 120m) │           │  (Bergman ODE)  │
    │  • Forecast     │           │  • What-If Lab  │
    │  • Risk Score   │           │  • Carb Bolus   │
    │  • SHAP XAI     │           │  • Exercise     │
    └────────┬────────┘           └────────┬────────┘
             │                             │
             └──────────────┬──────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│             FASTAPI REAL-TIME BACKEND                  │
│       REST Endpoints  •  Bi-directional WebSocket      │
└────────────┬─────────────────────────────┬─────────────┘
             │                             │
    ┌────────▼────────┐           ┌────────▼────────┐
    │ REACT DASHBOARD │           │ UNITY 3D TWIN   │
    │ Doctor Cockpit  │           │ Photorealistic  │
    │ Forecast Curves │           │ Organ Telemetry │
    └─────────────────┘           └─────────────────┘
```

---

## Slide 5: Rigorous Machine Learning Validation
### 120-Minute Glucose Horizon Forecasting
We strictly separated subject cohorts to guarantee zero data leakage (unseen patient generalization):

| Model | Evaluation Protocol | Metric | Baseline Comparison |
| :--- | :--- | :--- | :--- |
| **XGBoost Regressor (R2)** | GroupKFold (Cross-Patient) | **MAE = 29.74 mg/dL**<br>RMSE = 40.04 mg/dL | Persistence: 35.02 mg/dL<br>CGM-only: 31.55 mg/dL |
| **XGBoost Regressor (R2)** | Strict Temporal Holdout | **MAE = 41.01 mg/dL** | Evaluates long-term stability |
| **Risk Classifier (C2)** | GroupKFold (High Glucose >180) | **AUROC = 0.916**<br>**PR-AUC = 0.902** | Threshold Baseline: 0.775<br>CGM-only: 0.856 |
| **Alert Calibration** | Optimal Clinical Operating Point | **Alert Threshold = 0.45** | **F1 = 0.836**, Recall = 0.790, Precision = 0.889 |

> **Key Finding**: Dynamic multimodal fusion (CGM + Meals + Heart Rate + Steps) clearly outperforms CGM-only models by ~1.8 mg/dL in MAE and +0.06 in AUROC.

---

## Slide 6: Explainable AI (TreeSHAP)
### Moving from "Black-Box" to Actionable Clinical Insight
- For every 5-minute prediction, **TreeSHAP** calculates exact Shapley additive attributions for each active feature.
- **Top Drivers Identified**:
  - `cgm_rolling_mean_30`: Primary momentum driver.
  - `cgm_roc_15`: Rapid rate of glucose change.
  - `meal_carbs_window_60`: Postprandial carb surge.
  - `hr_mean_60` & `steps_sum_60`: Protective / metabolic expenditure buffer.
- Displayed as **live color-coded feature impact bars** on the clinician's dashboard.

---

## Slide 7: The "What-If" Simulation Engine
### Mechanistic Glucose-Insulin Surrogate (Bergman Minimal Model)
While ML excels at predicting the *expected* path under normal conditions, it cannot reliably simulate never-seen interventions. 
GlucoTwin-X integrates an executable biophysical ODE:
$$\frac{dG}{dt} = -(p_1 + X)G(t) + p_1 G_b + D(t) - E(t)$$
$$\frac{dX}{dt} = -p_2 X(t) + p_3 (I(t) - I_b)$$
$$\frac{dI}{dt} = -n(I(t) - I_b) + \gamma (G(t) - h)^+$$

- Solved in real-time via `scipy.integrate.solve_ivp` (RK45 numerical integrator).
- **Interactive Scenarios**: Clinicians can test **Carbohydrate Boluses** (e.g., 30g, 60g) and **Physical Activity Sessions** (30 min walking) and instantly compare the simulated future against the ML baseline.

---

## Slide 8: The Photorealistic 3D Digital Twin (Unity)
### Bringing Physiology to Life
- **3D Anatomical Assets**: Real-world textured high-fidelity meshes:
  - **Stomach** (54 MB high-resolution mesh from Sketchfab)
  - **Pancreas** (173,000 vertex anatomical model with PBR textures)
  - **Intestine** (folded multi-loop digestive tract)
  - **Bloodstream** (pulsing particle flow system)
- **Live State Feedback**:
  - Normal State: Gentle circulation, neutral organ emission.
  - High Risk Alert ($P > 0.45$): Pancreas flashes red with pulsing emission warning; bloodstream particle speed accelerates proportional to glucose velocity.

---

## Slide 9: Live Demo Workflow (5 Minutes)
1. **Select Twin (`DT-01`)**: Review static clinical profile (Age 59, Female, BMI 26.95, HbA1c 6.5%, Metformin).
2. **Start Historical Replay**: Stream continuous wearable sensor data at 5-minute intervals.
3. **Observe ML Forecast**: Watch the 120-minute forecast curve update with its empirical 90% prediction interval.
4. **Trigger High-Risk Transition**: Observe the SHAP explanation panel illuminate the exact meal surge causing the impending spike.
5. **View 3D Twin Synchronization**: Watch the Unity visualizer reflect the alert state with glowing pancreas emission.
6. **Run "What-If" Counterfactual**: Simulate 45 minutes of light exercise to observe the simulated excursion drop safely into target range (70–140 mg/dL).

---

## Slide 10: Limitations & Research Ethics
- **Synthetic Composite Nature**: 14 Type-2 Diabetes patient profiles fused from Synthea and CGMacros.
- **Research Prototype Disclaimer**: Strictly intended for translational research and algorithmic benchmarking; not approved as an FDA/CE diagnostic or therapeutic decision-support tool.
- **Future Roadmap**:
  - Expansion to larger multi-cohort clinical trials (T1D & T2D).
  - Closed-loop automated insulin/medication recommendation modules.
  - WebGL / WebGPU in-browser 3D rendering.

---

## Slide 11: Summary & Value Proposition
**GlucoTwin-X demonstrates the future of personalized medicine**:
- **Predictive**: Foresees glucose trends 2 hours ahead (MAE ~29.7 mg/dL).
- **Explainable**: Justifies every alert with real-time SHAP feature importance.
- **Simulative**: Allows counterfactual scenario testing before real-world patient actions.
- **Visual**: Bridges data science and clinical intuition through synchronized 3D telemetry.
