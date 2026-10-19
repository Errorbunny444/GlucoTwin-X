import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shap
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.glucotwin.explainability.shap_explainer import TwinExplainer, FEATURE_LABELS

def main():
    print("Loading dataset...")
    df = pd.read_parquet(project_root / "data" / "processed" / "glucose_forecasting_dataset.parquet")
    
    # Stratified sample or simple random sample
    # We want a mix of normal and high risk
    df_high = df[df['target_new_high_glucose_event'] == 1]
    df_norm = df[df['target_new_high_glucose_event'] == 0]
    
    # 2000 rows total
    sample_size = 1000
    df_sample = pd.concat([
        df_high.sample(n=min(sample_size, len(df_high)), random_state=42),
        df_norm.sample(n=min(sample_size, len(df_norm)), random_state=42)
    ])
    
    explainer = TwinExplainer()
    X = df_sample[explainer.features_order].copy()
    
    # Convert bools
    for col in X.columns:
        if str(X[col].dtype) in ['object', 'string', 'bool']:
            try:
                X[col] = X[col].astype(float)
            except ValueError:
                pass
                
    print("Computing SHAP values for regressor...")
    reg_shap_values = explainer.reg_explainer.shap_values(X)
    
    print("Computing SHAP values for classifier...")
    clf_shap_values = explainer.clf_explainer.shap_values(X)
    
    # Rename columns to human readable
    X_renamed = X.rename(columns=FEATURE_LABELS)
    
    plot_dir = project_root / "artifacts" / "plots" / "explainability"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating summary plots...")
    # Regressor summary
    plt.figure(figsize=(10, 8))
    shap.summary_plot(reg_shap_values, X_renamed, max_display=10, show=False)
    plt.title("SHAP Global Summary - Glucose Forecast (+120m)")
    plt.tight_layout()
    plt.savefig(plot_dir / "regressor_summary.png", dpi=150)
    plt.close()
    
    # Classifier summary
    plt.figure(figsize=(10, 8))
    shap.summary_plot(clf_shap_values, X_renamed, max_display=10, show=False)
    plt.title("SHAP Global Summary - High Glucose Risk (+120m)")
    plt.tight_layout()
    plt.savefig(plot_dir / "classifier_summary.png", dpi=150)
    plt.close()
    
    print("Global SHAP analysis complete.")

if __name__ == "__main__":
    main()
