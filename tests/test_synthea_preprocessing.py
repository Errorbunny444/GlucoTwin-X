"""Automated test suite for Synthea EHR Preprocessing and Static Digital Patient Profiles."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
from glucotwin.config.paths import (
    SYNTHEA_RAW_DIR,
    INTERIM_DATA_DIR,
    ARTIFACTS_DIR,
)
from glucotwin.preprocessing.synthea import find_synthea_csv_dir


@pytest.fixture(scope="module")
def static_profiles_df():
    path = INTERIM_DATA_DIR / "synthea_static_profiles.csv"
    assert path.exists(), f"Static profiles file missing at {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def t2d_profiles_df():
    path = INTERIM_DATA_DIR / "synthea_t2d_profiles.csv"
    assert path.exists(), f"T2D profiles file missing at {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def condition_summary_df():
    path = INTERIM_DATA_DIR / "synthea_condition_summary.csv"
    assert path.exists(), f"Condition summary file missing at {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def preprocessing_report():
    path = ARTIFACTS_DIR / "synthea_preprocessing_report.json"
    assert path.exists(), f"Preprocessing report missing at {path}"
    with open(path, "r") as f:
        return json.load(f)


def test_interim_and_artifact_files_exist():
    """Verify all expected pipeline outputs exist."""
    assert (INTERIM_DATA_DIR / "synthea_static_profiles.csv").exists()
    assert (INTERIM_DATA_DIR / "synthea_t2d_profiles.csv").exists()
    assert (INTERIM_DATA_DIR / "synthea_condition_summary.csv").exists()
    assert (ARTIFACTS_DIR / "synthea_preprocessing_report.json").exists()


def test_static_profiles_structural_integrity(static_profiles_df):
    """Test 1: Exactly 1 row per patient, unique IDs, no direct PII."""
    df = static_profiles_df

    # Total synthetic patients
    assert len(df) == 1171, f"Expected 1171 profiles, found {len(df)}"

    # Exactly one row per patient
    assert df["source_patient_id"].nunique() == 1171
    assert not df["source_patient_id"].duplicated().any()

    # Disallowed direct identifiers must not exist
    prohibited_cols = ["first", "last", "name", "ssn", "passport", "drivers", "address", "phone", "street"]
    for col in df.columns:
        assert col.lower() not in prohibited_cols, f"Forbidden direct identifier found: {col}"

    # Required standardized columns exist
    required_cols = [
        "source_patient_id", "gender", "race", "ethnicity", "age",
        "has_t2d", "has_diabetes_related_condition", "has_hypertension", "has_obesity", "has_dyslipidemia",
        "bmi", "bmi_date", "body_weight", "body_weight_date",
        "hba1c", "hba1c_date", "glucose", "glucose_date",
        "systolic_bp", "systolic_bp_date", "diastolic_bp", "diastolic_bp_date",
        "total_cholesterol", "hdl", "ldl", "triglycerides",
        "diabetes_medication_count", "has_diabetes_medication", "has_metformin", "has_insulin",
        "profile_completeness"
    ]
    for req in required_cols:
        assert req in df.columns, f"Required column {req} missing from static profiles"


def test_t2d_cohort_accuracy(static_profiles_df, t2d_profiles_df):
    """Test 2: Explicit T2D cohort contains exactly 33 patients with has_t2d == True."""
    df_t2d = t2d_profiles_df

    # Target count from verified inspection
    assert len(df_t2d) == 33, f"Expected 33 explicit T2D patients, found {len(df_t2d)}"

    # All must have has_t2d == True
    assert (df_t2d["has_t2d"] == True).all()

    # Must match the T2D subset from full population
    full_t2d = static_profiles_df[static_profiles_df["has_t2d"] == True]
    assert len(full_t2d) == 33
    assert set(df_t2d["source_patient_id"]) == set(full_t2d["source_patient_id"])

    # High completeness expected in explicit T2D cohort
    assert (df_t2d["profile_completeness"] == 1.0).all(), "T2D patients expected to have 100% complete metabolic profiles"


def test_demographic_and_clinical_validity(static_profiles_df):
    """Test 3: Age, BMI, BP, and glucose physiological validity."""
    df = static_profiles_df

    # Age sanity
    assert (df["age"] >= 0).all(), "Age cannot be negative"
    assert (df["age"] <= 130).all(), "Age exceeds human ceiling"

    # BMI sanity (where present)
    valid_bmi = df["bmi"].dropna()
    assert (valid_bmi >= 10.0).all(), "BMI below biological plausibility"
    assert (valid_bmi <= 90.0).all(), "BMI above biological plausibility"

    # Glucose sanity (where present)
    valid_glu = df["glucose"].dropna()
    assert (valid_glu >= 40.0).all(), "Blood glucose below biological floor"
    assert (valid_glu <= 500.0).all(), "Blood glucose above plausible range"

    # Blood pressure: Systolic must be strictly greater than Diastolic
    bp = df[["systolic_bp", "diastolic_bp"]].dropna()
    assert (bp["systolic_bp"] > bp["diastolic_bp"]).all(), "Systolic BP must exceed Diastolic BP"
    assert (bp["systolic_bp"] >= 60).all() and (bp["systolic_bp"] <= 260).all()
    assert (bp["diastolic_bp"] >= 40).all() and (bp["diastolic_bp"] <= 160).all()


def test_zero_imputation_policy(static_profiles_df):
    """Test 4: Verify true missing fields are preserved as NaN (NO imputation performed)."""
    df = static_profiles_df

    # Full population MUST have genuine missing fields in observations
    assert df["hba1c"].isna().sum() > 0, "HbA1c must contain genuine NaNs; imputation was forbidden"
    assert df["glucose"].isna().sum() > 0, "Glucose must contain genuine NaNs; imputation was forbidden"
    assert df["total_cholesterol"].isna().sum() > 0, "Cholesterol must contain genuine NaNs"

    # Verify missing rate matches expected clinical baseline (~71% missing HbA1c in general sample)
    hba1c_missing_pct = df["hba1c"].isna().mean() * 100
    assert 65.0 <= hba1c_missing_pct <= 75.0, f"Unexpected HbA1c missingness: {hba1c_missing_pct:.2f}%"


def test_condition_summary_table(condition_summary_df, static_profiles_df):
    """Test 5: Verify compact condition summary table schema and consistency."""
    df_cond = condition_summary_df

    expected_cols = ["source_patient_id", "condition_code", "condition_description", "start", "stop"]
    assert list(df_cond.columns) == expected_cols

    # Ensure condition summary rows only belong to valid synthetic patients
    valid_ids = set(static_profiles_df["source_patient_id"])
    assert set(df_cond["source_patient_id"]).issubset(valid_ids)
    assert len(df_cond) > 1000, "Condition summary should contain all project-relevant condition instances"


def test_preprocessing_report_content(preprocessing_report):
    """Test 6: Verify preprocessing report contains all required metrics."""
    rep = preprocessing_report

    assert rep["total_raw_patients"] == 1171
    assert rep["total_processed_profiles"] == 1171
    assert rep["explicit_t2d_patient_count"] == 33
    assert rep["hypertension_count"] == 302
    assert rep["obesity_count"] == 449
    assert rep["dyslipidemia_count"] == 136
    assert rep["duplicate_count"] == 0
    assert len(rep["invalid_value_warnings"]) == 0

    assert rep["t2d_cohort_observation_availability"]["hba1c"] == 33
    assert rep["t2d_cohort_observation_availability"]["glucose"] == 33
    assert rep["t2d_cohort_observation_availability"]["bmi"] == 33


def test_raw_files_unmodified():
    """Test 7: Ensure raw Synthea files remain untouched and present."""
    csv_dir = find_synthea_csv_dir(SYNTHEA_RAW_DIR)
    for fname in ["patients.csv", "conditions.csv", "observations.csv", "medications.csv", "encounters.csv"]:
        fpath = csv_dir / fname
        assert fpath.exists(), f"Raw file {fname} was removed or missing!"
        assert fpath.stat().st_size > 0, f"Raw file {fname} is empty!"
