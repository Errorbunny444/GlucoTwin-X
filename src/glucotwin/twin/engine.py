import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
from dataclasses import asdict

from src.glucotwin.twin.state import StaticTwinState, DynamicTwinState, PredictionState, DigitalTwinState
from src.glucotwin.features.glucose_forecasting import build_patient_features
from src.glucotwin.explainability.shap_explainer import TwinExplainer
from src.glucotwin.physiology.what_if import WhatIfScenario, run_what_if_scenarios

project_root = Path(__file__).resolve().parent.parent.parent.parent

logger = logging.getLogger(__name__)

class DigitalTwinEngine:
    def __init__(self, twin_id: str):
        self.twin_id = twin_id
        
        # Load static profile
        static_path = project_root / "data" / "processed" / "twin_static_profiles.csv"
        df_static = pd.read_csv(static_path)
        if twin_id not in df_static['digital_twin_id'].values:
            raise ValueError(f"Invalid Twin ID: {twin_id}")
            
        self.df_static = df_static[df_static['digital_twin_id'] == twin_id].copy()
        s = self.df_static.iloc[0]
        
        self.static_state = StaticTwinState(
            twin_id=twin_id,
            age=float(s.get('age', 0)),
            gender=str(s.get('gender', 'Unknown')),
            bmi=float(s.get('bmi', 0)),
            hba1c=float(s.get('hba1c', 0)),
            fasting_glucose=float(s.get('fasting_glucose', 0)),
            fasting_insulin=float(s.get('fasting_insulin', 0)),
            cholesterol=float(s.get('cholesterol', 0)),
            hdl=float(s.get('hdl', 0)),
            ldl=float(s.get('ldl', 0)),
            triglycerides=float(s.get('triglycerides', 0)),
            ehr_has_hypertension=float(s.get('has_hypertension', 0)),
            ehr_has_dyslipidemia=float(s.get('has_dyslipidemia', 0)),
            ehr_has_diabetes_medication=float(s.get('has_diabetes_medication', 0)),
            ehr_has_insulin=float(s.get('has_insulin', 0))
        )
        
        # Format gender for features mapping
        self.df_static['gender'] = self.df_static['gender'].map({'M': 1.0, 'F': 0.0, 'Male': 1.0, 'Female': 0.0, 1: 1.0, 0: 0.0}).astype(float)
        
        # Load models
        models_dir = project_root / "artifacts" / "models"
        
        with open(models_dir / "final_model_metadata.json", "r") as f:
            self.metadata = json.load(f)
            
        self.features_order = self.metadata['feature_order']
        self.alert_threshold = self.metadata['chosen_threshold']
        self.lower_90 = self.metadata['prediction_interval_bounds']['lower_residual']
        self.upper_90 = self.metadata['prediction_interval_bounds']['upper_residual']
        
        self.regressor = xgb.XGBRegressor()
        self.regressor.load_model(models_dir / "glucose_regressor_final.json")
        
        with open(models_dir / "high_glucose_classifier_final.pkl", "rb") as f:
            self.classifier = pickle.load(f)
            
        self.explainer = None # Lazy load
        self.last_feature_vector = None
            
        # Buffers
        self.history_cgm = []
        self.history_meals = []
        self.history_activity = []
        self.predictions_log = []
        self.alert_transitions = []
        
        self.current_timestamp = None
        self.last_risk_state = False
        
        self.MAX_HISTORY_MINUTES = 240
        logger.debug(f"Initialized Twin: {twin_id}")
        
    def _prune_buffers(self, current_time: datetime):
        cutoff = current_time - timedelta(minutes=self.MAX_HISTORY_MINUTES)
        self.history_cgm = [x for x in self.history_cgm if x['timestamp'] >= cutoff]
        self.history_meals = [x for x in self.history_meals if x['timestamp'] >= cutoff]
        self.history_activity = [x for x in self.history_activity if x['timestamp'] >= cutoff]
        
    def update(self, timestamp: datetime, glucose: Optional[float] = None, 
               meal: Optional[Dict[str, float]] = None, 
               activity: Optional[Dict[str, float]] = None):
        """Accept new dynamic observations."""
        self.current_timestamp = timestamp
        
        if glucose is not None:
            self.history_cgm.append({'timestamp': timestamp, 'glucose': glucose})
        if meal is not None:
            meal_record = {'timestamp': timestamp}
            meal_record.update(meal)
            self.history_meals.append(meal_record)
        if activity is not None:
            act_record = {'timestamp': timestamp}
            act_record.update(activity)
            self.history_activity.append(act_record)
            
        self._prune_buffers(timestamp)

    def is_prediction_ready(self) -> bool:
        if not self.history_cgm:
            return False
        first_cgm = self.history_cgm[0]['timestamp']
        if (self.current_timestamp - first_cgm).total_seconds() / 60 < 120:
            return False
        return True
        
    def predict(self) -> Optional[PredictionState]:
        if not self.is_prediction_ready():
            return None
            
        df_cgm = pd.DataFrame(self.history_cgm)
        df_meals = pd.DataFrame(self.history_meals) if self.history_meals else pd.DataFrame()
        df_act = pd.DataFrame(self.history_activity) if self.history_activity else pd.DataFrame()
        
        df_features = build_patient_features(
            self.twin_id, 
            df_cgm, 
            df_meals, 
            df_act, 
            self.df_static, 
            is_online=True, 
            online_timestamp=self.current_timestamp
        )
        
        if df_features.empty:
            return None
            
        for col in self.features_order:
            if col not in df_features.columns:
                raise ValueError(f"Feature schema mismatch: missing {col}")
                
        X = df_features[self.features_order].copy()
        for col in X.columns:
            if str(X[col].dtype) in ['object', 'string', 'bool']:
                try:
                    X[col] = X[col].astype(float)
                except ValueError:
                    pass
                    
        if pd.isna(X.iloc[0]['current_glucose']) or pd.isna(X.iloc[0]['glucose_120m_ago']):
            return None
            
        pred_glucose = float(self.regressor.predict(X)[0])
        prob_high = float(self.classifier.predict_proba(X)[0, 1])
        
        is_high_risk = prob_high >= self.alert_threshold
        
        lower_bound = max(0.0, pred_glucose + self.lower_90)
        upper_bound = pred_glucose + self.upper_90
        
        pred_state = PredictionState(
            prediction_timestamp=self.current_timestamp,
            predicted_glucose_120m=pred_glucose,
            lower_90=lower_bound,
            upper_90=upper_bound,
            high_glucose_probability=prob_high,
            high_glucose_risk=is_high_risk,
            alert_threshold=self.alert_threshold
        )
        
        self.last_feature_vector = X.copy()
        
        if self.last_risk_state != is_high_risk:
            self.alert_transitions.append({
                'timestamp': self.current_timestamp.isoformat(),
                'previous_state': self.last_risk_state,
                'new_state': is_high_risk,
                'probability': prob_high,
                'predicted_glucose': pred_glucose
            })
            self.last_risk_state = is_high_risk
            
        self.predictions_log.append(pred_state)
        return pred_state

    def explain_current_prediction(self) -> Optional[Dict[str, Any]]:
        if self.last_feature_vector is None:
            return None
            
        if self.explainer is None:
            self.explainer = TwinExplainer()
            
        explanation = self.explainer.explain_prediction(self.last_feature_vector)
        
        explanation["clinical_context"] = {
            "age": self.static_state.age,
            "bmi": self.static_state.bmi,
            "hba1c": self.static_state.hba1c,
            "diabetes_medication": bool(self.static_state.ehr_has_diabetes_medication)
        }
        
        return explanation

    def get_snapshot(self) -> DigitalTwinState:
        status = "warming_up" if not self.is_prediction_ready() else "active"
        current_g = self.history_cgm[-1]['glucose'] if self.history_cgm else None
        
        mins_since_meal = None
        if self.history_meals:
            mins_since_meal = (self.current_timestamp - self.history_meals[-1]['timestamp']).total_seconds() / 60
            
        hr = self.history_activity[-1]['heart_rate'] if self.history_activity else None
        
        trend = "Stable"
        if len(self.history_cgm) > 2:
            g1 = self.history_cgm[-1]['glucose']
            g2 = self.history_cgm[-3]['glucose'] # 10m ago if 5m freq
            trend = "Rising" if g1 - g2 > 5 else "Falling" if g1 - g2 < -5 else "Stable"
            
        dyn = DynamicTwinState(
            current_timestamp=self.current_timestamp or datetime.now(),
            current_glucose=current_g,
            glucose_trend=trend,
            heart_rate=hr,
            minutes_since_last_meal=mins_since_meal,
            recent_carbs_120m=None 
        )
        
        pred = self.predictions_log[-1] if self.predictions_log else None
        
        return DigitalTwinState(
            twin_id=self.twin_id,
            timestamp=self.current_timestamp or datetime.now(),
            status=status,
            prediction_ready=self.is_prediction_ready(),
            static=self.static_state,
            dynamic=dyn,
            prediction=pred
        )

    def run_what_if(self, scenarios: List[WhatIfScenario]) -> Dict[str, Any]:
        """
        Run hypothetical what-if scenarios from the current twin state.
        """
        snapshot = self.get_snapshot()
        return run_what_if_scenarios(asdict(snapshot), scenarios)
