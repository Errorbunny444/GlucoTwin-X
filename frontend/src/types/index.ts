export interface TwinSummary {
  twin_id: string;
  health_group: string;
  age: number;
  gender: string;
  bmi: number;
  hba1c: number;
  data_duration_days: number;
  completeness: number;
  demo_role?: string;
}

export interface StaticTwinState {
  twin_id: string;
  age: number;
  gender: string;
  bmi: number;
  hba1c: number;
  fasting_glucose: number;
  fasting_insulin: number;
  cholesterol: number;
  hdl: number;
  ldl: number;
  triglycerides: number;
  ehr_has_hypertension: number;
  ehr_has_dyslipidemia: number;
  ehr_has_diabetes_medication: number;
  ehr_has_insulin: number;
}

export interface DynamicTwinState {
  current_timestamp: string;
  current_glucose: number | null;
  glucose_trend: string;
  heart_rate: number | null;
  minutes_since_last_meal: number | null;
  recent_carbs_120m: number | null;
}

export interface PredictionState {
  prediction_timestamp: string;
  predicted_glucose_120m: number;
  lower_90: number;
  upper_90: number;
  high_glucose_probability: number;
  high_glucose_risk: boolean;
  alert_threshold: number;
}

export interface TwinSnapshot {
  twin_id: string;
  timestamp: string;
  status: string;
  prediction_ready: boolean;
  static: StaticTwinState;
  dynamic: DynamicTwinState;
  prediction: PredictionState | null;
}

export interface WebSocketEvent {
  event: string;
  twin_id: string;
  timestamp?: string;
  data?: TwinSnapshot;
}

export interface ExplanationFeature {
  feature: string;
  value: number;
  contribution: number;
  direction: 'up' | 'down';
}

export interface ExplanationResponse {
  twin_id: string;
  timestamp: string;
  prediction_target: string;
  predicted_value: number;
  base_value: number;
  top_features: ExplanationFeature[];
  clinical_context: Record<string, any>;
}

export interface WhatIfScenario {
  name: string;
  carbs_g: number;
  activity_level: string;
}

export interface TrajectoryPoint {
  time_offset_min: number;
  glucose: number;
}

export interface WhatIfResult {
  scenario_name: string;
  peak_glucose: number;
  time_to_peak_min: number;
  glucose_120m: number;
  delta_120m_vs_baseline: number;
  trajectory: TrajectoryPoint[];
}

export interface WhatIfResponse {
  twin_id: string;
  baseline: WhatIfResult;
  scenarios: WhatIfResult[];
  disclaimer: string;
}
