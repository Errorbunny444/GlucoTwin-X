import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.metrics import roc_auc_score, f1_score, recall_score, precision_score, accuracy_score, average_precision_score
from sklearn.linear_model import Ridge
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
import xgboost as xgb
from typing import Dict, List, Tuple

# --- Feature Groups ---
FEATURES_CGM = [
    'current_glucose', 'glucose_5m_ago', 'glucose_15m_ago', 'glucose_30m_ago', 
    'glucose_60m_ago', 'glucose_120m_ago', 'glucose_change_5m', 'glucose_change_15m', 
    'glucose_change_30m', 'glucose_change_60m', 'slope_30m', 'slope_60m',
    'cgm_mean_15min', 'cgm_std_15min', 'cgm_min_15min', 'cgm_max_15min',
    'cgm_mean_30min', 'cgm_std_30min', 'cgm_min_30min', 'cgm_max_30min',
    'cgm_mean_60min', 'cgm_std_60min', 'cgm_min_60min', 'cgm_max_60min',
    'cgm_mean_120min', 'cgm_std_120min', 'cgm_min_120min', 'cgm_max_120min'
]

FEATURES_MEALS = [
    'minutes_since_last_meal', 'carbohydrate_last_30m', 'carbohydrate_last_60m', 
    'carbohydrate_last_120m', 'carbohydrate_last_180m', 'protein_last_30m', 
    'protein_last_60m', 'protein_last_120m', 'protein_last_180m', 'fat_last_30m', 
    'fat_last_60m', 'fat_last_120m', 'fat_last_180m', 'fiber_last_30m', 
    'fiber_last_60m', 'fiber_last_120m', 'fiber_last_180m', 'calories_last_30m', 
    'calories_last_60m', 'calories_last_120m', 'calories_last_180m', 'carb_exposure',
    'recent_meal_outlier'
]

FEATURES_ACTIVITY = [
    'hr_available', 'current_heart_rate', 'mean_HR_last_15m', 'mean_HR_last_60m', 
    'std_HR_last_60m', 'activity_calories_last_60m', 'activity_calories_last_120m'
]

FEATURES_CIRCADIAN = [
    'hour_of_day', 'sin_hour', 'cos_hour'
]

FEATURES_STATIC_CGMACROS = [
    'age', 'gender', 'bmi', 'hba1c', 'fasting_glucose', 'cholesterol', 'hdl', 'ldl', 
    'triglycerides'
]

FEATURES_STATIC_SYNTHEA = [
    'has_hypertension', 'has_dyslipidemia', 'has_diabetes_medication', 'has_insulin'
]

FEATURES_DYNAMIC = FEATURES_CGM + FEATURES_MEALS + FEATURES_ACTIVITY + FEATURES_CIRCADIAN
FEATURES_STATIC = FEATURES_STATIC_CGMACROS + FEATURES_STATIC_SYNTHEA
FEATURES_FULL = FEATURES_DYNAMIC + FEATURES_STATIC

# Ensure no targets in features
TARGETS = [
    'target_glucose_120m', 'target_peak_glucose_next_120m', 
    'target_high_glucose_120m', 'target_new_high_glucose_event'
]

# --- Evaluator ---
def evaluate_regression(y_true, y_pred) -> Dict[str, float]:
    return {
        'MAE': mean_absolute_error(y_true, y_pred),
        'RMSE': np.sqrt(mean_squared_error(y_true, y_pred)),
        'R2': r2_score(y_true, y_pred)
    }

def evaluate_classification(y_true, y_pred_prob, threshold=0.5) -> Dict[str, float]:
    y_pred = (y_pred_prob >= threshold).astype(int)
    if len(np.unique(y_true)) > 1:
        auroc = roc_auc_score(y_true, y_pred_prob)
        pr_auc = average_precision_score(y_true, y_pred_prob)
    else:
        auroc = np.nan
        pr_auc = np.nan
        
    return {
        'AUROC': auroc,
        'PR_AUC': pr_auc,
        'F1': f1_score(y_true, y_pred, zero_division=0),
        'Recall': recall_score(y_true, y_pred, zero_division=0),
        'Precision': precision_score(y_true, y_pred, zero_division=0),
        'Accuracy': accuracy_score(y_true, y_pred)
    }

# --- Validation Engine ---
def run_group_kfold_regression(df: pd.DataFrame, features: List[str], target: str, model_type: str = 'xgboost'):
    """Run 5-fold GroupKFold for a regression model."""
    gkf = GroupKFold(n_splits=5)
    groups = df['digital_twin_id']
    X = df[features]
    y = df[target]
    
    fold_metrics = []
    oof_preds = np.zeros(len(df))
    
    for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=groups)):
        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
        val_groups = groups.iloc[val_idx].unique().tolist()
        
        if model_type == 'persistence':
            preds = X_val['current_glucose']
        elif model_type == 'ridge':
            model = Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('ridge', Ridge(alpha=1.0))
            ])
            model.fit(X_train, y_train)
            preds = model.predict(X_val)
        elif model_type == 'xgboost':
            model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_train, y_train)
            preds = model.predict(X_val)
            
        metrics = evaluate_regression(y_val, preds)
        metrics['fold'] = fold + 1
        metrics['val_twins'] = val_groups
        metrics['row_count'] = len(X_val)
        fold_metrics.append(metrics)
        oof_preds[val_idx] = preds
        
    agg = {k: np.mean([f[k] for f in fold_metrics]) for k in ['MAE', 'RMSE', 'R2']}
    agg_std = {f"{k}_std": np.std([f[k] for f in fold_metrics]) for k in ['MAE', 'RMSE', 'R2']}
    agg.update(agg_std)
    
    return agg, fold_metrics, oof_preds

def run_group_kfold_classification(df: pd.DataFrame, features: List[str], target: str, model_type: str = 'xgboost'):
    """Run 5-fold GroupKFold for a classification model."""
    gkf = GroupKFold(n_splits=5)
    groups = df['digital_twin_id']
    X = df[features]
    y = df[target]
    
    fold_metrics = []
    oof_probs = np.zeros(len(df))
    
    for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=groups)):
        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
        val_groups = groups.iloc[val_idx].unique().tolist()
        
        if model_type == 'baseline_c0':
            probs = (X_val['current_glucose'] >= 180).astype(float)
        elif model_type == 'xgboost':
            model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                eval_metric='logloss',
                n_jobs=-1
            )
            model.fit(X_train, y_train)
            probs = model.predict_proba(X_val)[:, 1]
            
        metrics = evaluate_classification(y_val, probs)
        metrics['fold'] = fold + 1
        metrics['val_twins'] = val_groups
        metrics['row_count'] = len(X_val)
        fold_metrics.append(metrics)
        oof_probs[val_idx] = probs
        
    agg_keys = ['AUROC', 'PR_AUC', 'F1', 'Recall', 'Precision', 'Accuracy']
    agg = {k: np.mean([f[k] for f in fold_metrics if pd.notna(f[k])]) for k in agg_keys}
    agg_std = {f"{k}_std": np.std([f[k] for f in fold_metrics if pd.notna(f[k])]) for k in agg_keys}
    agg.update(agg_std)
    
    return agg, fold_metrics, oof_probs
