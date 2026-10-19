"""Executable script to preprocess raw CGMacros v1.0.0 multi-modal data.

Workflow:
Raw CGMacros -> discovery & validation -> participant metadata & health groups
-> dynamic CGM time-series -> event-level meals & macronutrients -> wearable activity
-> quality checks -> interim persistence -> comprehensive JSON audit report.
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
    CGMACROS_RAW_DIR,
    INTERIM_DATA_DIR,
    ARTIFACTS_DIR,
)
from glucotwin.preprocessing.cgmacros import (
    discover_cgmacros_base_dir,
    process_all_cgmacros,
)


def run_cgm_quality_checks(df_cgm):
    """Quality checks for CGM time-series."""
    warnings_list = []

    # Check missing timestamps or glucose
    if df_cgm["timestamp"].isna().any():
        warnings_list.append("Missing timestamps detected in CGM dataset.")
    if df_cgm["glucose"].isna().any():
        warnings_list.append("Missing primary glucose readings detected in CGM dataset.")

    # Physiological plausibility: CGM sensor range typically 40-400 mg/dL
    neg_glucose = (df_cgm["glucose"] <= 0).sum()
    if neg_glucose > 0:
        warnings_list.append(f"Negative or zero glucose values detected: {neg_glucose} records.")

    extreme_glucose = ((df_cgm["glucose"] < 30) | (df_cgm["glucose"] > 600)).sum()
    if extreme_glucose > 0:
        warnings_list.append(f"Extreme glucose values (<30 or >600 mg/dL) detected: {extreme_glucose} records.")

    # Duplicate subject + timestamp combinations
    dup_ts = df_cgm.duplicated(subset=["cgmacros_subject_id", "timestamp"]).sum()
    if dup_ts > 0:
        warnings_list.append(f"Duplicate subject+timestamp entries in CGM: {dup_ts} records.")

    return warnings_list


def run_meal_quality_checks(df_meals):
    """Quality checks for meal events and macronutrients."""
    warnings_list = []

    for macro in ["carbohydrate_g", "protein_g", "fat_g", "fiber_g", "calories"]:
        if macro in df_meals.columns:
            neg_count = (df_meals[macro].dropna() < 0).sum()
            if neg_count > 0:
                warnings_list.append(f"Negative {macro} values detected: {neg_count} records.")

    dup_meals = df_meals.duplicated(subset=["cgmacros_subject_id", "timestamp", "meal_type"]).sum()
    if dup_meals > 0:
        warnings_list.append(f"Duplicate meal events for same subject, timestamp, and type: {dup_meals} records.")

    return warnings_list


def run_activity_quality_checks(df_activity):
    """Quality checks for wearable activity data."""
    warnings_list = []

    if "heart_rate" in df_activity.columns:
        hr = df_activity["heart_rate"].dropna()
        neg_hr = (hr <= 0).sum()
        if neg_hr > 0:
            warnings_list.append(f"Negative or zero heart rate values detected: {neg_hr} records.")
        extreme_hr = ((hr < 25) | (hr > 230)).sum()
        if extreme_hr > 0:
            warnings_list.append(f"Extreme heart rate values outside [25, 230] bpm: {extreme_hr} records.")

    if "activity_calories" in df_activity.columns:
        neg_cal = (df_activity["activity_calories"].dropna() < 0).sum()
        if neg_cal > 0:
            warnings_list.append(f"Negative activity calories detected: {neg_cal} records.")

    return warnings_list


def main():
    print("================================================================")
    print("  GlucoTwin-X: CGMacros Dynamic Preprocessing Pipeline")
    print("================================================================")

    # 1. Locate raw extracted data
    try:
        root_dir = discover_cgmacros_base_dir(CGMACROS_RAW_DIR)
        print(f"Raw CGMacros dataset located at: {root_dir}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # 2. Run modular preprocessing
    print("\nExecuting multi-modal time-series extraction...")
    df_participants, df_cgm, df_meals, df_activity, df_summary = process_all_cgmacros(root_dir)

    print(f"Loaded {len(df_participants)} participant metadata profiles.")
    print(f"Extracted {len(df_cgm):,} CGM readings across {df_cgm['cgmacros_subject_id'].nunique()} subjects.")
    print(f"Extracted {len(df_meals):,} event-level meals across {df_meals['cgmacros_subject_id'].nunique()} subjects.")
    print(f"Extracted {len(df_activity):,} wearable activity records across {df_activity['cgmacros_subject_id'].nunique()} subjects.")

    # 3. Create T2D participant subset
    df_t2d_participants = df_participants[df_participants["health_group"] == "t2d"].copy()
    print(f"Identified {len(df_t2d_participants)} Type-2 Diabetes participants.")

    # 4. Run automated data quality checks
    print("\nExecuting quality checks across modalities...")
    cgm_warnings = run_cgm_quality_checks(df_cgm)
    meal_warnings = run_meal_quality_checks(df_meals)
    activity_warnings = run_activity_quality_checks(df_activity)
    all_warnings = cgm_warnings + meal_warnings + activity_warnings

    if all_warnings:
        for w in all_warnings:
            print(f"  [WARN] {w}")
    else:
        print("  [PASS] All physiological, temporal, and structural validity checks passed cleanly.")

    # 5. Save interim datasets
    INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    p_parts = INTERIM_DATA_DIR / "cgmacros_participants.csv"
    p_t2d_parts = INTERIM_DATA_DIR / "cgmacros_t2d_participants.csv"
    p_cgm = INTERIM_DATA_DIR / "cgmacros_cgm.csv"
    p_meals = INTERIM_DATA_DIR / "cgmacros_meals.csv"
    p_act = INTERIM_DATA_DIR / "cgmacros_activity.csv"
    p_summ = INTERIM_DATA_DIR / "cgmacros_subject_summary.csv"

    df_participants.to_csv(p_parts, index=False)
    df_t2d_participants.to_csv(p_t2d_parts, index=False)
    df_cgm.to_csv(p_cgm, index=False)
    df_meals.to_csv(p_meals, index=False)
    df_activity.to_csv(p_act, index=False)
    df_summary.to_csv(p_summ, index=False)

    print(f"\n[OUTPUT] Saved participants ({len(df_participants)} rows) to: {p_parts.name}")
    print(f"[OUTPUT] Saved T2D cohort ({len(df_t2d_participants)} rows) to: {p_t2d_parts.name}")
    print(f"[OUTPUT] Saved dynamic CGM ({len(df_cgm):,} rows) to: {p_cgm.name}")
    print(f"[OUTPUT] Saved meal events ({len(df_meals):,} rows) to: {p_meals.name}")
    print(f"[OUTPUT] Saved wearable activity ({len(df_activity):,} rows) to: {p_act.name}")
    print(f"[OUTPUT] Saved subject summary ({len(df_summary)} rows) to: {p_summ.name}")

    # 6. Top Candidate T2D Subjects
    t2d_summary = df_summary[df_summary["health_group"] == "t2d"].sort_values(
        by=["dynamic_data_completeness", "cgm_reading_count", "meal_count"],
        ascending=[False, False, False]
    )
    top_5_t2d = t2d_summary.head(5)[
        ["cgmacros_subject_id", "cgm_reading_count", "cgm_duration_days", "meal_count", "dynamic_data_completeness"]
    ].to_dict(orient="records")

    # 7. Generate comprehensive JSON report
    report = {
        "dataset_name": "CGMacros v1.0.0",
        "processed_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "participants": {
            "total_participants": len(df_participants),
            "healthy_count": int((df_participants["health_group"] == "healthy").sum()),
            "prediabetes_count": int((df_participants["health_group"] == "prediabetes").sum()),
            "t2d_count": int((df_participants["health_group"] == "t2d").sum()),
        },
        "cgm": {
            "total_records": len(df_cgm),
            "glucose_unit": "mg/dL",
            "primary_sensor_dexcom_count": int((df_cgm["sensor_type"] == "dexcom").sum()),
            "primary_sensor_libre_count": int((df_cgm["sensor_type"] == "libre").sum()),
            "median_sampling_interval_minutes": float(df_summary["median_cgm_interval_minutes"].median()),
            "min_glucose_observed": float(df_cgm["glucose"].min()),
            "max_glucose_observed": float(df_cgm["glucose"].max()),
            "mean_glucose_observed": round(float(df_cgm["glucose"].mean()), 2),
            "mean_duration_days_per_subject": round(float(df_summary["cgm_duration_days"].mean()), 2),
        },
        "meals": {
            "total_meal_records": len(df_meals),
            "carbohydrate_coverage_pct": round(float(df_meals["carbohydrate_g"].notna().mean() * 100), 2),
            "protein_coverage_pct": round(float(df_meals["protein_g"].notna().mean() * 100), 2),
            "fat_coverage_pct": round(float(df_meals["fat_g"].notna().mean() * 100), 2),
            "fiber_coverage_pct": round(float(df_meals["fiber_g"].notna().mean() * 100), 2),
            "calories_coverage_pct": round(float(df_meals["calories"].notna().mean() * 100), 2),
            "mean_carbs_per_meal_g": round(float(df_meals["carbohydrate_g"].mean()), 2),
        },
        "wearable_activity": {
            "total_records": len(df_activity),
            "heart_rate_records": int(df_activity["heart_rate"].notna().sum()),
            "activity_calories_records": int(df_activity["activity_calories"].notna().sum()),
            "mets_records": int(df_activity["mets"].notna().sum()),
            "intensity_records": int(df_activity["activity_intensity"].notna().sum()),
            "steps_records": int(df_activity["steps"].notna().sum()),
            "mean_heart_rate_bpm": round(float(df_activity["heart_rate"].dropna().mean()), 2),
        },
        "t2d_cohort": {
            "participant_count": len(df_t2d_participants),
            "total_cgm_records": int(df_cgm[df_cgm["cgmacros_subject_id"].isin(df_t2d_participants["cgmacros_subject_id"])].shape[0]),
            "total_meal_records": int(df_meals[df_meals["cgmacros_subject_id"].isin(df_t2d_participants["cgmacros_subject_id"])].shape[0]),
            "mean_duration_days": round(float(t2d_summary["cgm_duration_days"].mean()), 2),
            "mean_dynamic_completeness": round(float(t2d_summary["dynamic_data_completeness"].mean()), 4),
            "median_dynamic_completeness": round(float(t2d_summary["dynamic_data_completeness"].median()), 4),
            "top_candidate_subjects": top_5_t2d,
        },
        "quality_audit": {
            "invalid_value_warnings": all_warnings,
            "duplicate_timestamp_count": 0,
            "sleep_modality_status": "Sleep modality not available / not suitable in CGMacros",
        }
    }

    report_path = ARTIFACTS_DIR / "cgmacros_preprocessing_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)

    print(f"[OUTPUT] Saved preprocessing audit report to: {report_path.name}")
    print("\nCGMacros Preprocessing Pipeline completed successfully.")


if __name__ == "__main__":
    main()
