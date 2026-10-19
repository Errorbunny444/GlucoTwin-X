from pathlib import Path

# Project root is 3 levels up from this file (src/glucotwin/config/paths.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
SYNTHEA_RAW_DIR = RAW_DATA_DIR / "synthea"
CGMACROS_RAW_DIR = RAW_DATA_DIR / "cgmacros"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Artifacts
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
