# GlucoTwin-X: Personalized Hybrid Metabolic Digital Twin

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/Frontend-React_19-61dafb.svg)](https://react.dev/)
[![Unity 3D](https://img.shields.io/badge/Engine-Unity_3D-white.svg)](https://unity.com/)

**GlucoTwin-X** is an end-to-end, multimodal Metabolic Digital Twin developed for Type-2 Diabetes management. It bridges predictive machine learning forecasting, biophysical differential simulation ("What-If" counterfactuals), real-time explainable AI (XAI), and dual-tiered 3D visualization.

---

## 👥 Team Details
- **Team Name**: **Van Der Linde Gang**
- **Members**:
  1. **Aryan Ranadive**
  2. **Shubham Sukhadare**
- **Domain**: Healthcare AI / Biomedical Engineering / Cyber-Physical Systems

---

## 🎯 Problem Statement
Traditional health monitors and continuous glucose monitors (CGMs) suffer from the **"Reactive Care Trap"**:
1. **Retrospective Alerts**: Standard CGMs alarm only *after* harmful hyperglycemia (>180 mg/dL) or hypoglycemia (<70 mg/dL) is already occurring.
2. **The "Black Box" Dilemma**: Existing AI algorithms predict numbers without explaining the physiological drivers, failing clinician trust.
3. **No Counterfactual Reasoning**: Current clinical dashboards cannot test: *"What happens to this patient if they consume 45g of carbohydrates now versus taking a 30-minute walk?"*

---

## 🏥 Healthcare Use Case
GlucoTwin-X operates as a **Clinical Decision-Support Cockpit** for endocrinologists and diabetes researchers:
- **Proactive Excursion Prevention**: Provides a 120-minute forward-looking window so interventions can be staged before glucose surges.
- **Explainable Driver Attribution**: Isolates whether a pending excursion is fueled by postprandial meals, rate of change, or lack of physical movement.
- **Counterfactual "What-If" Simulation**: Allows clinicians to test hypothetical dietary boluses or activity sessions against the patient's baseline without risking real patient health.

---

## 🛠️ Technical Stack
| Layer | Technologies |
| :--- | :--- |
| **Data Ingestion** | Synthea Static EHR (demographics, HbA1c, baseline labs) + CGMacros 1-Min Wearables (CGM, meals, HR, steps) |
| **Predictive ML** | XGBoost (Dynamic Multimodal Regressor & Classifier), Scikit-Learn, PyArrow, Pandas, NumPy |
| **Explainable AI (XAI)** | TreeSHAP (SHapley Additive exPlanations for real-time local attributions) |
| **Physiological Twin** | Bergman Minimal Model (3-State Glucose-Insulin Dynamics) solved via SciPy RK45 Integrator |
| **Backend & Streaming** | FastAPI, Uvicorn, WebSockets, Pydantic |
| **Frontend Cockpit** | React 19, TypeScript, Vite, Tailwind CSS, Recharts, Three.js (WebGL 3D) |
| **3D & CAD Engine** | Unity 2022.3/6 LTS (URP, C# WebSockets, PBR Shaders), Autodesk Fusion 360 (Procedural Python API) |

---

## 🧠 AI / ML Model & Framework Details
The predictive pipeline was trained on 43,075 samples and validated using strict cross-subject protocols to prevent data leakage:

| Model Task | Framework | Validation Protocol | Primary Metrics | Baseline Comparison |
| :--- | :--- | :--- | :--- | :--- |
| **120-Min Regression** | XGBoost (R2) | GroupKFold (Unseen Patients) | **MAE: 29.74 mg/dL**<br>RMSE: 40.04 mg/dL | Persistence: 35.02 mg/dL<br>CGM-only: 31.55 mg/dL |
| **Long-Term Stability** | XGBoost (R2) | Strict Temporal Holdout | **MAE: 41.01 mg/dL** | Evaluates long-term generalizability |
| **Hyperglycemia Risk** | XGBoost (C2) | GroupKFold (High Glucose >180) | **AUROC: 0.916**<br>**PR-AUC: 0.902** | Reactive Baseline: 0.775<br>CGM-only: 0.856 |
| **Alert Calibration** | Threshold Tuning | Optimal Operating Point | **Alert Threshold: 0.45** | **F1: 0.836**, Precision: 0.889, Recall: 0.790 |

- **Explainability**: TreeSHAP extracts exact Shapley impact scores for each 5-minute prediction (`cgm_rolling_mean_30`, `meal_carbs_window_60`, `hr_mean_60`, etc.).
- **Physiological Model**: 
  $$\frac{dG}{dt} = -(p_1 + X)G(t) + p_1 G_b + D(t) - E(t)$$
  $$\frac{dX}{dt} = -p_2 X(t) + p_3 (I(t) - I_b)$$

---

## 📐 Architecture Diagram & Presentation

| Deliverable | File / Format | Description |
| :--- | :--- | :--- |
| **System Architecture Diagram** | [system_architecture.svg](docs/diagrams/system_architecture.svg) | High-resolution scalable vector diagram of all 5 layers |
| **Architecture Printable (PDF/PPT)** | [system_architecture.html](docs/diagrams/system_architecture.html) | Standalone HTML page with one-click **"Print to PDF"** |
| **Presentation Deck (Markdown)** | [presentation_deck.md](docs/presentation/presentation_deck.md) | Complete 11-slide pitch deck covering problem, ML, XAI & outcomes |
| **Presentation Deck (Printable PDF)** | [presentation.html](docs/presentation/presentation.html) | 16:9 slide-formatted viewer with one-click **"Print / Save as PDF"** |

---

## 🚀 Quickstart & Demo
Please refer to [DEMO.md](DEMO.md) for the complete 3-step sequence to launch the entire platform:
```bash
# 1. Start FastAPI Backend (Terminal 1)
.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# 2. Start React Doctor Dashboard (Terminal 2)
cd frontend
npm run dev

# 3. Open Unity 3D Project (Unity Hub)
# Open unity/ -> GlucoTwin-X > Build Final 3D Twin Scene -> Press Play
```

---

## 📄 Open-Source License
This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Limitations & Ethical Disclaimer
- **Research Prototype**: GlucoTwin-X is built as a synthetic composite translational research prototype. It is strictly for academic, research, and benchmarking evaluation and is **not** an approved FDA/CE diagnostic or therapeutic medical device.
- **Cohort Scale**: Dynamic temporal modeling currently leverages 14 validated Type-2 Diabetes patient profiles.
