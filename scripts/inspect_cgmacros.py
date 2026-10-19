import os
import pandas as pd
import json
import hashlib
from pathlib import Path
import sys
import zipfile

# Ensure src is in sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))
from glucotwin.config.paths import CGMACROS_RAW_DIR, ARTIFACTS_DIR

def sha256_checksum(filename, block_size=65536):
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()

def inspect_cgmacros():
    print("=== CGMACROS v1.0.0 VERIFICATION & INSPECTION ===")
    summary = {
        "dataset_name": "CGMacros v1.0.0",
        "status": "OK",
        "archive_size_mb": 0,
        "checksum_verified": False,
        "diabetes_subjects": {"Type-2": [], "Healthy": [], "Pre-diabetic": [], "Unknown": []},
        "modalities_found": [],
        "sample_time_series": {}
    }
    
    zip_path = CGMACROS_RAW_DIR / 'CGMacros_dateshifted365.zip'
    sha_path = CGMACROS_RAW_DIR / 'SHA256SUMS.txt'
    
    if not zip_path.exists():
        print("ERROR: CGMacros_dateshifted365.zip not found.")
        return
        
    summary["archive_size_mb"] = round(os.path.getsize(zip_path) / (1024 * 1024), 2)
    print(f"Archive size: {summary['archive_size_mb']} MB")
    
    # 1. Verify Checksum
    if sha_path.exists():
        expected_sha = None
        with open(sha_path, 'r') as f:
            for line in f:
                if 'CGMacros_dateshifted365.zip' in line:
                    expected_sha = line.split()[0].strip()
                    break
        if expected_sha:
            actual_sha = sha256_checksum(zip_path)
            if actual_sha == expected_sha:
                print("Checksum VERIFIED.")
                summary["checksum_verified"] = True
            else:
                print(f"Checksum MISMATCH! Expected {expected_sha}, got {actual_sha}")
                summary["status"] = "CHECKSUM_FAILED"
    
    extract_dir = CGMACROS_RAW_DIR / 'extracted'
    csv_files = list(extract_dir.rglob("*.csv"))
    
    # Analyze bio.csv for subjects
    bio_files = [f for f in csv_files if f.name.lower() == 'bio.csv']
    if bio_files:
        bio_file = bio_files[0]
        try:
            df_bio = pd.read_csv(bio_file)
            
            # Use A1c to classify patients
            for idx, row in df_bio.iterrows():
                subj = row.get('subject')
                a1c = pd.to_numeric(row.get('A1c PDL (Lab)'), errors='coerce')
                if pd.isna(a1c):
                    summary["diabetes_subjects"]["Unknown"].append(subj)
                elif a1c >= 6.5:
                    summary["diabetes_subjects"]["Type-2"].append(subj)
                elif a1c >= 5.7:
                    summary["diabetes_subjects"]["Pre-diabetic"].append(subj)
                else:
                    summary["diabetes_subjects"]["Healthy"].append(subj)
                    
            print(f"Total Participants: {len(df_bio)}")
            print(f"Healthy: {len(summary['diabetes_subjects']['Healthy'])}")
            print(f"Prediabetes: {len(summary['diabetes_subjects']['Pre-diabetic'])}")
            print(f"Type-2 Diabetes: {len(summary['diabetes_subjects']['Type-2'])}")
        except Exception as e:
            print(f"Failed to parse bio.csv: {e}")
            
    # Sample a time-series file (CGMacros-001.csv)
    ts_files = [f for f in csv_files if f.name.startswith('CGMacros-0')]
    if ts_files:
        ts_file = ts_files[0]
        df_ts = pd.read_csv(ts_file, nrows=5)
        cols = str(list(df_ts.columns)).lower()
        
        if 'cgm' in cols or 'glucose' in cols:
            summary["modalities_found"].append("CGM")
        if 'carbs' in cols or 'meal' in cols or 'food' in cols or 'protein' in cols:
            summary["modalities_found"].append("Meals/Macronutrients")
        if 'step' in cols or 'heart' in cols or 'activity' in cols:
            summary["modalities_found"].append("Wearable/Activity")
        if 'time' in cols or 'date' in cols:
            summary["modalities_found"].append("Time-series (Timestamps)")
            
        print(f"Modalities found in time-series: {summary['modalities_found']}")
    
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    with open(ARTIFACTS_DIR / "cgmacros_inspection.json", "w") as f:
        json.dump(summary, f, indent=4)
    
if __name__ == "__main__":
    inspect_cgmacros()
