import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.glucotwin.physiology.what_if import WhatIfScenario, run_what_if_scenarios
from src.glucotwin.twin.engine import DigitalTwinEngine

def main():
    # We will instantiate the engine and load the snapshot directly
    # In a real environment, the engine would be hot and running
    
    snapshot_path = project_root / "artifacts" / "twin_snapshots" / "DT-01_latest.json"
    with open(snapshot_path, "r") as f:
        snapshot = json.load(f)
        
    scenarios = [
        WhatIfScenario(name="30g Meal", carbs_g=30.0),
        WhatIfScenario(name="60g Meal", carbs_g=60.0),
        WhatIfScenario(name="60g Meal + Moderate Activity", carbs_g=60.0, activity_level="moderate")
    ]
    
    print("Running What-If scenarios...")
    results = run_what_if_scenarios(snapshot, scenarios)
    
    print("--- DT-01 What-If Scenario Report ---")
    for s in results['scenarios']:
        print(f"Scenario: {s['name']}")
        print(f"  Peak Glucose: {s['peak_glucose']:.1f} mg/dL")
        print(f"  Glucose at 120m: {s['glucose_120m']:.1f} mg/dL")
        if s['name'] != "Baseline":
            print(f"  Delta vs Baseline at 120m: {s['delta_vs_baseline_120m']:+.1f} mg/dL")
        print(f"  Threshold Crossing (>180): {s['simulated_threshold_crossing']}")
        print()
        
    # Build CSV artifact
    df_data = {"time_min": results['scenarios'][0]['time']}
    for s in results['scenarios']:
        col_name = "baseline_glucose" if s['name'] == "Baseline" else s['name'].replace(" ", "_").lower()
        df_data[col_name] = s['trajectory']
        
    df_csv = pd.DataFrame(df_data)
    out_dir = project_root / "artifacts" / "what_if"
    out_dir.mkdir(parents=True, exist_ok=True)
    df_csv.to_csv(out_dir / "dt01_what_if_comparison.csv", index=False)
    
    # Plotting
    plot_dir = project_root / "artifacts" / "plots" / "what_if"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=(10, 6))
    for s in results['scenarios']:
        label = s['name']
        time = s['time']
        traj = s['trajectory']
        
        if s['name'] == "Baseline":
            plt.plot(time, traj, label=label, color='black', linewidth=2, linestyle='--')
        else:
            plt.plot(time, traj, label=label, linewidth=2)
            
    # Add threshold line
    plt.axhline(y=180.0, color='red', linestyle=':', label='Research Threshold (180 mg/dL)')
    
    plt.title("DT-01 Hypothetical What-If Future Trajectories")
    plt.xlabel("Time (min)")
    plt.ylabel("Simulated Glucose (mg/dL)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(plot_dir / "dt01_scenarios.png", dpi=150)
    plt.close()
    
    print("Saved artifacts and plots.")

if __name__ == "__main__":
    main()
