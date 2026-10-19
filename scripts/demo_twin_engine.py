import pandas as pd
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.glucotwin.twin.replay import TwinReplay
from src.glucotwin.twin.engine import DigitalTwinEngine

def load_data_for_twin(twin_id: str):
    # Lookup mapping
    map_path = project_root / "data" / "processed" / "twin_mapping.csv"
    mapping = pd.read_csv(map_path)
    
    if twin_id not in mapping['digital_twin_id'].values:
        raise ValueError(f"Twin {twin_id} not found in mapping.")
        
    subject_id = mapping.loc[mapping['digital_twin_id'] == twin_id, 'cgmacros_subject_id'].values[0]
    
    # Load and filter
    interim_dir = project_root / "data" / "interim"
    df_cgm = pd.read_csv(interim_dir / "cgmacros_cgm.csv")
    df_meals = pd.read_csv(interim_dir / "cgmacros_meals.csv")
    df_activity = pd.read_csv(interim_dir / "cgmacros_activity.csv")
    
    df_cgm = df_cgm[df_cgm['cgmacros_subject_id'] == subject_id].copy()
    df_meals = df_meals[df_meals['cgmacros_subject_id'] == subject_id].copy()
    df_activity = df_activity[df_activity['cgmacros_subject_id'] == subject_id].copy()
    
    df_cgm['timestamp'] = pd.to_datetime(df_cgm['timestamp'])
    df_meals['timestamp'] = pd.to_datetime(df_meals['timestamp'])
    df_activity['timestamp'] = pd.to_datetime(df_activity['timestamp'])
    
    return df_cgm, df_meals, df_activity

def demo():
    twin_id = "DT-01"
    print(f"Loading data for {twin_id}...")
    df_cgm, df_meals, df_activity = load_data_for_twin(twin_id)
    
    # Take a meaningful slice containing a meal if possible
    # Just sort by timestamp and take the first few days
    start_time = df_cgm['timestamp'].min()
    end_time = start_time + pd.Timedelta(days=3)
    
    df_cgm = df_cgm[(df_cgm['timestamp'] >= start_time) & (df_cgm['timestamp'] <= end_time)]
    df_meals = df_meals[(df_meals['timestamp'] >= start_time) & (df_meals['timestamp'] <= end_time)]
    df_activity = df_activity[(df_activity['timestamp'] >= start_time) & (df_activity['timestamp'] <= end_time)]
    
    print(f"Initializing Replay Engine with {len(df_cgm)} CGM events, {len(df_meals)} meals, {len(df_activity)} activity events...")
    
    replay = TwinReplay(twin_id, df_cgm, df_meals, df_activity)
    
    # Run
    print("Starting Replay...")
    results = replay.run(prediction_stride_minutes=15, verbose=True) # less frequent print
    
    print("\n--- Replay Summary ---")
    print(f"Total Predictions: {len(results)}")
    
    # Save a snapshot for inspection
    import json
    out_dir = project_root / "artifacts" / "twin_snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot = replay.engine.get_snapshot().to_dict()
    
    with open(out_dir / f"{twin_id}_latest.json", "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"Saved snapshot to {out_dir / f'{twin_id}_latest.json'}")

if __name__ == "__main__":
    demo()
