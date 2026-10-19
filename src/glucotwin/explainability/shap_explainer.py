import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import json
import shap
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).resolve().parent.parent.parent.parent

# Human readable names for features
FEATURE_LABELS = {
    "current_glucose": "Current glucose",
    "glucose_5m_ago": "Glucose 5 minutes ago",
    "glucose_15m_ago": "Glucose 15 minutes ago",
    "glucose_30m_ago": "Glucose 30 minutes ago",
    "glucose_60m_ago": "Glucose 1 hour ago",
    "glucose_120m_ago": "Glucose 2 hours ago",
    "glucose_change_5m": "5-minute glucose change",
    "glucose_change_15m": "15-minute glucose change",
    "glucose_change_30m": "30-minute glucose change",
    "glucose_change_60m": "60-minute glucose change",
    "slope_30m": "30-minute glucose trend",
    "slope_60m": "60-minute glucose trend",
    "cgm_mean_15min": "15-minute average glucose",
    "cgm_std_15min": "15-minute glucose variability",
    "cgm_min_15min": "15-minute minimum glucose",
    "cgm_max_15min": "15-minute maximum glucose",
    "cgm_mean_30min": "30-minute average glucose",
    "cgm_std_30min": "30-minute glucose variability",
    "cgm_min_30min": "30-minute minimum glucose",
    "cgm_max_30min": "30-minute maximum glucose",
    "cgm_mean_60min": "60-minute average glucose",
    "cgm_std_60min": "60-minute glucose variability",
    "cgm_min_60min": "60-minute minimum glucose",
    "cgm_max_60min": "60-minute maximum glucose",
    "cgm_mean_120min": "120-minute average glucose",
    "cgm_std_120min": "120-minute glucose variability",
    "cgm_min_120min": "120-minute minimum glucose",
    "cgm_max_120min": "120-minute maximum glucose",
    "minutes_since_last_meal": "Time since last meal",
    "carbohydrate_last_30m": "Carbs last 30 minutes",
    "carbohydrate_last_60m": "Carbs last hour",
    "carbohydrate_last_120m": "Carbs last 2 hours",
    "carbohydrate_last_180m": "Carbs last 3 hours",
    "protein_last_30m": "Protein last 30 minutes",
    "protein_last_60m": "Protein last hour",
    "protein_last_120m": "Protein last 2 hours",
    "protein_last_180m": "Protein last 3 hours",
    "fat_last_30m": "Fat last 30 minutes",
    "fat_last_60m": "Fat last hour",
    "fat_last_120m": "Fat last 2 hours",
    "fat_last_180m": "Fat last 3 hours",
    "fiber_last_30m": "Fiber last 30 minutes",
    "fiber_last_60m": "Fiber last hour",
    "fiber_last_120m": "Fiber last 2 hours",
    "fiber_last_180m": "Fiber last 3 hours",
    "calories_last_30m": "Calories last 30 minutes",
    "calories_last_60m": "Calories last hour",
    "calories_last_120m": "Calories last 2 hours",
    "calories_last_180m": "Calories last 3 hours",
    "carb_exposure": "Cumulative carbohydrate exposure",
    "recent_meal_outlier": "Recent extreme meal",
    "current_heart_rate": "Current heart rate",
    "hr_available": "Heart rate available",
    "mean_HR_last_15m": "Average heart rate last 15 mins",
    "mean_HR_last_60m": "Average heart rate last hour",
    "std_HR_last_60m": "Heart rate variability last hour",
    "activity_calories_last_60m": "Activity calories last hour",
    "activity_calories_last_120m": "Activity calories last 2 hours",
    "hour_of_day": "Hour of day",
    "sin_hour": "Time of day (circadian sin)",
    "cos_hour": "Time of day (circadian cos)",
}

def get_feature_group(col: str) -> str:
    if col.startswith('cgm_') or col.startswith('glucose_') or col.startswith('slope_') or col == 'current_glucose':
        return "CGM"
    if 'carbohydrate' in col or 'protein' in col or 'fat' in col or 'fiber' in col or 'calories' in col or 'carb' in col or 'meal' in col:
        if 'activity' not in col:
            return "Meal"
    if 'HR' in col or 'hr_' in col or 'heart_rate' in col:
        return "Heart Rate"
    if 'activity' in col:
        return "Activity"
    if 'hour' in col:
        return "Circadian"
    return "Unknown"

class TwinExplainer:
    def __init__(self):
        models_dir = project_root / "artifacts" / "models"
        
        with open(models_dir / "final_model_metadata.json", "r") as f:
            self.metadata = json.load(f)
            
        self.features_order = self.metadata['feature_order']
        
        self.regressor = xgb.XGBRegressor()
        self.regressor.load_model(models_dir / "glucose_regressor_final.json")
        
        with open(models_dir / "high_glucose_classifier_final.pkl", "rb") as f:
            self.classifier = pickle.load(f)
            
        # Explainer initialization
        self.reg_explainer = shap.TreeExplainer(self.regressor)
        # TreeExplainer for xgboost classifier gives log-odds (margin).
        # We can extract the tree explainer
        self.clf_explainer = shap.TreeExplainer(self.classifier)

    def _format_drivers(self, shap_values: np.ndarray, feature_row: pd.Series, top_n: int = 5, is_probability: bool = False) -> List[Dict[str, Any]]:
        contributions = []
        for i, col in enumerate(self.features_order):
            val = shap_values[i]
            contributions.append({
                "feature": col,
                "label": FEATURE_LABELS.get(col, col),
                "value": float(feature_row[col]) if pd.notna(feature_row[col]) else None,
                "contribution": float(val),
                "direction": "increases_risk" if val > 0 else "decreases_risk",
                "group": get_feature_group(col)
            })
            
        # Sort by absolute contribution magnitude
        contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)
        return contributions[:top_n]

    def explain_prediction(self, feature_row: pd.DataFrame) -> Dict[str, Any]:
        """
        Explain a single prediction. feature_row must be a DataFrame with exactly 1 row.
        """
        if len(feature_row) != 1:
            raise ValueError("Explain requires exactly 1 row.")
            
        X = feature_row[self.features_order].copy()
        for col in X.columns:
            if str(X[col].dtype) in ['object', 'string', 'bool']:
                try:
                    X[col] = X[col].astype(float)
                except ValueError:
                    pass
                    
        reg_shap = self.reg_explainer.shap_values(X)[0]
        clf_shap = self.clf_explainer.shap_values(X)[0]
        
        return {
            "glucose_forecast_drivers": self._format_drivers(reg_shap, X.iloc[0], top_n=5),
            "risk_drivers": self._format_drivers(clf_shap, X.iloc[0], top_n=5)
        }
