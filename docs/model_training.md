# Digital Twin Predictive Modeling Report

## 1. Prediction Tasks
The predictive modeling pipeline is tasked with two goals for a 120-minute horizon:
*   **Regression**: Predict the exact continuous value of glucose exactly 120 minutes into the future (`target_glucose_120m`).
*   **Classification**: Predict whether the subject will experience a high-glucose event (>= 180 mg/dL) at any point during the future 120-minute window (`target_high_glucose_120m`).

## 2. Baselines
To ensure model complexity actually adds value, basic physiological and simple ML baselines are enforced:
*   **Persistence (Regression)**: Assumes glucose at 120m equals current glucose.
*   **Ridge (Regression)**: Simple linear regression over the CGM history.
*   **Threshold Rule (Classification)**: Assumes a high-glucose event happens if the current glucose is already >= 180 mg/dL.

## 3. Validation Strategy
Because multiple rows belong to the same physiological Twin, random shuffling inherently leaks patient-specific behavior. Evaluation strictly relies on **5-fold GroupKFold by `twin_id`**. This measures whether the model generalizes to an *unseen* patient, rather than memorizing adjacent minutes from the same patient.

## 4. Ablation Study: Does Fusion Add Value?
Features were structured sequentially:
*   **Set A (CGM Only)**: Validates how well glucose history auto-predicts itself.
*   **Set B (Dynamic Multimodal)**: Adds meals, activity, and circadian context.
*   **Set C (Full Fusion)**: Adds the baseline physiological and Synthea EHR static covariates.

### Fusion Value Findings
*   **Did Dynamic Multimodal data improve over CGM-only?**
    **Yes, significantly.** For XGBoost Regression, moving from CGM-only to Dynamic Multimodal reduced MAE from 31.55 mg/dL to 29.75 mg/dL. For classification, AUROC improved dramatically from 0.856 to 0.916.
*   **Did Static + Dynamic Fusion improve further?**
    **No, it degraded generalization.** Because there are only 14 unique twins, static variables act as patient-level constants. XGBoost splits on these constants to explicitly "memorize" patients in the training fold, which backfires during GroupKFold validation on hold-out patients. The MAE for the Full Fusion model increased to 32.55 mg/dL. This underscores the need for larger subject cohorts to effectively learn static-to-dynamic relationships without overfitting.

## 5. Patient Heterogeneity
Performance varies substantially across the 14 subjects:
*   **Best Performing Twin**: `DT-11` (MAE: ~21.85 mg/dL)
*   **Worst Performing Twin**: `DT-07` (MAE: ~39.90 mg/dL)
This 18-point gap illustrates that physiological volatility is highly personalized. A "good" average score obscures the fact that some digital twins are fundamentally harder to predict.

## 6. Meal Outlier Robustness
The dataset retains a verified physiological outlier (761g carbohydrate meal for DT-03). A sensitivity check on the Full Fusion OOF predictions revealed:
*   MAE including all data: 32.96 mg/dL
*   MAE excluding windows near the outlier: 32.97 mg/dL
The outlier did not materially contaminate global performance. XGBoost remained robust.

## 7. Metrics Summary
Evaluated through 5-fold GroupKFold.

### Regression
*   **Persistence**: MAE 35.02
*   **Ridge (CGM)**: MAE 31.67
*   **XGBoost R1 (CGM)**: MAE 31.55
*   **XGBoost R2 (Dynamic)**: MAE 29.74 (Best)
*   **XGBoost R3 (Fusion)**: MAE 32.55

### Classification
*   **Baseline C0**: AUROC 0.775
*   **XGBoost C1 (CGM)**: AUROC 0.856
*   **XGBoost C2 (Dynamic)**: AUROC 0.916 (Best)
*   **XGBoost C3 (Fusion)**: AUROC 0.911

## 8. Limitations
Only 14 Type-2 Diabetes subjects are available in the current dataset. Full Fusion evaluation requires more subjects for static patient metadata to serve as generalizable physiological anchors instead of memorization identifiers.
