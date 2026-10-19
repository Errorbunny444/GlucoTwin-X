import pandas as pd
import pytest
from pathlib import Path
import numpy as np
import xgboost as xgb
from sklearn.model_selection import GroupKFold
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.glucotwin.models.glucose_models import (
    FEATURES_FULL, TARGETS, run_group_kfold_regression
)

@pytest.fixture
def dataset():
    ds_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "glucose_forecasting_dataset.parquet"
    if ds_path.exists():
        return pd.read_parquet(ds_path)
    return pd.DataFrame()

def test_no_target_leakage():
    for tgt in TARGETS:
        assert tgt not in FEATURES_FULL, f"Leakage: {tgt} found in features!"
        
def test_model_features_exclude_ids():
    invalid_cols = ['digital_twin_id', 'cgmacros_subject_id', 'synthea_patient_id', 'prediction_timestamp']
    for col in invalid_cols:
        assert col not in FEATURES_FULL, f"ID {col} found in features!"

def test_groupkfold_isolation(dataset):
    if dataset.empty:
        pytest.skip("Dataset not found")
        
    gkf = GroupKFold(n_splits=5)
    groups = dataset['digital_twin_id']
    
    for train_idx, val_idx in gkf.split(dataset, groups=groups):
        train_twins = set(groups.iloc[train_idx])
        val_twins = set(groups.iloc[val_idx])
        assert len(train_twins.intersection(val_twins)) == 0, "Twins overlap between train and val folds!"

def test_persistence_baseline(dataset):
    if dataset.empty:
        pytest.skip("Dataset not found")
        
    agg, fold_metrics, oof_preds = run_group_kfold_regression(dataset, ['current_glucose'], 'target_glucose_120m', 'persistence')
    
    # Check that persistence literally returns current_glucose
    assert np.allclose(oof_preds, dataset['current_glucose'].values, equal_nan=True)

def test_oof_alignment(dataset):
    ds_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "model_oof_predictions.parquet"
    if ds_path.exists():
        oof = pd.read_parquet(ds_path)
        assert len(oof) == len(dataset)
        assert (oof['prediction_timestamp'] == dataset['prediction_timestamp']).all()
        assert (oof['digital_twin_id'] == dataset['digital_twin_id']).all()
        
def test_probabilities_range():
    ds_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "model_oof_predictions.parquet"
    if ds_path.exists():
        oof = pd.read_parquet(ds_path)
        assert oof['predicted_high_glucose_probability'].min() >= 0.0
        assert oof['predicted_high_glucose_probability'].max() <= 1.0

def test_candidate_models_loadable():
    models_dir = Path(__file__).resolve().parent.parent / "artifacts" / "models"
    reg_path = models_dir / "xgb_glucose_regressor_candidate.json"
    clf_path = models_dir / "xgb_high_glucose_classifier_candidate.json"
    
    if reg_path.exists():
        model = xgb.XGBRegressor()
        model.load_model(reg_path)
        assert model is not None
        
    if clf_path.exists():
        model = xgb.XGBClassifier()
        model.load_model(clf_path)
        assert model is not None
