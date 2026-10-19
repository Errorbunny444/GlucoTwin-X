# Data

This directory stores all data used in the GlucoTwin-X project.

## Data Source 1 — Synthea

**Purpose:**
Static/Historical EHR stream.

**Expected future files may include:**
- `patients.csv`
- `conditions.csv`
- `observations.csv`
- `medications.csv`
- `encounters.csv`

**Placement:**
Actual dataset files should be placed inside:
`data/raw/synthea/`

**Current Status:**
Downloaded: Synthea 1K Sample CSV data

**Note:** Do not commit these dataset files to version control. The `.gitignore` is configured to ignore them.

---

## Data Source 2 — CGMacros

**Purpose:**
Dynamic CGM / wearable / meal time-series stream.

**Placement:**
Expected location:
`data/raw/cgmacros/`

**Current Status:**
Downloaded: Failed (Download from PhysioNet was exceptionally slow and timed out. The archive has not been successfully retrieved). Target was CGMacros v1.0.0.

**Note:** Do not commit these dataset files to version control.

---

Phase 1 preprocessing will later transform both sources into clean processed Digital Twin data, which will be saved into `data/interim/` and `data/processed/`.
