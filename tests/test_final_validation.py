import pandas as pd
import pytest
from pathlib import Path
import numpy as np
import xgboost as xgb
import json
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.glucotwin.models.glucose_models import FEATURES_DYNAMIC, TARGETS

def test_feature_ordering_and_leakage():
    for tgt in TARGETS:
        assert tgt not in FEATURES_DYNAMIC, f"Target {tgt} found in features!"
        
def test_models_loadable_and_schema():
    models_dir = project_root / "artifacts" / "models"
    reg_path = models_dir / "glucose_regressor_final.json"
    clf_path = models_dir / "high_glucose_classifier_final.pkl"
    meta_path = models_dir / "final_model_metadata.json"
    
    if reg_path.exists():
        model = xgb.XGBRegressor()
        model.load_model(reg_path)
        assert model is not None
        
    if clf_path.exists():
        import pickle
        with open(clf_path, "rb") as f:
            model = pickle.load(f)
        assert model is not None
        
    if meta_path.exists():
        with open(meta_path, "r") as f:
            meta = json.load(f)
        assert 0.0 <= meta["chosen_threshold"] <= 1.0
        assert meta["prediction_interval_bounds"]["lower_residual"] <= meta["prediction_interval_bounds"]["upper_residual"]
        assert meta["feature_order"] == FEATURES_DYNAMIC

def test_prediction_schema():
    preds_path = project_root / "data" / "processed" / "final_validation_predictions.parquet"
    if preds_path.exists():
        df = pd.read_parquet(preds_path)
        expected_cols = [
            'twin_id' if 'twin_id' in df.columns else 'digital_twin_id', 
            'prediction_timestamp', 'actual_glucose', 'predicted_glucose', 
            'lower_interval', 'upper_interval', 'actual_high_glucose', 
            'predicted_probability', 'predicted_alert', 'validation_strategy'
        ]
        for col in expected_cols:
            assert col in df.columns, f"Missing {col} in output schema"
            
        # prediction interval lower <= prediction <= upper
        # account for small float diffs or identical
        assert (df['lower_interval'] <= df['predicted_glucose'] + 1e-5).all()
        assert (df['predicted_glucose'] <= df['upper_interval'] + 1e-5).all()
