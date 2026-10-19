# CGMacros Dynamic Time-Series Preprocessing

## Overview
This document details the preprocessing pipeline for **CGMacros v1.0.0** (PhysioNet), converting raw multi-modal continuous sensor feeds and baseline clinical assays into clean, standardized, and traceable dynamic time-series datasets for the **GlucoTwin-X** platform.

---

## 1. Data Source & Provenance
- **Dataset**: CGMacros: A Continuous Glucose Monitoring and Macronutrient Intake Dataset (v1.0.0)
- **Host / Source**: PhysioNet / Stanford University & collaborators
- **Raw Storage Location**: `data/raw/cgmacros/`
- **Integrity**: Verified against official `SHA256SUMS.txt` checksums. Raw files are strictly read-only and never modified in place.

---

## 2. Modalities Used

The raw extracted files under `data/raw/cgmacros/extracted/CGMacros/` comprise:
1. `bio.csv`: Standardized laboratory assays, fingerstick calibrations, and anthropometry for all 45 participants.
2. `CGMacros-001/` through `CGMacros-049/` (45 participant subdirectories):
   - `CGMacros-00X.csv`: Time-aligned 1-minute longitudinal sensor tables.
   - `photos/`: Meal photographic verification images.

Modality breakdown:
- **Continuous Glucose Monitoring (CGM)**: Dual concurrent sensors (Dexcom G6 Pro and Abbott FreeStyle Libre Pro).
- **Nutritional Events**: Logged meals with calorie and macronutrient breakdown (Carbohydrates, Protein, Fat, Fiber).
- **Wearable Physiological Monitoring**: Fitbit Sense smartwatch capturing Heart Rate (HR), activity calories burned, and Metabolic Equivalent of Task (METs) / activity intensity.
- **Sleep Modality**: Evaluated during inspection. **Sleep modality is not available / not suitable in CGMacros** (no continuous sleep staging or duration records are present in the time-aligned participant CSVs). No synthetic sleep records were fabricated.

---

## 3. Participant Classification & Cohort Breakdown

Participant categorization into three mutually exclusive clinical health groups is based on official American Diabetes Association (ADA) diagnostic HbA1c criteria from baseline laboratory assays (`A1c PDL (Lab)` in `bio.csv`):

$$\text{Health Group} = \begin{cases} \text{healthy} & \text{if } \text{HbA1c} < 5.7\% \\ \text{prediabetes} & \text{if } 5.7\% \le \text{HbA1c} < 6.5\% \\ \text{t2d} & \text{if } \text{HbA1c} \ge 6.5\% \end{cases}$$

- **Healthy (Normoglycemic)**: **15 participants** (HbA1c: 4.6% – 5.6%)
- **Prediabetes**: **16 participants** (HbA1c: 5.7% – 6.4%)
- **Type-2 Diabetes (T2D)**: **14 participants** (HbA1c: 6.5% – 8.5%)
- **Total**: **45 unique participants**

---

## 4. CGM Time-Series Processing

- **Timestamp Parsing & Ordering**:
  - Timestamps are parsed safely into standardized ISO-8601 strings (`YYYY-MM-DD HH:MM:SS`).
  - Time-series are strictly sorted chronologically per participant.
  - Zero duplicate timestamps or rows exist in the raw dataset.
- **Dual-Sensor Hierarchy & Unit Standardization**:
  - Units are verified from data dictionaries and physiological ranges as **mg/dL**.
  - **Dexcom G6 Pro** is treated as the primary glucose signal due to its factory calibration and clinical gold-standard accuracy (MARD ~9.0%).
  - **Abbott FreeStyle Libre Pro** is retained as secondary fallback when Dexcom is uncalibrated or disconnected (present in 91.57% of rows concurrently with Dexcom, and utilized exclusively in 8.40% of rows).
  - Provenance is preserved via the `sensor_type` flag (`dexcom` vs `libre`), and both raw streams (`glucose_dexcom`, `glucose_libre`) are preserved alongside the primary `glucose` signal.
- **Sampling Frequency**:
  - The dataset is aligned onto a **1-minute sampling interval** (median $\Delta t = 1.0\text{ min}$).
- **Zero-Imputation & Zero-Interpolation Policy**:
  - In strict accordance with the pipeline specification, **no interpolation, no forward-fill, no backward-fill, and no smoothing were applied**. Raw gap characteristics are preserved for downstream feature engineering.

---

## 5. Meal & Macronutrient Event Processing

- **Event-Level Integrity**: Meals are preserved as discrete event records (1,706 total meals across 45 participants) rather than aggregated daily sums.
- **Macronutrient Completeness**:
  - `carbohydrate_g`: 100.0% coverage (range: 0.0g – 761.0g, mean: 52.1g)
  - `protein_g`: 100.0% coverage (range: 0.0g – 148.0g, mean: 29.2g)
  - `fat_g`: 100.0% coverage (range: 0.0g – 508.0g, mean: 19.8g)
  - `fiber_g`: 99.94% coverage (range: 0.0g – 2,830.0g, mean: 17.9g)
  - `calories`: 100.0% coverage (range: 0.0 kcal – 2,826.0 kcal, mean: 505.9 kcal)
  - All macronutrients and calories are verified non-negative.
- **Meal Type Normalization**: Standardized into lowercase categories: `breakfast`, `lunch`, `dinner`, `snack`.

---

## 6. Wearable Activity Processing

Wearable activity captured by Fitbit Sense smartwatches at 1-minute intervals was filtered to retain minimal but clinically meaningful dynamic physiological context:
- `heart_rate`: Beats per minute (610,256 readings, range: 30.0 – 176.0 bpm, mean: 78.8 bpm).
- `activity_calories`: Fitbit estimate of calories burned in the past minute (652,134 readings, range: 0.0 – 16.2 kcal/min).
- `mets`: Metabolic Equivalent of Task $\times 10$ (501,078 readings across 34 subjects).
- `activity_intensity`: Discrete activity level 0–3 (156,710 readings across 11 subjects).
- `steps`: Step counts where recorded (5,655 readings in `CGMacros-014`).

---

## 7. Date-Shifting De-Identification

The CGMacros dataset applies an intentional, pseudo-random year date-shift (`CGMacros_dateshifted365.zip`) to anonymize clinical timelines.
- Intra-subject temporal intervals, circadian rhythms, day-of-week sequences, and postprandial glycemic excursions are strictly preserved.
- In accordance with PhysioNet guidelines, **no attempt is made to reverse the date shift**. Timestamps are handled as relative study time in standardized ISO-8601 format.

---

## 8. Dynamic Data Completeness Metric

To identify the most reliable participants for Digital Twin pairing, a transparent multi-modal completeness metric is calculated:

$$\text{dynamic\_data\_completeness} = 0.25 \times \text{meta} + 0.25 \times \min\left(1.0, \frac{\text{cgm\_count}}{14400}\right) + 0.25 \times \min\left(1.0, \frac{\text{meal\_count}}{30}\right) + 0.25 \times \min\left(1.0, \frac{\text{hr\_count}}{10000}\right)$$

- **Full Population Mean**: $0.9826$ (Median: $1.0000$)
- **T2D Cohort Mean**: **$0.9899$ (Median: $1.0000$)**

---

## 9. Generated Output Datasets

All outputs are written to [`data/interim/`](file:///c:/Users/acer/Downloads/Healthcare%20Digital%20Twin/GlucoTwin-X/data/interim/) and [`artifacts/`](file:///c:/Users/acer/Downloads/Healthcare%20Digital%20Twin/GlucoTwin-X/artifacts/):

1. **Participant Metadata**: [`cgmacros_participants.csv`](file:///c:/Users/acer/Downloads/Healthcare%20Digital%20Twin/GlucoTwin-X/data/interim/cgmacros_participants.csv) (45 rows $\times$ 21 columns)
2. **Type-2 Diabetes Participant Cohort**: [`cgmacros_t2d_participants.csv`](file:///c:/Users/acer/Downloads/Healthcare%20Digital%20Twin/GlucoTwin-X/data/interim/cgmacros_t2d_participants.csv) (14 rows $\times$ 21 columns)
3. **Dynamic CGM Time-Series**: [`cgmacros_cgm.csv`](file:///c:/Users/acer/Downloads/Healthcare%20Digital%20Twin/GlucoTwin-X/data/interim/cgmacros_cgm.csv) (687,580 rows $\times$ 7 columns)
4. **Event-Level Meals**: [`cgmacros_meals.csv`](file:///c:/Users/acer/Downloads/Healthcare%20Digital%20Twin/GlucoTwin-X/data/interim/cgmacros_meals.csv) (1,706 rows $\times$ 10 columns)
5. **Wearable Activity**: [`cgmacros_activity.csv`](file:///c:/Users/acer/Downloads/Healthcare%20Digital%20Twin/GlucoTwin-X/data/interim/cgmacros_activity.csv) (687,580 rows $\times$ 7 columns)
6. **Per-Subject Summary**: [`cgmacros_subject_summary.csv`](file:///c:/Users/acer/Downloads/Healthcare%20Digital%20Twin/GlucoTwin-X/data/interim/cgmacros_subject_summary.csv) (45 rows $\times$ 16 columns)
7. **Audit Report**: [`artifacts/cgmacros_preprocessing_report.json`](file:///c:/Users/acer/Downloads/Healthcare%20Digital%20Twin/GlucoTwin-X/artifacts/cgmacros_preprocessing_report.json)
