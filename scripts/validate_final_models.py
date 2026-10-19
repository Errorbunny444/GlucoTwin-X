import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import xgboost as xgb
import datetime
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    roc_auc_score, f1_score, recall_score, precision_score, accuracy_score, average_precision_score, brier_score_loss, roc_curve, precision_recall_curve
)

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.glucotwin.models.glucose_models import FEATURES_DYNAMIC

def get_regression_metrics(y_true, y_pred):
    return {
        'MAE': mean_absolute_error(y_true, y_pred),
        'RMSE': np.sqrt(mean_squared_error(y_true, y_pred)),
        'R2': r2_score(y_true, y_pred)
    }

def get_classification_metrics(y_true, y_prob, threshold=0.5):
    y_pred = (y_prob >= threshold).astype(int)
    if len(np.unique(y_true)) > 1:
        auroc = roc_auc_score(y_true, y_prob)
        pr_auc = average_precision_score(y_true, y_prob)
        brier = brier_score_loss(y_true, y_prob)
    else:
        auroc = np.nan
        pr_auc = np.nan
        brier = np.nan
        
    return {
        'AUROC': auroc,
        'PR_AUC': pr_auc,
        'F1': f1_score(y_true, y_pred, zero_division=0),
        'Recall': recall_score(y_true, y_pred, zero_division=0),
        'Precision': precision_score(y_true, y_pred, zero_division=0),
        'Accuracy': accuracy_score(y_true, y_pred),
        'Brier': brier
    }

def main():
    print("Starting Rigorous Validation...")
    processed_dir = project_root / "data" / "processed"
    artifacts_dir = project_root / "artifacts"
    models_dir = artifacts_dir / "models"
    plots_dir = artifacts_dir / "plots" / "final_validation"
    
    plots_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_parquet(processed_dir / "glucose_forecasting_dataset.parquet")
    
    # Sort chronologically just in case
    df = df.sort_values(by=['digital_twin_id', 'prediction_timestamp']).reset_index(drop=True)
    
    features = FEATURES_DYNAMIC
    reg_tgt = 'target_glucose_120m'
    clf_tgt = 'target_high_glucose_120m'
    
    # Float conversion
    if 'gender' in df.columns:
        df['gender'] = df['gender'].map({'M': 1.0, 'F': 0.0, 'Male': 1.0, 'Female': 0.0, 1: 1.0, 0: 0.0}).astype(float)
    for col in features:
        if str(df[col].dtype) in ['object', 'string', 'bool']:
            try:
                df[col] = df[col].astype(float)
            except ValueError:
                pass

    X = df[features]
    y_reg = df[reg_tgt]
    y_clf = df[clf_tgt]
    groups = df['digital_twin_id']
    
    # ---------------------------------------------------------
    # 1. Validation A: Unseen Patient Generalization
    # ---------------------------------------------------------
    print("Validation A: GroupKFold...")
    gkf = GroupKFold(n_splits=5)
    
    val_a_reg_metrics = []
    val_a_clf_metrics = []
    
    oof_preds_reg = np.zeros(len(df))
    oof_probs_clf_raw = np.zeros(len(df))
    oof_probs_clf_cal = np.zeros(len(df))
    
    base_xgb_reg = xgb.XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1)
    base_xgb_clf = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric='logloss', n_jobs=-1)
    
    # We will also use CalibratedClassifierCV inside CV for cross-fitting
    calibrated_clf = CalibratedClassifierCV(estimator=base_xgb_clf, method='sigmoid', cv=3)
    
    for train_idx, val_idx in gkf.split(X, y_reg, groups=groups):
        X_train, y_train_reg, y_train_clf = X.iloc[train_idx], y_reg.iloc[train_idx], y_clf.iloc[train_idx]
        X_val, y_val_reg, y_val_clf = X.iloc[val_idx], y_reg.iloc[val_idx], y_clf.iloc[val_idx]
        
        # Regression
        reg_model = xgb.XGBRegressor(**base_xgb_reg.get_params())
        reg_model.fit(X_train, y_train_reg)
        preds = reg_model.predict(X_val)
        oof_preds_reg[val_idx] = preds
        val_a_reg_metrics.append(get_regression_metrics(y_val_reg, preds))
        
        # Classification (Raw)
        clf_model = xgb.XGBClassifier(**base_xgb_clf.get_params())
        clf_model.fit(X_train, y_train_clf)
        probs_raw = clf_model.predict_proba(X_val)[:, 1]
        oof_probs_clf_raw[val_idx] = probs_raw
        
        # Classification (Calibrated) - Fit on train only, avoiding leakage
        cal_model = CalibratedClassifierCV(estimator=xgb.XGBClassifier(**base_xgb_clf.get_params()), method='sigmoid', cv=3)
        cal_model.fit(X_train, y_train_clf)
        probs_cal = cal_model.predict_proba(X_val)[:, 1]
        oof_probs_clf_cal[val_idx] = probs_cal
        
        val_a_clf_metrics.append(get_classification_metrics(y_val_clf, probs_raw))
        
    agg_val_a_reg = {k: np.mean([f[k] for f in val_a_reg_metrics]) for k in val_a_reg_metrics[0].keys()}
    agg_val_a_clf = {k: np.mean([f[k] for f in val_a_clf_metrics]) for k in val_a_clf_metrics[0].keys()}
    
    # Global Brier score
    brier_raw = brier_score_loss(y_clf, oof_probs_clf_raw)
    brier_cal = brier_score_loss(y_clf, oof_probs_clf_cal)
    print(f"Brier Raw: {brier_raw:.4f}, Brier Calibrated: {brier_cal:.4f}")
    
    # We will use raw probabilities if calibration doesn't improve significantly.
    use_calibration = brier_cal < brier_raw
    oof_probs_clf = oof_probs_clf_cal if use_calibration else oof_probs_clf_raw
    
    # ---------------------------------------------------------
    # 2. Alert Threshold Selection
    # ---------------------------------------------------------
    print("Selecting Alert Threshold...")
    thresholds = [0.40, 0.45, 0.50, 0.55, 0.60]
    best_thresh = 0.5
    best_f1 = -1
    thresh_results = {}
    for t in thresholds:
        m = get_classification_metrics(y_clf, oof_probs_clf, threshold=t)
        thresh_results[t] = m
        if m['F1'] > best_f1:
            best_f1 = m['F1']
            best_thresh = t
            
    print(f"Selected Threshold: {best_thresh} (F1: {best_f1:.4f})")
    
    # ---------------------------------------------------------
    # 3. Regression Uncertainty (Empirical 90% PI)
    # ---------------------------------------------------------
    residuals = y_reg - oof_preds_reg
    lower_q = np.percentile(residuals, 5)
    upper_q = np.percentile(residuals, 95)
    
    oof_lower = oof_preds_reg + lower_q
    oof_upper = oof_preds_reg + upper_q
    
    # Coverage
    coverage = np.mean((y_reg >= oof_lower) & (y_reg <= oof_upper))
    print(f"90% PI Coverage: {coverage:.4f}")
    
    # ---------------------------------------------------------
    # 4. Validation B: Future-Time Generalization (80/20)
    # ---------------------------------------------------------
    print("Validation B: Future-Time Temporal Holdout...")
    train_idx_temp = []
    val_idx_temp = []
    
    for dt in df['digital_twin_id'].unique():
        idx = df[df['digital_twin_id'] == dt].index.values
        split_point = int(len(idx) * 0.8)
        train_idx_temp.extend(idx[:split_point])
        val_idx_temp.extend(idx[split_point:])
        
    X_train_t, y_train_reg_t, y_train_clf_t = X.iloc[train_idx_temp], y_reg.iloc[train_idx_temp], y_clf.iloc[train_idx_temp]
    X_val_t, y_val_reg_t, y_val_clf_t = X.iloc[val_idx_temp], y_reg.iloc[val_idx_temp], y_clf.iloc[val_idx_temp]
    
    temp_reg_model = xgb.XGBRegressor(**base_xgb_reg.get_params())
    temp_reg_model.fit(X_train_t, y_train_reg_t)
    temp_preds_reg = temp_reg_model.predict(X_val_t)
    
    temp_clf_model = xgb.XGBClassifier(**base_xgb_clf.get_params())
    if use_calibration:
        temp_clf_model = CalibratedClassifierCV(estimator=xgb.XGBClassifier(**base_xgb_clf.get_params()), method='sigmoid', cv=3)
    temp_clf_model.fit(X_train_t, y_train_clf_t)
    temp_probs_clf = temp_clf_model.predict_proba(X_val_t)[:, 1]
    
    val_b_reg = get_regression_metrics(y_val_reg_t, temp_preds_reg)
    val_b_clf = get_classification_metrics(y_val_clf_t, temp_probs_clf, threshold=best_thresh)
    
    # ---------------------------------------------------------
    # 5. New-Event Subset Evaluation (Current < 180)
    # ---------------------------------------------------------
    print("Evaluating New-Event Subset...")
    new_event_mask = df['current_glucose'] < 180
    new_event_metrics = get_classification_metrics(y_clf[new_event_mask], oof_probs_clf[new_event_mask], threshold=best_thresh)
    
    # ---------------------------------------------------------
    # 6. Error Analysis
    # ---------------------------------------------------------
    print("Performing Error Analysis...")
    err_analysis = {}
    
    # By Glucose Range
    mask_low = y_reg < 70
    mask_norm = (y_reg >= 70) & (y_reg < 180)
    mask_high = y_reg >= 180
    
    err_analysis['Range_<70'] = get_regression_metrics(y_reg[mask_low], oof_preds_reg[mask_low]) if sum(mask_low) > 0 else {}
    err_analysis['Range_70_180'] = get_regression_metrics(y_reg[mask_norm], oof_preds_reg[mask_norm]) if sum(mask_norm) > 0 else {}
    err_analysis['Range_>=180'] = get_regression_metrics(y_reg[mask_high], oof_preds_reg[mask_high]) if sum(mask_high) > 0 else {}
    err_analysis['Range_<70']['count'] = int(sum(mask_low))
    err_analysis['Range_70_180']['count'] = int(sum(mask_norm))
    err_analysis['Range_>=180']['count'] = int(sum(mask_high))
    
    # Around Meals
    mask_meal_none = df['minutes_since_last_meal'] > 120
    mask_meal_60 = df['minutes_since_last_meal'] <= 60
    mask_meal_120 = (df['minutes_since_last_meal'] > 60) & (df['minutes_since_last_meal'] <= 120)
    
    err_analysis['Meal_None'] = get_regression_metrics(y_reg[mask_meal_none], oof_preds_reg[mask_meal_none])
    err_analysis['Meal_<=60'] = get_regression_metrics(y_reg[mask_meal_60], oof_preds_reg[mask_meal_60])
    err_analysis['Meal_60_120'] = get_regression_metrics(y_reg[mask_meal_120], oof_preds_reg[mask_meal_120])
    
    # HR Missingness
    mask_hr_1 = df['hr_available'] == 1
    mask_hr_0 = df['hr_available'] == 0
    err_analysis['HR_Avail_1'] = get_regression_metrics(y_reg[mask_hr_1], oof_preds_reg[mask_hr_1])
    err_analysis['HR_Avail_0'] = get_regression_metrics(y_reg[mask_hr_0], oof_preds_reg[mask_hr_0]) if sum(mask_hr_0) > 0 else {}
    
    # Extreme Meal Stress Test (Outliers)
    mask_outlier = df['recent_meal_outlier'] == 1
    err_analysis['Extreme_Meal'] = get_regression_metrics(y_reg[mask_outlier], oof_preds_reg[mask_outlier]) if sum(mask_outlier) > 0 else {}
    
    # ---------------------------------------------------------
    # 7. Per-Twin Error Table
    # ---------------------------------------------------------
    per_twin_metrics = {}
    for dt in df['digital_twin_id'].unique():
        mask = df['digital_twin_id'] == dt
        rm = get_regression_metrics(y_reg[mask], oof_preds_reg[mask])
        cm = get_classification_metrics(y_clf[mask], oof_probs_clf[mask], threshold=best_thresh)
        prev = y_clf[mask].mean()
        per_twin_metrics[dt] = {
            'count': int(sum(mask)),
            'MAE': rm['MAE'],
            'RMSE': rm['RMSE'],
            'AUROC': cm['AUROC'],
            'F1': cm['F1'],
            'Recall': cm['Recall'],
            'Precision': cm['Precision'],
            'high_glucose_prevalence': prev
        }
        
    # ---------------------------------------------------------
    # 8. Retrain Final Models & Save
    # ---------------------------------------------------------
    print("Retraining Final Models on Full Data...")
    final_reg = xgb.XGBRegressor(**base_xgb_reg.get_params())
    final_reg.fit(X, y_reg)
    final_reg.save_model(models_dir / "glucose_regressor_final.json")
    
    final_clf = xgb.XGBClassifier(**base_xgb_clf.get_params())
    if use_calibration:
        final_clf = CalibratedClassifierCV(estimator=xgb.XGBClassifier(**base_xgb_clf.get_params()), method='sigmoid', cv=3)
    final_clf.fit(X, y_clf)
    
    import pickle
    with open(models_dir / "high_glucose_classifier_final.pkl", "wb") as f:
        pickle.dump(final_clf, f)
        
    # Metadata
    metadata = {
        "features": features,
        "feature_order": features,
        "chosen_threshold": best_thresh,
        "prediction_horizon": "120m",
        "lookback": "120m",
        "validation_strategy_A": "5-fold GroupKFold by twin_id",
        "validation_strategy_B": "80/20 Temporal Holdout per twin",
        "training_row_count": len(df),
        "twin_count": df['digital_twin_id'].nunique(),
        "uncertainty_method": "Empirical Residual-Based Prediction Interval",
        "prediction_interval_bounds": {"lower_residual": float(lower_q), "upper_residual": float(upper_q)},
        "calibration_used": bool(use_calibration)
    }
    with open(models_dir / "final_model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
        
    # ---------------------------------------------------------
    # 9. Save Predictions
    # ---------------------------------------------------------
    oof_df = df[['digital_twin_id', 'prediction_timestamp', reg_tgt, clf_tgt]].copy()
    oof_df['actual_glucose'] = y_reg
    oof_df['predicted_glucose'] = oof_preds_reg
    oof_df['lower_interval'] = oof_lower
    oof_df['upper_interval'] = oof_upper
    oof_df['actual_high_glucose'] = y_clf
    oof_df['predicted_probability'] = oof_probs_clf
    oof_df['predicted_alert'] = (oof_probs_clf >= best_thresh).astype(int)
    oof_df['validation_strategy'] = 'GroupKFold'
    
    oof_df.to_parquet(processed_dir / "final_validation_predictions.parquet", index=False)
    
    # ---------------------------------------------------------
    # 10. Generate Plots
    # ---------------------------------------------------------
    print("Generating Plots...")
    # Plot 1: Actual vs Pred
    plt.figure(figsize=(6,6))
    plt.scatter(y_reg, oof_preds_reg, alpha=0.1)
    plt.plot([0, 400], [0, 400], 'r--')
    plt.title('Actual vs Predicted Glucose (OOF)')
    plt.savefig(plots_dir / "1_actual_vs_predicted.png")
    plt.close()
    
    # Plot 2: Residuals
    plt.figure(figsize=(8,5))
    plt.hist(residuals, bins=50, edgecolor='black')
    plt.title('Residual Distribution')
    plt.savefig(plots_dir / "2_residuals.png")
    plt.close()
    
    # Plot 3: MAE by Twin
    twins = list(per_twin_metrics.keys())
    maes = [per_twin_metrics[t]['MAE'] for t in twins]
    plt.figure(figsize=(10,5))
    plt.bar(twins, maes)
    plt.title('MAE by Twin')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(plots_dir / "3_mae_by_twin.png")
    plt.close()
    
    # Plot 4: Temporal holdout (DT-01)
    dt01_val_idx = [i for i, idx in enumerate(val_idx_temp) if df.iloc[idx]['digital_twin_id'] == 'DT-01']
    if len(dt01_val_idx) > 0:
        dt01_y = y_val_reg_t.iloc[dt01_val_idx]
        dt01_p = temp_preds_reg[dt01_val_idx]
        plt.figure(figsize=(12,5))
        plt.plot(dt01_y.values, label='Actual')
        plt.plot(dt01_p, label='Predicted', alpha=0.7)
        plt.title('Temporal Holdout: DT-01')
        plt.legend()
        plt.savefig(plots_dir / "4_temporal_holdout_dt01.png")
        plt.close()
        
    # Plot 5: Prediction Interval Example (Subset of DT-01)
    if len(dt01_val_idx) > 0:
        sub_y = dt01_y.values[:200]
        sub_p = dt01_p[:200]
        plt.figure(figsize=(12,5))
        plt.plot(sub_y, label='Actual')
        plt.plot(sub_p, label='Predicted')
        plt.fill_between(range(len(sub_p)), sub_p + lower_q, sub_p + upper_q, alpha=0.2, label='90% PI')
        plt.title('Prediction Interval Example')
        plt.legend()
        plt.savefig(plots_dir / "5_prediction_interval.png")
        plt.close()
        
    # Plot 6: ROC
    fpr, tpr, _ = roc_curve(y_clf, oof_probs_clf)
    plt.figure(figsize=(6,6))
    plt.plot(fpr, tpr)
    plt.plot([0,1],[0,1], 'r--')
    plt.title('ROC Curve')
    plt.savefig(plots_dir / "6_roc_curve.png")
    plt.close()
    
    # Plot 7: PR
    prec, rec, _ = precision_recall_curve(y_clf, oof_probs_clf)
    plt.figure(figsize=(6,6))
    plt.plot(rec, prec)
    plt.title('PR Curve')
    plt.savefig(plots_dir / "7_pr_curve.png")
    plt.close()
    
    # Plot 8: Calibration Curve
    prob_true, prob_pred = calibration_curve(y_clf, oof_probs_clf, n_bins=10)
    plt.figure(figsize=(6,6))
    plt.plot(prob_pred, prob_true, marker='o')
    plt.plot([0,1],[0,1], 'r--')
    plt.title('Calibration/Reliability Curve')
    plt.savefig(plots_dir / "8_calibration.png")
    plt.close()
    
    # Plot 9: Threshold Trade-off
    ts = list(thresh_results.keys())
    rs = [thresh_results[t]['Recall'] for t in ts]
    ps = [thresh_results[t]['Precision'] for t in ts]
    fs = [thresh_results[t]['F1'] for t in ts]
    plt.figure(figsize=(8,5))
    plt.plot(ts, rs, label='Recall', marker='o')
    plt.plot(ts, ps, label='Precision', marker='o')
    plt.plot(ts, fs, label='F1', marker='o')
    plt.title('Threshold Trade-off')
    plt.legend()
    plt.savefig(plots_dir / "9_threshold_tradeoff.png")
    plt.close()
    
    # Plot 10: F1/Recall by Twin
    f1s = [per_twin_metrics[t]['F1'] for t in twins]
    recs = [per_twin_metrics[t]['Recall'] for t in twins]
    x = np.arange(len(twins))
    plt.figure(figsize=(12,5))
    plt.bar(x - 0.2, f1s, 0.4, label='F1')
    plt.bar(x + 0.2, recs, 0.4, label='Recall')
    plt.xticks(x, twins, rotation=45)
    plt.title('F1 & Recall by Twin')
    plt.legend()
    plt.tight_layout()
    plt.savefig(plots_dir / "10_f1_recall_by_twin.png")
    plt.close()
    
    # ---------------------------------------------------------
    # 11. Final Validation Report
    # ---------------------------------------------------------
    def clean_nan(d):
        for k, v in d.items():
            if isinstance(v, dict):
                clean_nan(v)
            elif pd.isna(v):
                d[k] = None
                
    report = {
        "validation_A_unseen_patient": {
            "regression": agg_val_a_reg,
            "classification": agg_val_a_clf
        },
        "validation_B_future_time": {
            "regression": val_b_reg,
            "classification": val_b_clf
        },
        "calibration": {
            "used": bool(use_calibration),
            "brier_raw": float(brier_raw),
            "brier_calibrated": float(brier_cal)
        },
        "threshold": {
            "selected": float(best_thresh),
            "metrics": thresh_results[best_thresh]
        },
        "new_event_subset": new_event_metrics,
        "error_analysis": err_analysis,
        "prediction_interval": {
            "lower_offset": float(lower_q),
            "upper_offset": float(upper_q),
            "coverage": float(coverage)
        },
        "per_twin_metrics": per_twin_metrics
    }
    
    clean_nan(report)
    
    with open(artifacts_dir / "final_model_validation_report.json", "w") as f:
        json.dump(report, f, indent=4)
        
    print("Completed Rigorous Validation.")

if __name__ == '__main__':
    main()
