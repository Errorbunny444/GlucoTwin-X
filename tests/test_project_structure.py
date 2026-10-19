import sys
from pathlib import Path
import pytest

# Ensure src is in sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from glucotwin.config.paths import (
    PROJECT_ROOT, 
    DATA_DIR, 
    RAW_DATA_DIR, 
    SYNTHEA_RAW_DIR, 
    CGMACROS_RAW_DIR,
    INTERIM_DATA_DIR,
    PROCESSED_DATA_DIR
)

def test_project_directories_exist():
    """Verify that expected data directories exist."""
    assert PROJECT_ROOT.exists(), "Project root does not exist"
    assert DATA_DIR.exists(), "Data directory does not exist"
    assert RAW_DATA_DIR.exists(), "Raw data directory does not exist"
    assert SYNTHEA_RAW_DIR.exists(), "Synthea raw data directory does not exist"
    assert CGMACROS_RAW_DIR.exists(), "CGMacros raw data directory does not exist"
    assert INTERIM_DATA_DIR.exists(), "Interim data directory does not exist"
    assert PROCESSED_DATA_DIR.exists(), "Processed data directory does not exist"

def test_package_imports():
    """Verify that core package imports work."""
    import glucotwin
    from glucotwin.config import paths
    from glucotwin.utils.logger import get_logger
    
    assert paths.PROJECT_ROOT == PROJECT_ROOT
    
    logger = get_logger("test")
    assert logger.name == "test"
