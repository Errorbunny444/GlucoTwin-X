# Final Model Validation Report

## 1. Model Selection
Following rigorous ablation tests, the **XGBoost Dynamic Multimodal** models (R2 and C2) were selected as the primary predictive models for the 120-minute horizon. They demonstrated the strongest out-of-fold generalization, lowering Regression MAE to 29.74 mg/dL and increasing Classification AUROC to 0.916 compared to CGM-only baselines.

## 2. Unseen Patient Generalization
Evaluated using 5-fold GroupKFold by `twin_id`, ensuring the models had never seen the evaluated patient's data during training:
*   **Regression**: MAE = 29.75 mg/dL, RMSE = 40.04 mg/dL
*   **Classification**: AUROC = 0.916, F1 = 0.798, Recall = 0.734, Precision = 0.874

This indicates strong capability to generalize across entirely novel patient physiologies.

## 3. Future-Time Generalization
Evaluated using an 80/20 temporal split per twin, maintaining chronological order to verify forecasting of *known* patients into later periods:
*   **Regression**: MAE = 41.01 mg/dL, RMSE = 52.39 mg/dL
*   **Classification**: AUROC = 0.911, F1 = 0.747, Recall = 0.833, Precision = 0.676

The performance shift indicates that physiological patterns can drift slightly over time even within the same patient, but the overall capability to flag future high-risk events remains highly intact (AUROC 0.911).

## 4. Calibration
The raw XGBoost classification probabilities were compared to a 3-fold cross-fitted Platt (Sigmoid) Calibrated model. 
*   **Raw Brier Score**: 0.1050
*   **Calibrated Brier Score**: 0.1078
Because the raw probabilities were already well-calibrated natively, the explicit calibration step was discarded to prevent unnecessary complexity and slight over-fitting.

## 5. Alert Threshold
Through systematic comparison of decision thresholds [0.4, 0.45, 0.5, 0.55, 0.6], an alert threshold of **0.45** was selected. 
This optimizes the F1 score (0.836) while securing a high Recall (0.790) without catastrophic Precision loss (0.889), ensuring early warning capabilities minimize missed high-glucose events.

## 6. Patient Heterogeneity & Outliers
Performance remains notably diverse across subjects:
*   **Best Twin**: DT-11 (MAE = 20.09 mg/dL)
*   **Worst Twin**: DT-10 (MAE = 37.64 mg/dL)
*   **Representative Twin**: DT-01 (MAE = 30.01 mg/dL) provides a balanced mix of typical glucose behavior.

**Outlier Stress Test**: The 761g carbohydrate meal (DT-03) had a local subset MAE of 13.04 mg/dL, indicating the model managed this extreme physiological stress test remarkably well, largely due to the robust historical lag features.

## 7. Static EHR Finding & Architecture
With only 14 dynamic T2D subjects available, feeding static patient attributes directly into the global XGBoost model degraded generalization by forcing patient-memorization. 

Consequently, the final GlucoTwin-X architecture strictly segments responsibility:
1.  **Predictive Layer**: Only uses dynamic multimodal time-series (CGM, meals, activity, circadian context) for safe, generalizable short-horizon forecasting.
2.  **Digital Twin Context Layer**: Leverages static EHR and baseline metrics for personalization, physiological simulation, and explainability.

## 8. Limitations
1.  **Sample Size**: The dataset contains only 14 unique dynamic T2D subjects.
2.  **Duration**: Models are trained on approximately 7-19 days per participant. 
3.  **Nature of Data**: This relies on synthetic composite EHR enrichments matched to real dynamic data. It represents a robust research/competition prototype, not an FDA-approved clinical diagnostic system.
