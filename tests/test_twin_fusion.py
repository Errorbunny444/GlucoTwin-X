import pandas as pd
import pytest
from pathlib import Path

@pytest.fixture
def data_dir():
    return Path(__file__).resolve().parent.parent / "data"

def test_twin_registry_exists_and_format(data_dir):
    registry_path = data_dir / "processed" / "twin_registry.csv"
    assert registry_path.exists(), "twin_registry.csv missing"
    
    df = pd.read_csv(registry_path)
    assert len(df) == 14, "Should have exactly 14 composite twins"
    
    expected_cols = ['digital_twin_id', 'cgmacros_subject_id', 'synthea_patient_id', 
                     'matching_distance', 'is_demo_candidate', 'has_meal_outliers']
    for col in expected_cols:
        assert col in df.columns, f"Missing {col} in registry"

def test_twin_static_profiles(data_dir):
    profiles_path = data_dir / "processed" / "twin_static_profiles.csv"
    assert profiles_path.exists(), "twin_static_profiles.csv missing"
    
    df = pd.read_csv(profiles_path)
    assert len(df) == 14, "Should have exactly 14 composite twins in profiles"
    
    # Check provenance fields
    assert 'digital_twin_id' in df.columns
    assert 'cgmacros_subject_id' in df.columns
    assert 'synthea_patient_id' in df.columns

def test_provenance_preservation(data_dir):
    registry = pd.read_csv(data_dir / "processed" / "twin_registry.csv")
    synthea_raw = pd.read_csv(data_dir / "interim" / "synthea_t2d_profiles.csv")
    cgmacros_raw = pd.read_csv(data_dir / "interim" / "cgmacros_t2d_participants.csv")
    
    # Each twin should map back to exactly one existing CGMacros and Synthea profile
    for _, row in registry.iterrows():
        c_id = row['cgmacros_subject_id']
        s_id = row['synthea_patient_id']
        
        assert c_id in cgmacros_raw['cgmacros_subject_id'].values, "Invalid CGMacros ID"
        assert s_id in synthea_raw['source_patient_id'].values, "Invalid Synthea ID"
        
def test_demo_candidates_count(data_dir):
    registry = pd.read_csv(data_dir / "processed" / "twin_registry.csv")
    candidates = registry[registry['is_demo_candidate'] == True]
    assert len(candidates) == 3, "Should have exactly 3 demo candidates"
