import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import xgboost as xgb
import datetime
from sklearn.model_selection import GroupKFold

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.glucotwin.models.glucose_models import (
    FEATURES_CGM, FEATURES_DYNAMIC, FEATURES_FULL, TARGETS,
    run_group_kfold_regression, run_group_kfold_classification,
    evaluate_regression, evaluate_classification
)

def check_leakage(df):
    all_features = FEATURES_FULL
    for tgt in TARGETS:
        if tgt in all_features:
            raise ValueError(f"Leakage detected: {tgt} is in features list!")

def main():
    print("Starting Model Training...")
    processed_dir = project_root / "data" / "processed"
    artifacts_dir = project_root / "artifacts"
    models_dir = artifacts_dir / "models"
    plots_dir = artifacts_dir / "plots"
    
    models_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    # Load dataset
    ds_path = processed_dir / "glucose_forecasting_dataset.parquet"
    df = pd.read_parquet(ds_path)
    
    check_leakage(df)
    
    print(f"Loaded {len(df)} rows.")
    
    # Ensure boolean/categorical are float for XGBoost
    if 'gender' in df.columns:
        df['gender'] = df['gender'].map({'M': 1.0, 'F': 0.0, 'Male': 1.0, 'Female': 0.0, 1: 1.0, 0: 0.0}).astype(float)
        
    for col in FEATURES_FULL:
        if str(df[col].dtype) in ['object', 'string', 'bool']:
            try:
                df[col] = df[col].astype(float)
            except ValueError:
                pass
            
    # --- Regression ---
    print("\n--- Regression ---")
    reg_tgt = 'target_glucose_120m'
    
    print("Running Persistence Baseline...")
    agg_pers, fold_pers, oof_pers = run_group_kfold_regression(df, FEATURES_CGM, reg_tgt, 'persistence')
    
    print("Running Ridge (CGM)...")
    agg_ridge, fold_ridge, oof_ridge = run_group_kfold_regression(df, FEATURES_CGM, reg_tgt, 'ridge')
    
    print("Running XGBoost R1 (CGM)...")
    agg_xgb_r1, fold_xgb_r1, oof_xgb_r1 = run_group_kfold_regression(df, FEATURES_CGM, reg_tgt, 'xgboost')
    
    print("Running XGBoost R2 (Dynamic Multimodal)...")
    agg_xgb_r2, fold_xgb_r2, oof_xgb_r2 = run_group_kfold_regression(df, FEATURES_DYNAMIC, reg_tgt, 'xgboost')
    
    print("Running XGBoost R3 (Full Digital Twin Fusion)...")
    agg_xgb_r3, fold_xgb_r3, oof_xgb_r3 = run_group_kfold_regression(df, FEATURES_FULL, reg_tgt, 'xgboost')
    
    # --- Classification ---
    print("\n--- Classification ---")
    clf_tgt = 'target_high_glucose_120m'
    
    print("Running Baseline C0 (Current Glucose >= 180)...")
    agg_c0, fold_c0, oof_c0 = run_group_kfold_classification(df, FEATURES_CGM, clf_tgt, 'baseline_c0')
    
    print("Running XGBoost C1 (CGM)...")
    agg_c1, fold_c1, oof_c1 = run_group_kfold_classification(df, FEATURES_CGM, clf_tgt, 'xgboost')
    
    print("Running XGBoost C2 (Dynamic Multimodal)...")
    agg_c2, fold_c2, oof_c2 = run_group_kfold_classification(df, FEATURES_DYNAMIC, clf_tgt, 'xgboost')
    
    print("Running XGBoost C3 (Full Digital Twin Fusion)...")
    agg_c3, fold_c3, oof_c3 = run_group_kfold_classification(df, FEATURES_FULL, clf_tgt, 'xgboost')
    
    # --- OOF Evaluation for Meal Outliers ---
    print("\nEvaluating Meal Outliers...")
    mask_no_outlier = df['recent_meal_outlier'] == 0
    metrics_r3_clean = evaluate_regression(df[mask_no_outlier][reg_tgt], oof_xgb_r3[mask_no_outlier])
    metrics_r3_all = evaluate_regression(df[reg_tgt], oof_xgb_r3)
    
    # --- Train Candidate Models on All Data ---
    print("\nTraining Candidate Models on Full Dataset...")
    reg_candidate = xgb.XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1)
    reg_candidate.fit(df[FEATURES_FULL], df[reg_tgt])
    reg_candidate.save_model(models_dir / "xgb_glucose_regressor_candidate.json")
    
    clf_candidate = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric='logloss', use_label_encoder=False, n_jobs=-1)
    clf_candidate.fit(df[FEATURES_FULL], df[clf_tgt])
    clf_candidate.save_model(models_dir / "xgb_high_glucose_classifier_candidate.json")
    
    # --- Save Metadata ---
    metadata = {
        "model_type": "XGBoost",
        "training_timestamp": datetime.datetime.now().isoformat(),
        "feature_set": "Full Digital Twin Fusion",
        "number_of_training_rows": len(df),
        "number_of_twins": df['digital_twin_id'].nunique(),
        "hyperparameters": {
            "n_estimators": 100,
            "max_depth": 4,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8
        },
        "forecast_horizon": "120 minutes",
        "prediction_stride": "5 minutes",
        "cross_validation_strategy": "5-fold GroupKFold by twin_id",
        "metrics_summary": {
            "Regression_MAE": agg_xgb_r3['MAE'],
            "Classification_AUROC": agg_c3['AUROC']
        },
        "dataset_path": "data/processed/glucose_forecasting_dataset.parquet"
    }
    with open(models_dir / "model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
        
    # --- Save OOF Predictions ---
    print("Saving OOF Predictions...")
    oof_df = df[['digital_twin_id', 'prediction_timestamp', reg_tgt, clf_tgt]].copy()
    oof_df['predicted_glucose_120m'] = oof_xgb_r3
    oof_df['predicted_high_glucose_probability'] = oof_c3
    oof_df['predicted_high_glucose_class'] = (oof_c3 >= 0.5).astype(int)
    
    gkf = GroupKFold(n_splits=5)
    oof_df['fold'] = -1
    for fold, (_, val_idx) in enumerate(gkf.split(df[FEATURES_FULL], df[reg_tgt], groups=df['digital_twin_id'])):
        oof_df.loc[val_idx, 'fold'] = fold + 1
    
    oof_df.to_parquet(processed_dir / "model_oof_predictions.parquet", index=False)
    
    # --- Save Report ---
    report = {
        "regression": {
            "Persistence": agg_pers,
            "Ridge": agg_ridge,
            "XGBoost_R1_CGM": agg_xgb_r1,
            "XGBoost_R2_Dynamic": agg_xgb_r2,
            "XGBoost_R3_Fusion": agg_xgb_r3
        },
        "classification": {
            "Baseline_C0": agg_c0,
            "XGBoost_C1_CGM": agg_c1,
            "XGBoost_C2_Dynamic": agg_c2,
            "XGBoost_C3_Fusion": agg_c3
        },
        "outlier_sensitivity": {
            "MAE_All_Data": metrics_r3_all['MAE'],
            "MAE_No_Outliers": metrics_r3_clean['MAE']
        },
        "features": {
            "CGM": len(FEATURES_CGM),
            "Dynamic": len(FEATURES_DYNAMIC),
            "Full_Fusion": len(FEATURES_FULL)
        }
    }
    
    per_twin_metrics = {}
    for dt in df['digital_twin_id'].unique():
        mask = df['digital_twin_id'] == dt
        y_true_reg = df.loc[mask, reg_tgt]
        y_pred_reg = oof_xgb_r3[mask]
        reg_m = evaluate_regression(y_true_reg, y_pred_reg)
        
        y_true_clf = df.loc[mask, clf_tgt]
        y_pred_clf = oof_c3[mask]
        clf_m = evaluate_classification(y_true_clf, y_pred_clf)
        
        # Convert nan to None for JSON
        for k, v in clf_m.items():
            if pd.isna(v): clf_m[k] = None
        for k, v in reg_m.items():
            if pd.isna(v): reg_m[k] = None
            
        per_twin_metrics[dt] = {
            "MAE": reg_m['MAE'],
            "RMSE": reg_m['RMSE'],
            "AUROC": clf_m['AUROC'],
            "F1": clf_m['F1'],
            "Recall": clf_m['Recall'],
            "Precision": clf_m['Precision']
        }
    report['per_twin_metrics'] = per_twin_metrics
    
    with open(artifacts_dir / "model_training_report.json", "w") as f:
        json.dump(report, f, indent=4)
        
    # --- Generate Plots ---
    plt.figure(figsize=(6,6))
    plt.scatter(oof_df[reg_tgt], oof_df['predicted_glucose_120m'], alpha=0.1)
    plt.plot([0, 400], [0, 400], 'r--')
    plt.xlabel('Actual Glucose 120m')
    plt.ylabel('Predicted Glucose 120m')
    plt.title('Actual vs Predicted Glucose (Full Fusion OOF)')
    plt.savefig(plots_dir / "plot1_actual_vs_predicted.png")
    plt.close()
    
    residuals = oof_df[reg_tgt] - oof_df['predicted_glucose_120m']
    plt.figure(figsize=(8,5))
    plt.hist(residuals, bins=50, edgecolor='black')
    plt.title('Residuals Distribution')
    plt.savefig(plots_dir / "plot2_residuals.png")
    plt.close()
    
    twins = list(per_twin_metrics.keys())
    maes = [per_twin_metrics[t]['MAE'] for t in twins]
    plt.figure(figsize=(10,5))
    plt.bar(twins, maes)
    plt.title('MAE by Digital Twin')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(plots_dir / "plot3_mae_by_twin.png")
    plt.close()
    
    models = ['Persistence', 'Ridge', 'XGB R1 (CGM)', 'XGB R2 (Dyn)', 'XGB R3 (Full)']
    mae_vals = [agg_pers['MAE'], agg_ridge['MAE'], agg_xgb_r1['MAE'], agg_xgb_r2['MAE'], agg_xgb_r3['MAE']]
    plt.figure(figsize=(8,5))
    plt.bar(models, mae_vals, color=['grey', 'grey', 'blue', 'orange', 'green'])
    plt.title('Model Comparison: MAE')
    plt.ylabel('Mean Absolute Error (mg/dL)')
    plt.savefig(plots_dir / "plot4_model_comparison_mae.png")
    plt.close()

    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve(oof_df[clf_tgt], oof_df['predicted_high_glucose_probability'])
    plt.figure(figsize=(6,6))
    plt.plot(fpr, tpr)
    plt.plot([0,1],[0,1], 'r--')
    plt.title('ROC Curve (Full Fusion OOF)')
    plt.savefig(plots_dir / "plot5_roc_curve.png")
    plt.close()

    from sklearn.metrics import precision_recall_curve
    prec, rec, _ = precision_recall_curve(oof_df[clf_tgt], oof_df['predicted_high_glucose_probability'])
    plt.figure(figsize=(6,6))
    plt.plot(rec, prec)
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve (Full Fusion OOF)')
    plt.savefig(plots_dir / "plot6_pr_curve.png")
    plt.close()
    
    f1s = [per_twin_metrics[t]['F1'] if per_twin_metrics[t]['F1'] is not None else 0 for t in twins]
    recs = [per_twin_metrics[t]['Recall'] if per_twin_metrics[t]['Recall'] is not None else 0 for t in twins]
    x = np.arange(len(twins))
    plt.figure(figsize=(12,5))
    plt.bar(x - 0.2, f1s, 0.4, label='F1')
    plt.bar(x + 0.2, recs, 0.4, label='Recall')
    plt.xticks(x, twins, rotation=45)
    plt.legend()
    plt.title('F1 and Recall by Twin')
    plt.tight_layout()
    plt.savefig(plots_dir / "plot7_f1_recall_by_twin.png")
    plt.close()

    print("Completed script.")
    
if __name__ == '__main__':
    main()
