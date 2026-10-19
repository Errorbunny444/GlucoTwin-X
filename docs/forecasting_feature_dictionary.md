# Glucose Forecasting Feature Dictionary

This document defines the variables included in the ML-ready temporal dataset (`data/processed/glucose_forecasting_dataset.parquet`).

## Metadata
| Feature Name | Definition | Static/Dynamic |
|---|---|---|
| `prediction_timestamp` | The exact time `t` at which the prediction is made. | Metadata |
| `digital_twin_id` | Unique identifier for the composite digital twin patient. | Metadata |

## Targets
| Feature Name | Definition | Unit | Missingness |
|---|---|---|---|
| `target_glucose_120m` | Glucose value exactly 120 minutes in the future (nearest match within 10m). | mg/dL | Dropped if missing |
| `target_peak_glucose_next_120m` | The maximum glucose observed over the future 120 minutes. | mg/dL | Possible |
| `target_high_glucose_120m` | Binary flag (1/0): True if `target_peak_glucose_next_120m` >= 180. | Binary | Possible |
| `target_new_high_glucose_event` | Binary flag (1/0): True if `current_glucose` < 180 AND `target_high_glucose_120m` == 1. | Binary | Possible |

## CGM Dynamic Features
| Feature Name | Definition | Unit |
|---|---|---|
| `current_glucose` | The most recent glucose reading at or just before `t`. | mg/dL |
| `glucose_Xm_ago` | The exact glucose reading `X` minutes prior to `t` (where X = 5, 15, 30, 60, 120). | mg/dL |
| `glucose_change_Xm` | Difference between `current_glucose` and `glucose_Xm_ago`. | mg/dL |
| `slope_Xm` | Rate of change over `X` minutes (`glucose_change_Xm / X`). | mg/dL per min |
| `cgm_mean_Xmin` | Rolling mean of glucose over the last `X` minutes (X = 15, 30, 60, 120). | mg/dL |
| `cgm_std_Xmin` | Rolling standard deviation of glucose. | mg/dL |
| `cgm_min_Xmin` | Minimum glucose reading within rolling window. | mg/dL |
| `cgm_max_Xmin` | Maximum glucose reading within rolling window. | mg/dL |

## Meal Dynamic Features
| Feature Name | Definition | Unit |
|---|---|---|
| `minutes_since_last_meal` | Time elapsed since the most recent recorded meal. | minutes |
| `carbohydrate_last_Xm` | Sum of carbohydrates consumed in the last `X` minutes (X = 30, 60, 120, 180). | g |
| `protein_last_Xm` | Sum of protein consumed in the last `X` minutes. | g |
| `fat_last_Xm` | Sum of fat consumed in the last `X` minutes. | g |
| `fiber_last_Xm` | Sum of fiber consumed in the last `X` minutes. | g |
| `calories_last_Xm` | Sum of calories consumed in the last `X` minutes. | kcal |
| `carb_exposure` | Exponentially decayed carbohydrate accumulation (60-minute half-life), modeling basic digestion. | g (decayed) |
| `recent_meal_outlier` | Binary flag indicating if a biologically extreme meal (>500g carb or >300g fat) occurred in the last 180m. | Binary |

## Activity & Heart Rate Dynamic Features
| Feature Name | Definition | Unit | Missingness |
|---|---|---|---|
| `hr_available` | Binary flag indicating whether heart rate data exists for this timeframe. | Binary | None |
| `current_heart_rate` | Most recent mean heart rate over the last 5 minutes. | bpm | Expected |
| `mean_HR_last_Xm` | Mean heart rate over the last `X` minutes (15, 60). | bpm | Expected |
| `std_HR_last_60m` | Standard deviation of heart rate over the last 60 minutes. | bpm | Expected |
| `activity_calories_last_Xm` | Sum of activity-induced calories over the last `X` minutes (60, 120). | kcal | Expected |

## Static Profile Features
| Feature Name | Definition | Unit |
|---|---|---|
| `age` | Patient age. | Years |
| `gender` | Encoded gender (0/1). | Categorical |
| `bmi` | Body Mass Index. | kg/m² |
| `hba1c` | Glycated hemoglobin. | % |
| `fasting_glucose` | Baseline fasting glucose. | mg/dL |
| `cholesterol` | Total baseline cholesterol. | mg/dL |
| `hdl` / `ldl` | High/Low-density lipoprotein. | mg/dL |
| `triglycerides` | Baseline triglycerides. | mg/dL |
| `has_hypertension` | EHR-derived diagnosis flag. | Binary |
| `has_dyslipidemia` | EHR-derived diagnosis flag. | Binary |
| `has_diabetes_medication` | EHR-derived medication flag. | Binary |
| `has_insulin` | EHR-derived insulin prescription flag. | Binary |

## Circadian Features
| Feature Name | Definition | 
|---|---|
| `hour_of_day` | Extracted hour from prediction timestamp (0-23). |
| `sin_hour` / `cos_hour` | Cyclically encoded hour of day. |
