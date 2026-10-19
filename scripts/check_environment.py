import sys
from pathlib import Path

# Add src to sys.path so we can import glucotwin
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from glucotwin.config.paths import SYNTHEA_RAW_DIR, CGMACROS_RAW_DIR

def check_environment():
    print("GlucoTwin-X Environment Check")
    print("=============================")
    
    # Check Python version
    py_version = sys.version_info
    print(f"Python Version: {py_version.major}.{py_version.minor}.{py_version.micro} (Requires 3.11+)")
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 11):
        print("WARNING: Python 3.11 or higher is required.")
        
    print("\nData Directories:")
    # Check Synthea
    if SYNTHEA_RAW_DIR.exists():
        synthea_files = list(SYNTHEA_RAW_DIR.glob("*"))
        # Exclude .gitkeep
        synthea_data_files = [f for f in synthea_files if f.name != ".gitkeep"]
        if synthea_data_files:
            print("Synthea data folder: READY")
        else:
            print("Synthea data folder: EMPTY")
    else:
        print(f"ERROR: Missing Synthea directory at {SYNTHEA_RAW_DIR}")
        
    # Check CGMacros
    if CGMACROS_RAW_DIR.exists():
        cgmacros_files = list(CGMACROS_RAW_DIR.glob("*"))
        # Exclude .gitkeep
        cgmacros_data_files = [f for f in cgmacros_files if f.name != ".gitkeep"]
        if cgmacros_data_files:
            print("CGMacros data folder: READY")
        else:
            print("CGMacros data folder: EMPTY")
    else:
        print(f"ERROR: Missing CGMacros directory at {CGMACROS_RAW_DIR}")

if __name__ == "__main__":
    check_environment()
