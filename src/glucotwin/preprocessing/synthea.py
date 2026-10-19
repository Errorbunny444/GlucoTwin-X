"""Synthea EHR Preprocessing Module for GlucoTwin-X.

Converts raw Synthea CSV tables into clean, compact static patient profiles
suitable for baseline Digital Twin patient representation.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import warnings

import numpy as np
import pandas as pd

# Core metabolic variables LOINC, description, and unit specification
OBSERVATION_METABOLIC_MAP = {
    "bmi": {
        "code": "39156-5",
        "description": "Body Mass Index",
        "expected_unit": "kg/m2",
    },
    "body_weight": {
        "code": "29463-7",
        "description": "Body Weight",
        "expected_unit": "kg",
    },
    "hba1c": {
        "code": "4548-4",
        "description": "Hemoglobin A1c/Hemoglobin.total in Blood",
        "expected_unit": "%",
    },
    "glucose": {
        "code": "2339-0",
        "description": "Glucose",
        "expected_unit": "mg/dL",
    },
    "systolic_bp": {
        "code": "8480-6",
        "description": "Systolic Blood Pressure",
        "expected_unit": "mm[Hg]",
    },
    "diastolic_bp": {
        "code": "8462-4",
        "description": "Diastolic Blood Pressure",
        "expected_unit": "mm[Hg]",
    },
    "total_cholesterol": {
        "code": "2093-3",
        "description": "Total Cholesterol",
        "expected_unit": "mg/dL",
    },
    "hdl": {
        "code": "2085-9",
        "description": "High Density Lipoprotein Cholesterol",
        "expected_unit": "mg/dL",
    },
    "ldl": {
        "code": "18262-6",
        "description": "Low Density Lipoprotein Cholesterol",
        "expected_unit": "mg/dL",
    },
    "triglycerides": {
        "code": "2571-8",
        "description": "Triglycerides",
        "expected_unit": "mg/dL",
    },
}

# Relevant condition definitions for static profile flags
CONDITION_DEFINITIONS = {
    "explicit_t2d_codes": {
        "368581000119106",  # Neuropathy due to type 2 diabetes mellitus
        "1551000119108",    # Nonproliferative diabetic retinopathy due to type 2 diabetes mellitus
        "90781000119102",   # Microalbuminuria due to type 2 diabetes mellitus
        "97331000119101",   # Macular edema and retinopathy due to type 2 diabetes mellitus
    },
    "t2d_description_regex": r"(?i)(?:type\s*2\s*diabetes|diabetes\s*mellitus\s*type\s*2)",
    "diabetes_related_regex": r"(?i)(?:diabetes|hyperglycemia|prediabetes)",
    "hypertension_code": "59621000",
    "hypertension_regex": r"(?i)hypertension",
    "obesity_codes": {"162864005", "408512008"},
    "obesity_regex": r"(?i)obesity",
    "dyslipidemia_codes": {"55822004"},
    "dyslipidemia_regex": r"(?i)(?:hyperlipidemia|dyslipidemia)",
}


def find_synthea_csv_dir(base_dir: Union[str, Path]) -> Path:
    """Locates the directory containing patients.csv within base_dir.
    
    Handles nested directory layouts (e.g. data/raw/synthea/csv/csv).
    """
    base_path = Path(base_dir)
    if (base_path / "patients.csv").exists():
        return base_path
    for p in base_path.rglob("patients.csv"):
        return p.parent
    raise FileNotFoundError(f"Could not find patients.csv in {base_dir} or subdirectories.")


def load_synthea_tables(csv_dir: Union[str, Path]) -> Dict[str, pd.DataFrame]:
    """Loads required Synthea CSV tables into pandas DataFrames.
    
    Expected tables: patients, conditions, observations, medications, encounters.
    """
    resolved_dir = find_synthea_csv_dir(csv_dir)
    tables = {}
    table_names = ["patients", "conditions", "observations", "medications", "encounters"]
    
    for name in table_names:
        file_path = resolved_dir / f"{name}.csv"
        if file_path.exists():
            tables[name] = pd.read_csv(file_path, low_memory=False)
        else:
            warnings.warn(f"Synthea table '{name}.csv' not found in {resolved_dir}.")
            tables[name] = pd.DataFrame()
            
    return tables


def extract_demographics(
    patients_df: pd.DataFrame,
    encounters_df: pd.DataFrame,
    observations_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Extracts demographic attributes and calculates age using a reproducible clinical reference date.
    
    Reference Date Logic:
    - If the patient is deceased (DEATHDATE is present), use DEATHDATE (age at death).
    - If the patient is living, use their latest clinical encounter date.
    - If encounter date is missing, fallback to latest observation date or dataset reference date.
    Age is computed as: (reference_date - birthdate) in days / 365.25.
    
    Returns DataFrame with:
    ['source_patient_id', 'gender', 'race', 'ethnicity', 'age']
    """
    if patients_df.empty:
        return pd.DataFrame(columns=["source_patient_id", "gender", "race", "ethnicity", "age"])

    id_col = "Id" if "Id" in patients_df.columns else patients_df.columns[0]
    df = patients_df[[id_col, "BIRTHDATE", "DEATHDATE", "GENDER", "RACE", "ETHNICITY"]].copy()
    df.rename(columns={id_col: "source_patient_id"}, inplace=True)

    df["birthdate"] = pd.to_datetime(df["BIRTHDATE"], utc=True, errors="coerce").dt.tz_localize(None)
    df["deathdate"] = pd.to_datetime(df["DEATHDATE"], utc=True, errors="coerce").dt.tz_localize(None)

    # Calculate latest encounter date per patient
    if not encounters_df.empty and "START" in encounters_df.columns and "PATIENT" in encounters_df.columns:
        enc = encounters_df[["PATIENT", "START"]].copy()
        enc["START"] = pd.to_datetime(enc["START"], utc=True, errors="coerce").dt.tz_localize(None)
        latest_enc = enc.groupby("PATIENT")["START"].max().reset_index()
        latest_enc.rename(columns={"PATIENT": "source_patient_id", "START": "latest_encounter"}, inplace=True)
    else:
        latest_enc = pd.DataFrame(columns=["source_patient_id", "latest_encounter"])

    df = df.merge(latest_enc, on="source_patient_id", how="left")

    # If living and no encounter, check latest observation
    if observations_df is not None and not observations_df.empty and "DATE" in observations_df.columns and "PATIENT" in observations_df.columns:
        obs = observations_df[["PATIENT", "DATE"]].copy()
        obs["DATE"] = pd.to_datetime(obs["DATE"], utc=True, errors="coerce").dt.tz_localize(None)
        latest_obs = obs.groupby("PATIENT")["DATE"].max().reset_index()
        latest_obs.rename(columns={"PATIENT": "source_patient_id", "DATE": "latest_obs"}, inplace=True)
        df = df.merge(latest_obs, on="source_patient_id", how="left")
    else:
        df["latest_obs"] = pd.NaT

    # Clinical reference date determination:
    # 1. Deceased -> deathdate
    # 2. Living -> latest encounter date
    # 3. Fallback -> latest observation date
    # 4. Ultimate fallback -> dataset max encounter date or 2020-04-01
    global_ref = df["latest_encounter"].max()
    if pd.isna(global_ref):
        global_ref = pd.to_datetime("2020-04-01")

    living_ref = df["latest_encounter"].combine_first(df["latest_obs"]).fillna(global_ref)
    df["reference_date"] = df["deathdate"].combine_first(living_ref)

    # Compute age in years, rounded to 1 decimal place
    age_days = (df["reference_date"] - df["birthdate"]).dt.days
    df["age"] = (age_days / 365.25).round(1)
    df.loc[df["age"] < 0, "age"] = np.nan

    # Clean standardized demographic columns
    df["gender"] = df["GENDER"].astype(str).str.strip().str.upper()
    df["race"] = df["RACE"].astype(str).str.strip().str.lower()
    df["ethnicity"] = df["ETHNICITY"].astype(str).str.strip().str.lower()

    return df[["source_patient_id", "gender", "race", "ethnicity", "age"]]


def extract_conditions(conditions_df: pd.DataFrame, patient_ids: pd.Series) -> pd.DataFrame:
    """Extracts standardized disease flags:
    - has_t2d: Explicit Type-2 Diabetes Mellitus only
    - has_diabetes_related_condition: Any diabetes, prediabetes, or hyperglycemia
    - has_hypertension: Hypertension
    - has_obesity: Obesity / severe obesity
    - has_dyslipidemia: Hyperlipidemia / dyslipidemia
    """
    df_cond = pd.DataFrame({"source_patient_id": patient_ids})
    
    if conditions_df.empty:
        for col in ["has_t2d", "has_diabetes_related_condition", "has_hypertension", "has_obesity", "has_dyslipidemia"]:
            df_cond[col] = False
        return df_cond

    cond = conditions_df.copy()
    cond["CODE_STR"] = cond["CODE"].astype(str).str.strip()
    cond["DESC_STR"] = cond["DESCRIPTION"].astype(str).str.strip()

    # 1. Explicit T2D (SNOMED-CT codes or explicit description regex)
    t2d_code_mask = cond["CODE_STR"].isin(CONDITION_DEFINITIONS["explicit_t2d_codes"])
    t2d_desc_mask = cond["DESC_STR"].str.contains(CONDITION_DEFINITIONS["t2d_description_regex"], na=False)
    t2d_patients = cond.loc[t2d_code_mask | t2d_desc_mask, "PATIENT"].unique()

    # 2. General diabetes-related
    diab_rel_mask = cond["DESC_STR"].str.contains(CONDITION_DEFINITIONS["diabetes_related_regex"], na=False)
    diab_rel_patients = cond.loc[diab_rel_mask, "PATIENT"].unique()

    # 3. Hypertension
    htn_code_mask = cond["CODE_STR"] == CONDITION_DEFINITIONS["hypertension_code"]
    htn_desc_mask = cond["DESC_STR"].str.contains(CONDITION_DEFINITIONS["hypertension_regex"], na=False)
    htn_patients = cond.loc[htn_code_mask | htn_desc_mask, "PATIENT"].unique()

    # 4. Obesity
    obesity_code_mask = cond["CODE_STR"].isin(CONDITION_DEFINITIONS["obesity_codes"])
    obesity_desc_mask = cond["DESC_STR"].str.contains(CONDITION_DEFINITIONS["obesity_regex"], na=False)
    obesity_patients = cond.loc[obesity_code_mask | obesity_desc_mask, "PATIENT"].unique()

    # 5. Dyslipidemia / Hyperlipidemia
    dys_code_mask = cond["CODE_STR"].isin(CONDITION_DEFINITIONS["dyslipidemia_codes"])
    dys_desc_mask = cond["DESC_STR"].str.contains(CONDITION_DEFINITIONS["dyslipidemia_regex"], na=False)
    dys_patients = cond.loc[dys_code_mask | dys_desc_mask, "PATIENT"].unique()

    df_cond["has_t2d"] = df_cond["source_patient_id"].isin(t2d_patients)
    df_cond["has_diabetes_related_condition"] = df_cond["source_patient_id"].isin(diab_rel_patients)
    df_cond["has_hypertension"] = df_cond["source_patient_id"].isin(htn_patients)
    df_cond["has_obesity"] = df_cond["source_patient_id"].isin(obesity_patients)
    df_cond["has_dyslipidemia"] = df_cond["source_patient_id"].isin(dys_patients)

    return df_cond


def extract_condition_summary(conditions_df: pd.DataFrame, patient_ids: pd.Series) -> pd.DataFrame:
    """Extracts a compact table of project-relevant conditions for traceability:
    - source_patient_id
    - condition_code
    - condition_description
    - start
    - stop
    """
    if conditions_df.empty:
        return pd.DataFrame(columns=["source_patient_id", "condition_code", "condition_description", "start", "stop"])

    cond = conditions_df.copy()
    cond["CODE_STR"] = cond["CODE"].astype(str).str.strip()
    cond["DESC_STR"] = cond["DESCRIPTION"].astype(str).str.strip()

    # Filter for project-relevant conditions: diabetes, hypertension, obesity, dyslipidemia
    relevant_mask = (
        cond["CODE_STR"].isin(CONDITION_DEFINITIONS["explicit_t2d_codes"])
        | cond["DESC_STR"].str.contains(CONDITION_DEFINITIONS["diabetes_related_regex"], na=False)
        | (cond["CODE_STR"] == CONDITION_DEFINITIONS["hypertension_code"])
        | cond["DESC_STR"].str.contains(CONDITION_DEFINITIONS["hypertension_regex"], na=False)
        | cond["CODE_STR"].isin(CONDITION_DEFINITIONS["obesity_codes"])
        | cond["DESC_STR"].str.contains(CONDITION_DEFINITIONS["obesity_regex"], na=False)
        | cond["CODE_STR"].isin(CONDITION_DEFINITIONS["dyslipidemia_codes"])
        | cond["DESC_STR"].str.contains(CONDITION_DEFINITIONS["dyslipidemia_regex"], na=False)
    )

    filtered = cond[relevant_mask & cond["PATIENT"].isin(patient_ids)].copy()
    summary = filtered.rename(columns={
        "PATIENT": "source_patient_id",
        "CODE": "condition_code",
        "DESCRIPTION": "condition_description",
        "START": "start",
        "STOP": "stop",
    })[["source_patient_id", "condition_code", "condition_description", "start", "stop"]]

    summary["start"] = pd.to_datetime(summary["start"], utc=True, errors="coerce").dt.strftime("%Y-%m-%d")
    summary["stop"] = pd.to_datetime(summary["stop"], utc=True, errors="coerce").dt.strftime("%Y-%m-%d")

    return summary.sort_values(["source_patient_id", "start"]).reset_index(drop=True)


def extract_observations(observations_df: pd.DataFrame, patient_ids: pd.Series) -> pd.DataFrame:
    """Extracts the latest valid observation for each core metabolic feature.
    
    Robust Identification:
    Uses official LOINC codes as primary identifiers to avoid false matches
    (e.g. distinguishing BMI in kg/m2 from BMI percentiles, and blood glucose
    from urine glucose test strips).
    
    Returns DataFrame with:
    - [feature] : latest numerical measurement (float)
    - [feature]_date : ISO date string (YYYY-MM-DD) of the latest measurement
    """
    df_obs = pd.DataFrame({"source_patient_id": patient_ids})

    if observations_df.empty:
        for feature in OBSERVATION_METABOLIC_MAP.keys():
            df_obs[feature] = np.nan
            df_obs[f"{feature}_date"] = np.nan
        return df_obs

    obs = observations_df.copy()
    obs["CODE_STR"] = obs["CODE"].astype(str).str.strip()
    obs["DESC_STR"] = obs["DESCRIPTION"].astype(str).str.strip()
    obs["DATE_DT"] = pd.to_datetime(obs["DATE"], utc=True, errors="coerce").dt.tz_localize(None)
    obs["VALUE_NUM"] = pd.to_numeric(obs["VALUE"], errors="coerce")

    # Drop rows without numeric values or dates
    valid_obs = obs.dropna(subset=["VALUE_NUM", "DATE_DT"]).copy()

    for feature_name, spec in OBSERVATION_METABOLIC_MAP.items():
        target_code = spec["code"]
        target_desc = spec["description"].lower()

        # Target matching: by LOINC code (primary) or exact normalized description
        f_mask = (valid_obs["CODE_STR"] == target_code) | (valid_obs["DESC_STR"].str.lower() == target_desc)
        f_obs = valid_obs[f_mask].copy()

        if f_obs.empty:
            df_obs[feature_name] = np.nan
            df_obs[f"{feature_name}_date"] = np.nan
            continue

        # Sort chronologically, keep latest valid observation per patient
        f_obs_latest = f_obs.sort_values("DATE_DT").drop_duplicates(subset=["PATIENT"], keep="last")

        f_subset = f_obs_latest[["PATIENT", "VALUE_NUM", "DATE_DT"]].copy()
        f_subset["DATE_STR"] = f_subset["DATE_DT"].dt.strftime("%Y-%m-%d")
        f_subset.rename(columns={
            "PATIENT": "source_patient_id",
            "VALUE_NUM": feature_name,
            "DATE_STR": f"{feature_name}_date",
        }, inplace=True)

        df_obs = df_obs.merge(f_subset[["source_patient_id", feature_name, f"{feature_name}_date"]], on="source_patient_id", how="left")

    return df_obs


def extract_medications(medications_df: pd.DataFrame, patient_ids: pd.Series) -> pd.DataFrame:
    """Extracts compact diabetes medication summary:
    - has_diabetes_medication (bool)
    - has_metformin (bool)
    - has_insulin (bool)
    - diabetes_medication_count (int: count of distinct diabetes classes prescribed)
    - total_diabetes_prescriptions (int: total fill/dispense events)
    """
    df_meds = pd.DataFrame({"source_patient_id": patient_ids})

    if medications_df.empty:
        df_meds["diabetes_medication_count"] = 0
        df_meds["total_diabetes_prescriptions"] = 0
        df_meds["has_diabetes_medication"] = False
        df_meds["has_metformin"] = False
        df_meds["has_insulin"] = False
        return df_meds

    meds = medications_df.copy()
    meds["DESC_LOWER"] = meds["DESCRIPTION"].astype(str).str.lower()

    # Drug class masks
    metformin_mask = meds["DESC_LOWER"].str.contains("metformin", na=False)
    insulin_mask = meds["DESC_LOWER"].str.contains("insulin", na=False)
    diabetes_med_mask = metformin_mask | insulin_mask

    meds["is_metformin"] = metformin_mask
    meds["is_insulin"] = insulin_mask
    meds["is_diabetes_med"] = diabetes_med_mask

    # Aggregate by patient
    agg = meds.groupby("PATIENT").agg(
        has_metformin=("is_metformin", "any"),
        has_insulin=("is_insulin", "any"),
        has_diabetes_medication=("is_diabetes_med", "any"),
        total_diabetes_prescriptions=("is_diabetes_med", "sum"),
    ).reset_index().rename(columns={"PATIENT": "source_patient_id"})

    agg["diabetes_medication_count"] = agg["has_metformin"].astype(int) + agg["has_insulin"].astype(int)

    df_meds = df_meds.merge(agg, on="source_patient_id", how="left")

    # Default missing to zero/False
    df_meds["diabetes_medication_count"] = df_meds["diabetes_medication_count"].fillna(0).astype(int)
    df_meds["total_diabetes_prescriptions"] = df_meds["total_diabetes_prescriptions"].fillna(0).astype(int)
    for col in ["has_diabetes_medication", "has_metformin", "has_insulin"]:
        df_meds[col] = df_meds[col].eq(True)

    return df_meds


def calculate_completeness(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates profile completeness metric based on key clinical metabolic features.
    
    Evaluates availability across 9 core markers:
    ['bmi', 'hba1c', 'glucose', 'systolic_bp', 'diastolic_bp', 'total_cholesterol', 'hdl', 'ldl', 'triglycerides']
    Returns score as a float in [0.0, 1.0].
    """
    key_fields = [
        "bmi",
        "hba1c",
        "glucose",
        "systolic_bp",
        "diastolic_bp",
        "total_cholesterol",
        "hdl",
        "ldl",
        "triglycerides",
    ]
    available_fields = [f for f in key_fields if f in df.columns]
    if available_fields:
        df["profile_completeness"] = (df[available_fields].notna().sum(axis=1) / len(available_fields)).round(4)
    else:
        df["profile_completeness"] = 0.0

    return df


def build_static_profiles(csv_dir: Union[str, Path]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Orchestrates extraction of all Synthea tables into static patient profiles.
    
    Returns:
    - df_profiles: DataFrame of full static profiles (one row per patient)
    - df_condition_summary: DataFrame of project-relevant conditions for auditability
    """
    tables = load_synthea_tables(csv_dir)
    patients = tables.get("patients", pd.DataFrame())
    if patients.empty:
        return pd.DataFrame(), pd.DataFrame()

    encounters = tables.get("encounters", pd.DataFrame())
    observations = tables.get("observations", pd.DataFrame())
    conditions = tables.get("conditions", pd.DataFrame())
    medications = tables.get("medications", pd.DataFrame())

    # 1. Demographics
    df_demo = extract_demographics(patients, encounters, observations)
    patient_ids = df_demo["source_patient_id"]

    # 2. Disease Flags & Condition Summary
    df_cond = extract_conditions(conditions, patient_ids)
    df_cond_summary = extract_condition_summary(conditions, patient_ids)

    # 3. Metabolic Observations
    df_obs = extract_observations(observations, patient_ids)

    # 4. Medication Summary
    df_meds = extract_medications(medications, patient_ids)

    # Merge all components
    df_profiles = df_demo.merge(df_cond, on="source_patient_id", how="left")
    df_profiles = df_profiles.merge(df_obs, on="source_patient_id", how="left")
    df_profiles = df_profiles.merge(df_meds, on="source_patient_id", how="left")

    # 5. Completeness Metric
    df_profiles = calculate_completeness(df_profiles)

    return df_profiles, df_cond_summary
