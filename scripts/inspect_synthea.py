import pandas as pd
import json
from pathlib import Path
import sys

# Ensure src is in sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))
from glucotwin.config.paths import SYNTHEA_RAW_DIR, ARTIFACTS_DIR

def inspect_synthea():
    print("=== SYNTHEA 1K SAMPLE INSPECTION ===")
    summary = {
        "dataset_name": "Synthea 1K Sample CSV",
        "tables": {},
        "diabetes_related_findings": {
            "unique_patients_total": 0,
            "patients_with_diabetes_related_conditions": 0,
            "explicit_type2_diabetes": 0,
            "hypertension": 0,
            "obesity": 0
        }
    }
    
    important_files = ['patients.csv', 'conditions.csv', 'observations.csv', 'medications.csv', 'encounters.csv']
    
    csv_dir = SYNTHEA_RAW_DIR
    if (SYNTHEA_RAW_DIR / "csv").exists():
        csv_dir = SYNTHEA_RAW_DIR / "csv"

    # Find the actual path of patients.csv to handle subdirectories
    for path in SYNTHEA_RAW_DIR.rglob("*.csv"):
        if path.name.lower() == 'patients.csv':
            csv_dir = path.parent
            break
            
    for fname in important_files:
        fpath = csv_dir / fname
        if not fpath.exists():
            print(f"File {fname} not found in {csv_dir}")
            continue
            
        print(f"\nInspecting {fname}...")
        df = pd.read_csv(fpath, low_memory=False)
        
        table_summary = {
            "filename": fname,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "missing_values": df.isna().sum().to_dict(),
            "duplicate_rows": int(df.duplicated().sum())
        }
        
        summary["tables"][fname] = table_summary
        print(f"Rows: {table_summary['row_count']}, Columns: {table_summary['column_count']}")
        
        if fname == 'patients.csv':
            id_col = 'Id' if 'Id' in df.columns else df.columns[0]
            summary["diabetes_related_findings"]["unique_patients_total"] = int(df[id_col].nunique())
            
        elif fname == 'conditions.csv':
            if 'DESCRIPTION' in df.columns and 'PATIENT' in df.columns:
                desc = df['DESCRIPTION'].str.lower()
                
                # Diabetes related (general)
                general_diabetes = df[desc.str.contains('diabetes|hyperglycemia', na=False)]
                summary["diabetes_related_findings"]["patients_with_diabetes_related_conditions"] = int(general_diabetes['PATIENT'].nunique())
                
                # Explicit Type-2 Diabetes
                t2d = df[desc.str.contains('type 2 diabetes|diabetes mellitus type 2', na=False)]
                summary["diabetes_related_findings"]["explicit_type2_diabetes"] = int(t2d['PATIENT'].nunique())
                
                # Hypertension
                htn = df[desc.str.contains('hypertension', na=False)]
                summary["diabetes_related_findings"]["hypertension"] = int(htn['PATIENT'].nunique())
                
                # Obesity
                obesity = df[desc.str.contains('obesity', na=False)]
                summary["diabetes_related_findings"]["obesity"] = int(obesity['PATIENT'].nunique())

    print("\nSynthea Patient Summary:")
    for k, v in summary["diabetes_related_findings"].items():
        print(f"  {k}: {v}")
        
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    with open(ARTIFACTS_DIR / "synthea_inspection.json", "w") as f:
        json.dump(summary, f, indent=4)
        
if __name__ == "__main__":
    inspect_synthea()
