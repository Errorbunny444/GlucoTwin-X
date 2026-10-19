import pandas as pd
import numpy as np
from pathlib import Path
import json
import matplotlib.pyplot as plt
import sys

# Add src to path so we can import glucotwin
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.glucotwin.features.glucose_forecasting import build_patient_features

def main():
    print("Building Glucose Forecasting Dataset...")
    
    interim_dir = project_root / "data" / "interim"
    processed_dir = project_root / "data" / "processed"
    artifacts_dir = project_root / "artifacts"
    plots_dir = artifacts_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    # Load registries
    registry = pd.read_csv(processed_dir / "twin_registry.csv")
    static_profiles = pd.read_csv(processed_dir / "twin_static_profiles.csv")
    
    # Load dynamic data
    cgm = pd.read_csv(interim_dir / "cgmacros_cgm.csv", parse_dates=['timestamp'])
    meals = pd.read_csv(interim_dir / "cgmacros_meals.csv", parse_dates=['timestamp'])
    activity = pd.read_csv(interim_dir / "cgmacros_activity.csv", parse_dates=['timestamp'])
    
    all_features = []
    
    for _, row in registry.iterrows():
        dt_id = row['digital_twin_id']
        cg_id = row['cgmacros_subject_id']
        
        print(f"Processing {dt_id} (CGMacros: {cg_id})...")
        
        df_cgm = cgm[cgm['cgmacros_subject_id'] == cg_id]
        df_meals = meals[meals['cgmacros_subject_id'] == cg_id]
        df_activity = activity[activity['cgmacros_subject_id'] == cg_id]
        df_static = static_profiles[static_profiles['digital_twin_id'] == dt_id]
        
        features_df = build_patient_features(dt_id, df_cgm, df_meals, df_activity, df_static)
        all_features.append(features_df)
        
    full_dataset = pd.concat(all_features, ignore_index=True)
    
    print(f"Total rows generated: {len(full_dataset)}")
    
    # Save dataset
    full_dataset.to_parquet(processed_dir / "glucose_forecasting_dataset.parquet", index=False)
    
    # Save preview
    full_dataset.head(200).to_csv(artifacts_dir / "glucose_forecasting_preview.csv", index=False)
    
    # --- Generate Report ---
    report = {
        "dataset_rows": len(full_dataset),
        "number_of_twins": full_dataset['digital_twin_id'].nunique(),
        "feature_count": len(full_dataset.columns),
        "prediction_stride": "5 minutes",
        "lookback_window": "120 minutes",
        "forecast_horizon": "120 minutes",
        "positive_high_glucose_events": int(full_dataset['target_high_glucose_120m'].sum()),
        "positive_high_glucose_percentage": round(full_dataset['target_high_glucose_120m'].mean() * 100, 2),
        "target_glucose_mean": round(full_dataset['target_glucose_120m'].mean(), 2),
        "target_glucose_median": round(full_dataset['target_glucose_120m'].median(), 2),
        "target_glucose_min": round(full_dataset['target_glucose_120m'].min(), 2),
        "target_glucose_max": round(full_dataset['target_glucose_120m'].max(), 2),
        "new_event_count": int(full_dataset['target_new_high_glucose_event'].sum()),
        "missingness": full_dataset.isnull().sum().to_dict(),
        "per_twin_distribution": full_dataset.groupby('digital_twin_id')['target_high_glucose_120m'].mean().to_dict()
    }
    
    with open(artifacts_dir / "forecasting_dataset_report.json", "w") as f:
        json.dump(report, f, indent=4)
        
    # --- Visual Sanity Checks ---
    # Demo Twin (DT-01 recommended as it is complete and representative, without outlier)
    demo_twin = "DT-01"
    df_demo = full_dataset[full_dataset['digital_twin_id'] == demo_twin].sort_values('prediction_timestamp').reset_index(drop=True)
    
    if not df_demo.empty:
        # Plot 1: Prediction temporal sequence (subset of 1 day)
        plt.figure(figsize=(10, 5))
        subset = df_demo.iloc[100:200]
        plt.plot(subset['prediction_timestamp'], subset['current_glucose'], label='Current Glucose (t)')
        plt.plot(subset['prediction_timestamp'], subset['target_glucose_120m'], label='Target Glucose (t+120m)', linestyle='--')
        plt.title(f"Glucose vs Future Target ({demo_twin})")
        plt.legend()
        plt.savefig(plots_dir / "plot1_temporal_sequence.png")
        plt.close()
        
        # Plot 2: Distribution of target_glucose_120m
        plt.figure(figsize=(8, 5))
        plt.hist(full_dataset['target_glucose_120m'].dropna(), bins=50, color='skyblue', edgecolor='black')
        plt.title("Distribution of target_glucose_120m (Entire Cohort)")
        plt.xlabel("Glucose (mg/dL)")
        plt.ylabel("Frequency")
        plt.savefig(plots_dir / "plot2_target_distribution.png")
        plt.close()
        
        # Plot 3: Target Class Balance
        plt.figure(figsize=(6, 4))
        counts = full_dataset['target_high_glucose_120m'].value_counts()
        counts.plot(kind='bar', color=['green', 'red'])
        plt.title("High Glucose Target Balance (0 vs 1)")
        plt.savefig(plots_dir / "plot3_class_balance.png")
        plt.close()
        
        # Plot 4: Recent Carbs vs Future Glucose Change
        df_demo['future_change'] = df_demo['target_glucose_120m'] - df_demo['current_glucose']
        plt.figure(figsize=(8, 5))
        plt.scatter(df_demo['carbohydrate_last_120m'], df_demo['future_change'], alpha=0.5)
        plt.title(f"Carbs (last 120m) vs Future Glucose Change ({demo_twin})")
        plt.xlabel("Carbohydrates Last 120m (g)")
        plt.ylabel("Glucose Change in Next 120m (mg/dL)")
        plt.savefig(plots_dir / "plot4_carbs_vs_change.png")
        plt.close()

    print("Completed. Data, report, and plots saved.")

if __name__ == '__main__':
    main()
