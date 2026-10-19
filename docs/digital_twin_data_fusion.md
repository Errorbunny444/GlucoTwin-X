# Digital Twin Data Fusion Report

## 1. Overview
This document details the data fusion process mapping the 14 Type-2 Diabetes (T2D) subjects from the CGMacros dataset to the 33 T2D synthetic patient profiles from Synthea to create synthetic composite Digital Twin identities. 

**Objective**: Co-map physiological dynamic profiles with rich medical history while maintaining strict separation of provenance and strictly preventing data leakage (no mapping to future targets).

## 2. Methodology

### 2.1 Mapping Algorithm
- **Constraint**: One-to-one mapping to prevent repeated profiles.
- **Algorithm**: Linear Sum Assignment algorithm (`scipy.optimize.linear_sum_assignment`).
- **Distance Metric**: Pairwise Euclidean distance on standardized features.
- **Target Features**: Age, Gender (mapped numerically), BMI, HbA1c, Total Cholesterol, HDL, LDL, and Triglycerides.
- **Handling Missingness**: Median imputation was performed *only* for the purpose of distance calculation to prevent NaN issues during mapping. Actual registries retain the exact, un-imputed original values.

### 2.2 Data Integrity and Provenance
To ensure data provenance is preserved, the synthetic composite twins are assigned a new canonical ID format: `DT-XX`. The registry file explicitly maps this new composite ID back to its originating physiological identity (`cgmacros_subject_id`) and medical history identity (`synthea_patient_id`).

### 2.3 Meal Outlier Auditing
A full audit of the CGMacros meal database confirmed the presence of distinct physiological outliers in macronutrient reporting:
- **High Carb (>500g)**: CGMacros-036 (761g at a single meal).
- **High Fat (>300g)**: CGMacros-016 (508g at a single meal). Note: CGMacros-016 is not in the T2D cohort.
- **High Fiber (>1000g)**: CGMacros-016 (2830g).

These are actual reported values. Per project specifications, these values have NOT been clipped or deleted. Instead, the final registry includes a boolean flag `has_meal_outliers` for transparency during downstream modeling.

## 3. Results

**Total Composite Digital Twins Constructed**: 14

### 3.1 Demo Candidates
The system has selected the top 3 twins with the lowest matching distances as primary candidates for future Phase 2 demonstrations and the Unity/Simulink UI:

1. **DT-01** (Mapped to CGMacros-003)
2. **DT-02** (Mapped to CGMacros-030)
3. **DT-03** (Mapped to CGMacros-036) — *Note: This subject explicitly carries a meal outlier flag (761g carb event), providing an excellent edge-case for robust prediction demonstrations.*

## 4. Artifacts Generated
- `data/processed/twin_mapping.csv`: The intermediate mapping file containing calculated Euclidean distances.
- `data/processed/twin_static_profiles.csv`: The fused baseline physiological and synthesized EHR metadata table for each composite twin.
- `data/processed/twin_registry.csv`: The primary authoritative index mapping `digital_twin_id` -> `cgmacros_subject_id` & `synthea_patient_id` alongside key data quality flags (`is_demo_candidate`, `has_meal_outliers`).
- `tests/test_twin_fusion.py`: Comprehensive test suite verifying one-to-one provenance mapping and output cardinality.
