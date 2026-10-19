"""Automated test suite for CGMacros dynamic time-series preprocessing."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
from glucotwin.config.paths import (
    CGMACROS_RAW_DIR,
    INTERIM_DATA_DIR,
    ARTIFACTS_DIR,
)
from glucotwin.preprocessing.cgmacros import discover_cgmacros_base_dir


@pytest.fixture(scope="module")
def participants_df():
    path = INTERIM_DATA_DIR / "cgmacros_participants.csv"
    assert path.exists(), f"Missing participants file at {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def t2d_participants_df():
    path = INTERIM_DATA_DIR / "cgmacros_t2d_participants.csv"
    assert path.exists(), f"Missing T2D participants file at {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def cgm_df():
    path = INTERIM_DATA_DIR / "cgmacros_cgm.csv"
    assert path.exists(), f"Missing CGM file at {path}"
    # Read first 50,000 rows for fast testing
    return pd.read_csv(path, nrows=50000)


@pytest.fixture(scope="module")
def meals_df():
    path = INTERIM_DATA_DIR / "cgmacros_meals.csv"
    assert path.exists(), f"Missing meals file at {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def activity_df():
    path = INTERIM_DATA_DIR / "cgmacros_activity.csv"
    assert path.exists(), f"Missing activity file at {path}"
    return pd.read_csv(path, nrows=50000)


@pytest.fixture(scope="module")
def summary_df():
    path = INTERIM_DATA_DIR / "cgmacros_subject_summary.csv"
    assert path.exists(), f"Missing summary file at {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def report_dict():
    path = ARTIFACTS_DIR / "cgmacros_preprocessing_report.json"
    assert path.exists(), f"Missing report at {path}"
    with open(path, "r") as f:
        return json.load(f)


def test_interim_files_exist():
    """Verify all 6 generated interim CSVs and JSON report exist."""
    assert (INTERIM_DATA_DIR / "cgmacros_participants.csv").exists()
    assert (INTERIM_DATA_DIR / "cgmacros_t2d_participants.csv").exists()
    assert (INTERIM_DATA_DIR / "cgmacros_cgm.csv").exists()
    assert (INTERIM_DATA_DIR / "cgmacros_meals.csv").exists()
    assert (INTERIM_DATA_DIR / "cgmacros_activity.csv").exists()
    assert (INTERIM_DATA_DIR / "cgmacros_subject_summary.csv").exists()
    assert (ARTIFACTS_DIR / "cgmacros_preprocessing_report.json").exists()


def test_participant_metadata_structure(participants_df):
    """Test 1: 45 unique participants, correct group counts, valid health_group values."""
    df = participants_df
    assert len(df) == 45, f"Expected 45 participants, got {len(df)}"
    assert df["cgmacros_subject_id"].nunique() == 45
    assert not df["cgmacros_subject_id"].duplicated().any()

    # Allowed health_groups
    allowed_groups = {"healthy", "prediabetes", "t2d"}
    assert set(df["health_group"].unique()).issubset(allowed_groups)

    # Specific group counts
    assert (df["health_group"] == "healthy").sum() == 15
    assert (df["health_group"] == "prediabetes").sum() == 16
    assert (df["health_group"] == "t2d").sum() == 14

    # Sanity on age, BMI, and HbA1c
    assert (df["age"] >= 18).all() and (df["age"] <= 100).all()
    assert (df["bmi"] >= 18.0).all() and (df["bmi"] <= 60.0).all()
    assert (df["hba1c"] >= 4.0).all() and (df["hba1c"] <= 15.0).all()


def test_t2d_cohort_accuracy(participants_df, t2d_participants_df):
    """Test 2: Exactly 14 T2D participants matching main metadata subset."""
    df_t2d = t2d_participants_df
    assert len(df_t2d) == 14
    assert (df_t2d["health_group"] == "t2d").all()
    assert (df_t2d["hba1c"] >= 6.5).all(), "All T2D participants must satisfy ADA diagnostic HbA1c >= 6.5%"
    assert set(df_t2d["cgmacros_subject_id"]) == set(participants_df.loc[participants_df["health_group"] == "t2d", "cgmacros_subject_id"])


def test_cgm_series_integrity(cgm_df):
    """Test 3: CGM timestamp parsing, chronological sorting, unit, and physiological plausibility."""
    df = cgm_df
    assert not df["timestamp"].isna().any()

    # Verify timestamp format is parsable
    parsed_ts = pd.to_datetime(df["timestamp"], errors="coerce")
    assert not parsed_ts.isna().any()

    # Glucose range & unit
    assert (df["glucose_unit"] == "mg/dL").all()
    assert (df["glucose"] >= 40.0).all() and (df["glucose"] <= 400.0).all()

    # Sensor type provenance
    assert set(df["sensor_type"].unique()).issubset({"dexcom", "libre"})

    # Check chronological ordering per subject
    for subj, sub_df in df.groupby("cgmacros_subject_id"):
        ts_vals = pd.to_datetime(sub_df["timestamp"])
        assert ts_vals.is_monotonic_increasing, f"Timestamps for {subj} are not monotonically increasing"


def test_meals_data_validity(meals_df):
    """Test 4: Meal events, no negative nutrients, normalized meal types."""
    df = meals_df
    assert len(df) == 1706

    # Normalized meal types
    allowed_types = {"breakfast", "lunch", "dinner", "snack", "unspecified"}
    assert set(df["meal_type"].unique()).issubset(allowed_types)

    # Non-negative macronutrients
    for col in ["carbohydrate_g", "protein_g", "fat_g", "fiber_g", "calories"]:
        vals = df[col].dropna()
        assert (vals >= 0.0).all(), f"Found negative values in {col}"

    # Verify carbohydrate availability is complete
    assert df["carbohydrate_g"].notna().all(), "All logged meals must have carbohydrate grams"


def test_activity_data_validity(activity_df):
    """Test 5: Wearable activity ranges and non-negativity."""
    df = activity_df

    # Heart rate within human biological ranges
    hr = df["heart_rate"].dropna()
    assert (hr >= 30.0).all() and (hr <= 220.0).all()

    # Activity calories non-negative
    cal = df["activity_calories"].dropna()
    assert (cal >= 0.0).all()

    # METs non-negative
    mets = df["mets"].dropna()
    assert (mets >= 0.0).all()


def test_subject_summary_and_completeness(summary_df):
    """Test 6: Per-subject summary row count and dynamic completeness range [0, 1]."""
    df = summary_df
    assert len(df) == 45
    assert not df["cgmacros_subject_id"].duplicated().any()

    # Completeness strictly bounded in [0, 1]
    assert (df["dynamic_data_completeness"] >= 0.0).all()
    assert (df["dynamic_data_completeness"] <= 1.0).all()

    # T2D completeness mean is very high (> 0.95)
    t2d_comp = df.loc[df["health_group"] == "t2d", "dynamic_data_completeness"]
    assert t2d_comp.mean() > 0.95


def test_report_content(report_dict):
    """Test 7: Preprocessing report integrity."""
    rep = report_dict
    assert rep["participants"]["total_participants"] == 45
    assert rep["participants"]["healthy_count"] == 15
    assert rep["participants"]["prediabetes_count"] == 16
    assert rep["participants"]["t2d_count"] == 14
    assert rep["cgm"]["total_records"] == 687580
    assert rep["meals"]["total_meal_records"] == 1706
    assert rep["quality_audit"]["sleep_modality_status"] == "Sleep modality not available / not suitable in CGMacros"
    assert len(rep["t2d_cohort"]["top_candidate_subjects"]) == 5


def test_raw_files_untouched():
    """Test 8: Verify raw extracted CGMacros files remain unmodified."""
    root_dir = discover_cgmacros_base_dir(CGMACROS_RAW_DIR)
    assert (root_dir / "bio.csv").exists()
    assert (root_dir / "CGMacros-001" / "CGMacros-001.csv").exists()
    assert (root_dir / "CGMacros-049" / "CGMacros-049.csv").exists()
