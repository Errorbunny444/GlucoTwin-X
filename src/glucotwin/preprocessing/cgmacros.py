"""CGMacros Preprocessing Module for GlucoTwin-X.

Converts raw multi-modal CGMacros v1.0.0 data (CGM, meals, wearable activity, baseline biology)
into clean, standardized, and traceable dynamic patient time-series tables.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import warnings

import numpy as np
import pandas as pd

# ADA (American Diabetes Association) Diagnostic HbA1c Cutoffs
ADA_HBA1C_THRESHOLDS = {
    "healthy_upper": 5.7,     # < 5.7% is normoglycemic
    "prediabetes_upper": 6.5, # 5.7% to < 6.5% is prediabetes, >= 6.5% is T2D
}


def discover_cgmacros_base_dir(base_path: Union[str, Path]) -> Path:
    """Discovers the root directory containing extracted CGMacros participant folders.
    
    Searches for directory containing bio.csv and participant directories.
    """
    path = Path(base_path)
    if (path / "bio.csv").exists():
        return path
    if (path / "extracted" / "CGMacros" / "bio.csv").exists():
        return path / "extracted" / "CGMacros"
    for candidate in path.rglob("bio.csv"):
        return candidate.parent
    raise FileNotFoundError(f"Could not locate CGMacros directory with bio.csv under {base_path}")


def load_participant_metadata(base_dir: Union[str, Path]) -> pd.DataFrame:
    """Loads and standardizes participant baseline metabolic metadata from bio.csv.
    
    Standardizes:
    - cgmacros_subject_id: CGMacros-001 through CGMacros-049
    - health_group: 'healthy', 'prediabetes', 't2d' based on ADA HbA1c diagnostic criteria
    - diabetes_status: descriptive diagnosis label
    - age, gender, race_ethnicity, bmi
    - body_weight_lbs, body_weight_kg (standardized conversion)
    - height_in, height_cm (standardized conversion)
    - hba1c (% NGSP), fasting_glucose (mg/dL), fasting_insulin (mcU/mL)
    - complete lipid panel (triglycerides, cholesterol, HDL, non-HDL, LDL, VLDL, chol/HDL ratio)
    """
    root_dir = discover_cgmacros_base_dir(base_dir)
    bio_path = root_dir / "bio.csv"
    if not bio_path.exists():
        raise FileNotFoundError(f"bio.csv not found at {bio_path}")

    raw_bio = pd.read_csv(bio_path)

    # Standardize column names and patient IDs
    df = pd.DataFrame()
    df["cgmacros_subject_id"] = raw_bio["subject"].apply(lambda s: f"CGMacros-{int(s):03d}")

    # ADA HbA1c Classification
    a1c_vals = pd.to_numeric(raw_bio["A1c PDL (Lab)"], errors="coerce")
    
    def classify_health_group(val: float) -> str:
        if pd.isna(val):
            return "unknown"
        if val < ADA_HBA1C_THRESHOLDS["healthy_upper"]:
            return "healthy"
        if val < ADA_HBA1C_THRESHOLDS["prediabetes_upper"]:
            return "prediabetes"
        return "t2d"

    def classify_diabetes_status(val: float) -> str:
        if pd.isna(val):
            return "Unknown"
        if val < ADA_HBA1C_THRESHOLDS["healthy_upper"]:
            return "Healthy (Normoglycemic)"
        if val < ADA_HBA1C_THRESHOLDS["prediabetes_upper"]:
            return "Prediabetes"
        return "Type-2 Diabetes"

    df["health_group"] = a1c_vals.apply(classify_health_group)
    df["diabetes_status"] = a1c_vals.apply(classify_diabetes_status)

    df["age"] = pd.to_numeric(raw_bio["Age"], errors="coerce").astype(int)
    df["gender"] = raw_bio["Gender"].astype(str).str.strip().str.upper()
    df["race_ethnicity"] = raw_bio["Self-identify "].astype(str).str.strip()
    df["bmi"] = pd.to_numeric(raw_bio["BMI"], errors="coerce").round(2)

    # Body measurements and unit conversions
    weight_lbs = pd.to_numeric(raw_bio["Body weight "], errors="coerce")
    height_in = pd.to_numeric(raw_bio["Height "], errors="coerce")
    df["body_weight_lbs"] = weight_lbs.round(1)
    df["body_weight_kg"] = (weight_lbs * 0.45359237).round(1)
    df["height_in"] = height_in.round(1)
    df["height_cm"] = (height_in * 2.54).round(1)

    # Glycemic and metabolic markers
    df["hba1c"] = a1c_vals.round(2)
    df["fasting_glucose"] = pd.to_numeric(raw_bio["Fasting GLU - PDL (Lab)"], errors="coerce")
    df["fasting_insulin"] = pd.to_numeric(raw_bio["Insulin "], errors="coerce").round(1)

    # Lipid profile
    df["triglycerides"] = pd.to_numeric(raw_bio["Triglycerides"], errors="coerce")
    df["cholesterol"] = pd.to_numeric(raw_bio["Cholesterol"], errors="coerce")
    df["hdl"] = pd.to_numeric(raw_bio["HDL"], errors="coerce")
    df["non_hdl"] = pd.to_numeric(raw_bio["Non HDL "], errors="coerce")
    df["ldl"] = pd.to_numeric(raw_bio["LDL (Cal)"], errors="coerce")
    df["vldl"] = pd.to_numeric(raw_bio["VLDL (Cal)"], errors="coerce")
    df["chol_hdl_ratio"] = pd.to_numeric(raw_bio["Cho/HDL Ratio"], errors="coerce").round(2)

    return df.sort_values("cgmacros_subject_id").reset_index(drop=True)


def parse_and_standardize_timestamp(series: pd.Series) -> pd.Series:
    """Parses timestamps safely without altering date shift or injecting timezone bias.
    
    Returns ISO-8601 formatted datetime strings: 'YYYY-MM-DD HH:MM:SS'.
    """
    dt = pd.to_datetime(series, errors="coerce")
    return dt.dt.strftime("%Y-%m-%d %H:%M:%S")


def preprocess_cgm_series(df_raw: pd.DataFrame, subject_id: str) -> pd.DataFrame:
    """Extracts and standardizes glucose time-series from raw participant table.
    
    Schema:
    - cgmacros_subject_id: participant ID
    - timestamp: ISO-8601 datetime string
    - glucose: primary glucose value (Dexcom when available, else Libre)
    - glucose_unit: 'mg/dL'
    - sensor_type: 'dexcom' or 'libre'
    - glucose_dexcom: raw Dexcom G6 Pro reading in mg/dL
    - glucose_libre: raw Libre Pro reading in mg/dL
    """
    ts_str = parse_and_standardize_timestamp(df_raw["Timestamp"])

    dexcom_vals = pd.to_numeric(df_raw["Dexcom GL"], errors="coerce") if "Dexcom GL" in df_raw.columns else pd.Series(np.nan, index=df_raw.index)
    libre_vals = pd.to_numeric(df_raw["Libre GL"], errors="coerce") if "Libre GL" in df_raw.columns else pd.Series(np.nan, index=df_raw.index)

    # Primary glucose selection: Dexcom G6 Pro (gold standard) when available, fallback to Libre Pro
    primary_glucose = dexcom_vals.combine_first(libre_vals)
    sensor_type = np.where(dexcom_vals.notna(), "dexcom", np.where(libre_vals.notna(), "libre", "none"))

    out_df = pd.DataFrame({
        "cgmacros_subject_id": subject_id,
        "timestamp": ts_str,
        "glucose": primary_glucose,
        "glucose_unit": "mg/dL",
        "sensor_type": sensor_type,
        "glucose_dexcom": dexcom_vals,
        "glucose_libre": libre_vals,
    })

    # Drop rows without timestamp or any glucose reading
    out_df = out_df.dropna(subset=["timestamp", "glucose"]).copy()

    # Sort chronologically
    out_df = out_df.sort_values("timestamp").reset_index(drop=True)

    return out_df


def preprocess_meal_events(df_raw: pd.DataFrame, subject_id: str) -> pd.DataFrame:
    """Extracts event-level meals and macronutrient details.
    
    Schema:
    - cgmacros_subject_id: participant ID
    - timestamp: ISO-8601 datetime string
    - meal_type: normalized lowercase ('breakfast', 'lunch', 'dinner', 'snack')
    - carbohydrate_g: float grams
    - protein_g: float grams
    - fat_g: float grams
    - fiber_g: float grams
    - calories: float kcal
    - amount_consumed_pct: float percentage
    - image_path: optional path to meal photo
    """
    meal_type_col = "Meal Type" if "Meal Type" in df_raw.columns else None
    carbs_col = "Carbs" if "Carbs" in df_raw.columns else None
    calories_col = "Calories" if "Calories" in df_raw.columns else None

    # Filter rows with meal event presence
    has_meal = pd.Series(False, index=df_raw.index)
    if meal_type_col:
        has_meal |= df_raw[meal_type_col].notna()
    if carbs_col:
        has_meal |= df_raw[carbs_col].notna()
    if calories_col:
        has_meal |= df_raw[calories_col].notna()

    meal_subset = df_raw[has_meal].copy()
    if meal_subset.empty:
        return pd.DataFrame(columns=[
            "cgmacros_subject_id", "timestamp", "meal_type", "carbohydrate_g",
            "protein_g", "fat_g", "fiber_g", "calories", "amount_consumed_pct", "image_path"
        ])

    ts_str = parse_and_standardize_timestamp(meal_subset["Timestamp"])

    # Normalize meal types: breakfast, lunch, dinner, snack
    raw_meal_types = meal_subset[meal_type_col].astype(str).str.strip().str.lower() if meal_type_col else pd.Series("unspecified", index=meal_subset.index)
    
    def normalize_meal_type(m_str: str) -> str:
        if "breakfast" in m_str:
            return "breakfast"
        if "lunch" in m_str:
            return "lunch"
        if "dinner" in m_str:
            return "dinner"
        if "snack" in m_str:
            return "snack"
        return m_str if m_str not in ["nan", "none", ""] else "unspecified"

    norm_meal_types = raw_meal_types.apply(normalize_meal_type)

    carbs = pd.to_numeric(meal_subset["Carbs"], errors="coerce") if "Carbs" in meal_subset.columns else pd.Series(np.nan, index=meal_subset.index)
    protein = pd.to_numeric(meal_subset["Protein"], errors="coerce") if "Protein" in meal_subset.columns else pd.Series(np.nan, index=meal_subset.index)
    fat = pd.to_numeric(meal_subset["Fat"], errors="coerce") if "Fat" in meal_subset.columns else pd.Series(np.nan, index=meal_subset.index)
    fiber = pd.to_numeric(meal_subset["Fiber"], errors="coerce") if "Fiber" in meal_subset.columns else pd.Series(np.nan, index=meal_subset.index)
    calories = pd.to_numeric(meal_subset["Calories"], errors="coerce") if "Calories" in meal_subset.columns else pd.Series(np.nan, index=meal_subset.index)

    # Amount Consumed column handling (check possible trailing space variant)
    ac_col = "Amount Consumed" if "Amount Consumed" in meal_subset.columns else ("Amount Consumed " if "Amount Consumed " in meal_subset.columns else None)
    amount_consumed = pd.to_numeric(meal_subset[ac_col], errors="coerce") if ac_col else pd.Series(np.nan, index=meal_subset.index)

    image_col = "Image path" if "Image path" in meal_subset.columns else None
    image_path = meal_subset[image_col].astype(str) if image_col else pd.Series(np.nan, index=meal_subset.index)
    image_path = image_path.replace({"nan": np.nan, "None": np.nan})

    out_df = pd.DataFrame({
        "cgmacros_subject_id": subject_id,
        "timestamp": ts_str,
        "meal_type": norm_meal_types,
        "carbohydrate_g": carbs,
        "protein_g": protein,
        "fat_g": fat,
        "fiber_g": fiber,
        "calories": calories,
        "amount_consumed_pct": amount_consumed,
        "image_path": image_path,
    })

    return out_df.sort_values("timestamp").reset_index(drop=True)


def preprocess_activity_series(df_raw: pd.DataFrame, subject_id: str) -> pd.DataFrame:
    """Extracts wearable activity measurements (Fitbit Sense).
    
    Schema:
    - cgmacros_subject_id: participant ID
    - timestamp: ISO-8601 datetime string
    - heart_rate: beats per minute (HR)
    - activity_calories: kcal/min
    - mets: METs estimate (x10)
    - activity_intensity: discrete activity level (0-3) if present
    - steps: step count if present
    """
    ts_str = parse_and_standardize_timestamp(df_raw["Timestamp"])

    hr = pd.to_numeric(df_raw["HR"], errors="coerce") if "HR" in df_raw.columns else pd.Series(np.nan, index=df_raw.index)
    act_cal = pd.to_numeric(df_raw["Calories (Activity)"], errors="coerce") if "Calories (Activity)" in df_raw.columns else pd.Series(np.nan, index=df_raw.index)
    
    mets = pd.to_numeric(df_raw["METs"], errors="coerce") if "METs" in df_raw.columns else pd.Series(np.nan, index=df_raw.index)
    intensity = pd.to_numeric(df_raw["Intensity"], errors="coerce") if "Intensity" in df_raw.columns else pd.Series(np.nan, index=df_raw.index)
    steps = pd.to_numeric(df_raw["Steps"], errors="coerce") if "Steps" in df_raw.columns else pd.Series(np.nan, index=df_raw.index)

    out_df = pd.DataFrame({
        "cgmacros_subject_id": subject_id,
        "timestamp": ts_str,
        "heart_rate": hr,
        "activity_calories": act_cal,
        "mets": mets,
        "activity_intensity": intensity,
        "steps": steps,
    })

    return out_df.sort_values("timestamp").reset_index(drop=True)


def calculate_dynamic_completeness(
    meta_present: bool,
    cgm_count: int,
    meal_count: int,
    activity_count: int,
) -> float:
    """Calculates dynamic data completeness metric in [0.0, 1.0].
    
    Evaluation weights:
    - Metadata availability (25%): baseline biology present
    - CGM coverage (25%): target 14,400 readings (~10 days of continuous 1-min data)
    - Meal records (25%): target 30 logged meals (~3 meals/day over 10 days)
    - Activity records (25%): target 10,000 wearable records (~7 days of tracking)
    """
    meta_score = 1.0 if meta_present else 0.0
    cgm_score = min(1.0, cgm_count / 14400.0)
    meal_score = min(1.0, meal_count / 30.0)
    act_score = min(1.0, activity_count / 10000.0)

    score = 0.25 * meta_score + 0.25 * cgm_score + 0.25 * meal_score + 0.25 * act_score
    return round(float(score), 4)


def process_all_cgmacros(
    base_dir: Union[str, Path]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Processes the full CGMacros dataset across all modalities.
    
    Returns:
    - df_participants: (45 rows) standardized baseline metadata
    - df_cgm: dynamic CGM time-series across all participants
    - df_meals: event-level meal and macronutrient records
    - df_activity: wearable activity time-series (HR, METs, Calories)
    - df_summary: (45 rows) per-subject data volume and completeness summary
    """
    root_dir = discover_cgmacros_base_dir(base_dir)

    # 1. Load participant metadata
    df_participants = load_participant_metadata(root_dir)
    health_group_lookup = dict(zip(df_participants["cgmacros_subject_id"], df_participants["health_group"]))

    # 2. Iterate through all participant directories
    subdirs = sorted([d for d in root_dir.iterdir() if d.is_dir()])
    
    cgm_dfs = []
    meal_dfs = []
    activity_dfs = []
    summary_rows = []

    for d in subdirs:
        csv_file = d / f"{d.name}.csv"
        if not csv_file.exists():
            continue

        subj_id = d.name
        h_group = health_group_lookup.get(subj_id, "unknown")
        df_raw = pd.read_csv(csv_file, low_memory=False)

        # Preprocess modalities
        subj_cgm = preprocess_cgm_series(df_raw, subj_id)
        subj_meals = preprocess_meal_events(df_raw, subj_id)
        subj_act = preprocess_activity_series(df_raw, subj_id)

        cgm_dfs.append(subj_cgm)
        meal_dfs.append(subj_meals)
        activity_dfs.append(subj_act)

        # Compute per-participant summary
        ts_dt = pd.to_datetime(subj_cgm["timestamp"], errors="coerce")
        cgm_start = ts_dt.min().strftime("%Y-%m-%d %H:%M:%S") if not subj_cgm.empty else ""
        cgm_end = ts_dt.max().strftime("%Y-%m-%d %H:%M:%S") if not subj_cgm.empty else ""
        duration_days = round((ts_dt.max() - ts_dt.min()).total_seconds() / 86400.0, 2) if not subj_cgm.empty else 0.0

        deltas = ts_dt.diff().dt.total_seconds() / 60.0
        median_delta = round(float(deltas.median()), 1) if not deltas.dropna().empty else np.nan

        cgm_vals = subj_cgm["glucose"].dropna()
        cgm_min = round(float(cgm_vals.min()), 1) if not cgm_vals.empty else np.nan
        cgm_max = round(float(cgm_vals.max()), 1) if not cgm_vals.empty else np.nan
        cgm_mean = round(float(cgm_vals.mean()), 1) if not cgm_vals.empty else np.nan

        carbs_vals = subj_meals["carbohydrate_g"].dropna()
        total_carbs = round(float(carbs_vals.sum()), 1) if not carbs_vals.empty else 0.0
        mean_carbs = round(float(carbs_vals.mean()), 1) if not carbs_vals.empty else 0.0

        hr_vals = subj_act["heart_rate"].dropna()
        hr_count = len(hr_vals)
        mean_hr = round(float(hr_vals.mean()), 1) if not hr_vals.empty else np.nan

        completeness = calculate_dynamic_completeness(
            meta_present=True,
            cgm_count=len(subj_cgm),
            meal_count=len(subj_meals),
            activity_count=hr_count,
        )

        summary_rows.append({
            "cgmacros_subject_id": subj_id,
            "health_group": h_group,
            "cgm_reading_count": len(subj_cgm),
            "cgm_start": cgm_start,
            "cgm_end": cgm_end,
            "cgm_duration_days": duration_days,
            "median_cgm_interval_minutes": median_delta,
            "cgm_min_glucose": cgm_min,
            "cgm_max_glucose": cgm_max,
            "cgm_mean_glucose": cgm_mean,
            "meal_count": len(subj_meals),
            "total_carbohydrate_g": total_carbs,
            "mean_meal_carbohydrate_g": mean_carbs,
            "activity_record_count": len(subj_act),
            "mean_heart_rate_bpm": mean_hr,
            "dynamic_data_completeness": completeness,
        })

    df_cgm = pd.concat(cgm_dfs, ignore_index=True) if cgm_dfs else pd.DataFrame()
    df_meals = pd.concat(meal_dfs, ignore_index=True) if meal_dfs else pd.DataFrame()
    df_activity = pd.concat(activity_dfs, ignore_index=True) if activity_dfs else pd.DataFrame()
    df_summary = pd.DataFrame(summary_rows).sort_values("cgmacros_subject_id").reset_index(drop=True)

    return df_participants, df_cgm, df_meals, df_activity, df_summary
