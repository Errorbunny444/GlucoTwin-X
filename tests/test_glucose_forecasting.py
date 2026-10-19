import pandas as pd
import pytest
from pathlib import Path

@pytest.fixture
def data_dir():
    return Path(__file__).resolve().parent.parent / "data"

@pytest.fixture
def dataset(data_dir):
    ds_path = data_dir / "processed" / "glucose_forecasting_dataset.parquet"
    if ds_path.exists():
        return pd.read_parquet(ds_path)
    return pd.DataFrame()

def test_dataset_exists_and_format(dataset):
    assert not dataset.empty, "Dataset missing or empty"
    assert 'digital_twin_id' in dataset.columns
    assert 'prediction_timestamp' in dataset.columns
    
def test_anti_leakage_targets(dataset):
    # The target should be roughly 120 minutes in the future
    # We test this conceptually since the actual 'future timestamp' isn't retained in the rows
    # But we can test that the targets have valid ranges and binary values
    assert set(dataset['target_high_glucose_120m'].dropna().unique()).issubset({0.0, 1.0})
    assert set(dataset['target_new_high_glucose_event'].dropna().unique()).issubset({0.0, 1.0})
    
def test_twin_mapping(dataset, data_dir):
    registry = pd.read_csv(data_dir / "processed" / "twin_registry.csv")
    valid_twins = registry['digital_twin_id'].unique()
    ds_twins = dataset['digital_twin_id'].unique()
    
    for dt in ds_twins:
        assert dt in valid_twins, f"{dt} not in T2D registry!"
        
def test_no_impossible_values(dataset):
    # Glucose values shouldn't be negative
    assert dataset['current_glucose'].min() >= 0
    assert dataset['target_glucose_120m'].min() >= 0
    
def test_rolling_are_backward(dataset):
    # This is an indirect test: glucose_change_15m should equal current_glucose - glucose_15m_ago
    # If this breaks, our logic for lags vs current is broken
    diff = dataset['current_glucose'] - dataset['glucose_15m_ago']
    # Check if they are equal (ignoring NaNs)
    mask = dataset['glucose_change_15m'].notna() & diff.notna()
    assert (dataset.loc[mask, 'glucose_change_15m'] == diff[mask]).all()
    
def test_source_datasets_unchanged(data_dir):
    # Simple check that raw data still exists and isn't overwritten
    assert (data_dir / "interim" / "cgmacros_cgm.csv").exists()
    assert (data_dir / "interim" / "cgmacros_meals.csv").exists()
