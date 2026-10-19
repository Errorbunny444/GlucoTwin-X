# Synthea

- **Dataset used:** Synthea 1K Sample CSV
- **Major files:** `patients.csv`, `conditions.csv`, `observations.csv`, `medications.csv`, `encounters.csv`
- **Approximate patient count:** 108
- **Relevant EHR information found:** Patient demographics, conditions, observations (glucose, BMI, BP, etc.), medications, encounters.
- **Diabetes-related data availability:** Found 125 condition records related to diabetes, hyperglycemia, hypertension, and obesity.
- **Missingness/issues discovered:** Data seems very clean as it is synthetic. Some duplicate rows were found in `observations.csv` (18 duplicates). Some columns may be mostly empty depending on the specific synthetic generation logic.

# CGMacros

- **Dataset version:** v1.0.0
- **Participant count:** Unknown (Download failed)
- **Subject categories:** Unknown
- **CGM availability:** Yes (expected, but file inaccessible)
- **Wearable/activity availability:** Yes (expected)
- **Meal/nutrition availability:** Yes (expected)
- **Metabolic variables:** Yes (expected)
- **Timestamp structure:** Date-shifted time-series (expected)
- **Missingness/issues discovered:** **CRITICAL ISSUE:** The dataset download from PhysioNet was exceptionally slow (~10 KB/s, estimated >15 hours to download 626 MB). Processing of the dataset was aborted to prevent usage of a corrupted or incomplete archive as per instructions.

# Suitability for GlucoTwin-X

### Static/Historical Stream
**Synthea:** Synthea will provide the static EHR baseline. It currently contains ~100 synthetic patients with full medical histories.

### Dynamic Stream
**CGMacros:** CGMacros will provide the dynamic CGM/Wearable stream once it can be reliably acquired.

*Note: The datasets are not naturally linked. Later phases will create synthetic composite Digital Twin identities by fusing compatible static and dynamic profiles.*
