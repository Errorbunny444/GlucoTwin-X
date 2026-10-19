"""Executable script to preprocess raw Synthea EHR data into static patient profiles.

Workflow:
Raw CSVs -> validation -> patient demographic extraction -> disease condition extraction
-> observation extraction -> medication extraction -> static profile generation
-> quality checks -> save outputs (full profiles, T2D cohort, condition summary, JSON report).
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import warnings

# Add src to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from glucotwin.config.paths import (
    SYNTHEA_RAW_DIR,
    INTERIM_DATA_DIR,
    ARTIFACTS_DIR,
)
from glucotwin.preprocessing.synthea import (
    find_synthea_csv_dir,
    build_static_profiles,
)


def run_quality_checks(df, name="Profiles"):
    """Performs rigorous automated clinical and structural data quality checks."""
    warnings_list = []
    
    # 1. Row/Patient Uniqueness
    dup_count = int(df["source_patient_id"].duplicated().sum())
    if dup_count > 0:
        warnings_list.append(f"Duplicate patient IDs detected: {dup_count} duplicates found.")

    # 2. Age checks
    if "age" in df.columns:
        neg_ages = int((df["age"] < 0).sum())
        if neg_ages > 0:
            warnings_list.append(f"Negative age detected in {neg_ages} records.")
        extreme_ages = int((df["age"] > 130).sum())
        if extreme_ages > 0:
            warnings_list.append(f"Extreme ages (>130 years) detected in {extreme_ages} records.")

    # 3. BMI checks
    if "bmi" in df.columns:
        neg_bmi = int((df["bmi"].dropna() <= 0).sum())
        if neg_bmi > 0:
            warnings_list.append(f"Negative or zero BMI detected in {neg_bmi} records.")
        extreme_bmi = int(((df["bmi"].dropna() < 10) | (df["bmi"].dropna() > 90)).sum())
        if extreme_bmi > 0:
            warnings_list.append(f"Extreme BMI outside [10, 90] detected in {extreme_bmi} records.")

    # 4. Blood Glucose checks
    if "glucose" in df.columns:
        neg_glucose = int((df["glucose"].dropna() <= 0).sum())
        if neg_glucose > 0:
            warnings_list.append(f"Negative or zero glucose detected in {neg_glucose} records.")
        extreme_glucose = int((df["glucose"].dropna() > 1000).sum())
        if extreme_glucose > 0:
            warnings_list.append(f"Extreme glucose (>1000 mg/dL) detected in {extreme_glucose} records.")

    # 5. Blood Pressure checks (systolic vs diastolic)
    if "systolic_bp" in df.columns and "diastolic_bp" in df.columns:
        bp_valid = df[["systolic_bp", "diastolic_bp"]].dropna()
        malformed_bp = int((bp_valid["systolic_bp"] <= bp_valid["diastolic_bp"]).sum())
        if malformed_bp > 0:
            warnings_list.append(f"Malformed blood pressure (systolic <= diastolic) in {malformed_bp} records.")
        extreme_sbp = int(((bp_valid["systolic_bp"] < 50) | (bp_valid["systolic_bp"] > 300)).sum())
        if extreme_sbp > 0:
            warnings_list.append(f"Extreme systolic BP outside [50, 300] mmHg in {extreme_sbp} records.")

    # 6. Profile Completeness range
    if "profile_completeness" in df.columns:
        invalid_comp = int(((df["profile_completeness"] < 0.0) | (df["profile_completeness"] > 1.0)).sum())
        if invalid_comp > 0:
            warnings_list.append(f"Completeness scores outside [0.0, 1.0] in {invalid_comp} records.")

    print(f"\n--- Quality Check Summary for {name} ---")
    if warnings_list:
        for w in warnings_list:
            print(f"  [WARN] {w}")
    else:
        print("  [PASS] All clinical validity and structural sanity checks passed.")

    return warnings_list


def main():
    print("================================================================")
    print("  GlucoTwin-X: Synthea EHR Preprocessing Pipeline")
    print("================================================================")

    # 1. Locate raw Synthea CSV directory
    try:
        csv_dir = find_synthea_csv_dir(SYNTHEA_RAW_DIR)
        print(f"Raw Synthea files located at: {csv_dir}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # 2. Build static profiles and condition summary
    print("\nExecuting modular profile generation...")
    df_profiles, df_condition_summary = build_static_profiles(csv_dir)

    if df_profiles.empty:
        print("ERROR: Pipeline returned an empty profile DataFrame.")
        sys.exit(1)

    print(f"Extracted {len(df_profiles)} total patient profiles with {len(df_profiles.columns)} columns.")
    print(f"Extracted {len(df_condition_summary)} relevant condition records.")

    # 3. Create interim and artifact directories
    INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Run automated quality checks
    full_warnings = run_quality_checks(df_profiles, name="Full Population")

    # 5. Build Explicit Type-2 Diabetes Cohort
    df_t2d = df_profiles[df_profiles["has_t2d"] == True].copy()
    t2d_warnings = run_quality_checks(df_t2d, name="Type-2 Diabetes Cohort")

    # 6. Save Interim Outputs
    out_static = INTERIM_DATA_DIR / "synthea_static_profiles.csv"
    out_t2d = INTERIM_DATA_DIR / "synthea_t2d_profiles.csv"
    out_cond = INTERIM_DATA_DIR / "synthea_condition_summary.csv"

    df_profiles.to_csv(out_static, index=False)
    df_t2d.to_csv(out_t2d, index=False)
    df_condition_summary.to_csv(out_cond, index=False)

    print(f"\n[OUTPUT] Saved full static profiles ({len(df_profiles)} rows) to: {out_static.name}")
    print(f"[OUTPUT] Saved T2D cohort profiles ({len(df_t2d)} rows) to: {out_t2d.name}")
    print(f"[OUTPUT] Saved condition summary ({len(df_condition_summary)} rows) to: {out_cond.name}")

    # 7. Generate Comprehensive Preprocessing Report
    missingness = (df_profiles.isna().sum() / len(df_profiles) * 100).round(2).to_dict()
    
    report = {
        "dataset_name": "Synthea EHR 1K Sample",
        "processed_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_raw_patients": len(df_profiles),
        "total_processed_profiles": len(df_profiles),
        "explicit_t2d_patient_count": len(df_t2d),
        "diabetes_related_condition_count": int(df_profiles["has_diabetes_related_condition"].sum()),
        "hypertension_count": int(df_profiles["has_hypertension"].sum()),
        "obesity_count": int(df_profiles["has_obesity"].sum()),
        "dyslipidemia_count": int(df_profiles["has_dyslipidemia"].sum()),
        "field_missingness_percentages": missingness,
        "important_observation_availability": {
            "bmi": int(df_profiles["bmi"].notna().sum()),
            "body_weight": int(df_profiles["body_weight"].notna().sum()),
            "hba1c": int(df_profiles["hba1c"].notna().sum()),
            "glucose": int(df_profiles["glucose"].notna().sum()),
            "systolic_bp": int(df_profiles["systolic_bp"].notna().sum()),
            "diastolic_bp": int(df_profiles["diastolic_bp"].notna().sum()),
            "total_cholesterol": int(df_profiles["total_cholesterol"].notna().sum()),
            "hdl": int(df_profiles["hdl"].notna().sum()),
            "ldl": int(df_profiles["ldl"].notna().sum()),
            "triglycerides": int(df_profiles["triglycerides"].notna().sum()),
        },
        "t2d_cohort_observation_availability": {
            "bmi": int(df_t2d["bmi"].notna().sum()),
            "body_weight": int(df_t2d["body_weight"].notna().sum()),
            "hba1c": int(df_t2d["hba1c"].notna().sum()),
            "glucose": int(df_t2d["glucose"].notna().sum()),
            "systolic_bp": int(df_t2d["systolic_bp"].notna().sum()),
            "diastolic_bp": int(df_t2d["diastolic_bp"].notna().sum()),
            "total_cholesterol": int(df_t2d["total_cholesterol"].notna().sum()),
            "hdl": int(df_t2d["hdl"].notna().sum()),
            "ldl": int(df_t2d["ldl"].notna().sum()),
            "triglycerides": int(df_t2d["triglycerides"].notna().sum()),
        },
        "profile_completeness_distribution": {
            "mean": float(df_profiles["profile_completeness"].mean()),
            "median": float(df_profiles["profile_completeness"].median()),
            "min": float(df_profiles["profile_completeness"].min()),
            "max": float(df_profiles["profile_completeness"].max()),
            "t2d_mean": float(df_t2d["profile_completeness"].mean()) if not df_t2d.empty else 0.0,
            "t2d_median": float(df_t2d["profile_completeness"].median()) if not df_t2d.empty else 0.0,
        },
        "medication_summary": {
            "total_with_diabetes_medication": int(df_profiles["has_diabetes_medication"].sum()),
            "total_with_metformin": int(df_profiles["has_metformin"].sum()),
            "total_with_insulin": int(df_profiles["has_insulin"].sum()),
            "t2d_with_diabetes_medication": int(df_t2d["has_diabetes_medication"].sum()),
            "t2d_with_metformin": int(df_t2d["has_metformin"].sum()),
            "t2d_with_insulin": int(df_t2d["has_insulin"].sum()),
        },
        "invalid_value_warnings": full_warnings + t2d_warnings,
        "duplicate_count": int(df_profiles["source_patient_id"].duplicated().sum()),
    }

    report_path = ARTIFACTS_DIR / "synthea_preprocessing_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)

    print(f"[OUTPUT] Saved preprocessing report to: {report_path.name}")
    print("\nSynthea Preprocessing Pipeline completed successfully.")


if __name__ == "__main__":
    main()
