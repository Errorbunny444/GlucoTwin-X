import pandas as pd
import time
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional, Dict, Any, List

from src.glucotwin.twin.engine import DigitalTwinEngine
from src.glucotwin.twin.state import DigitalTwinState

logger = logging.getLogger(__name__)

class TwinReplay:
    def __init__(self, twin_id: str, df_cgm: pd.DataFrame, df_meals: pd.DataFrame, df_activity: pd.DataFrame):
        self.twin_id = twin_id
        self.engine = DigitalTwinEngine(twin_id)
        
        self.df_cgm = df_cgm.sort_values('timestamp').reset_index(drop=True) if df_cgm is not None else pd.DataFrame()
        self.df_meals = df_meals.sort_values('timestamp').reset_index(drop=True) if df_meals is not None else pd.DataFrame()
        self.df_activity = df_activity.sort_values('timestamp').reset_index(drop=True) if df_activity is not None else pd.DataFrame()
        
        self.events = self._build_event_queue()
        self.ground_truth = self._build_ground_truth()
        
    def _build_event_queue(self):
        events = []
        if not self.df_cgm.empty:
            for _, row in self.df_cgm.iterrows():
                events.append({
                    'timestamp': row['timestamp'],
                    'type': 'cgm',
                    'data': {'glucose': row['glucose']}
                })
        if not self.df_meals.empty:
            for _, row in self.df_meals.iterrows():
                events.append({
                    'timestamp': row['timestamp'],
                    'type': 'meal',
                    'data': {
                        'carbohydrate_g': row['carbohydrate_g'],
                        'protein_g': row['protein_g'],
                        'fat_g': row['fat_g'],
                        'fiber_g': row['fiber_g'],
                        'calories': row.get('calories', 0)
                    }
                })
        if not self.df_activity.empty:
            for _, row in self.df_activity.iterrows():
                events.append({
                    'timestamp': row['timestamp'],
                    'type': 'activity',
                    'data': {
                        'heart_rate': row['heart_rate'],
                        'activity_calories': row.get('activity_calories', 0)
                    }
                })
        
        events.sort(key=lambda x: x['timestamp'])
        return events
        
    def _build_ground_truth(self) -> pd.DataFrame:
        if self.df_cgm.empty:
            return pd.DataFrame()
        cgm = self.df_cgm[['timestamp', 'glucose']].copy()
        cgm.set_index('timestamp', inplace=True)
        return cgm

    def get_actual_glucose(self, target_time: datetime) -> Optional[float]:
        # Lookup closest within 5 minutes
        if self.ground_truth.empty:
            return None
        idx = self.ground_truth.index.get_indexer([target_time], method='nearest')
        if idx[0] == -1:
            return None
        closest_time = self.ground_truth.index[idx[0]]
        if abs((closest_time - target_time).total_seconds()) <= 300:
            return float(self.ground_truth.iloc[idx[0]]['glucose'])
        return None

    def run(self, speed_multiplier: float = 0, prediction_stride_minutes: int = 5, verbose: bool = False, print_func=print) -> List[Dict[str, Any]]:
        last_predict_time = None
        results = []
        
        start_real = time.time()
        
        for event in self.events:
            ts = event['timestamp']
            
            if event['type'] == 'cgm':
                self.engine.update(timestamp=ts, glucose=event['data']['glucose'])
            elif event['type'] == 'meal':
                self.engine.update(timestamp=ts, meal=event['data'])
                if verbose:
                    print_func(f"[{ts}] MEAL_RECORDED: {event['data']['carbohydrate_g']}g carbs")
            elif event['type'] == 'activity':
                self.engine.update(timestamp=ts, activity=event['data'])

            # Predict on 5-min boundaries ideally, or stride based on CGM events
            if event['type'] == 'cgm':
                if last_predict_time is None or (ts - last_predict_time).total_seconds() / 60 >= prediction_stride_minutes:
                    if self.engine.is_prediction_ready():
                        if last_predict_time is None and verbose:
                            print_func(f"[{ts}] WARMUP_COMPLETE")
                            
                        pred = self.engine.predict()
                        last_predict_time = ts
                        
                        if pred:
                            actual_120m = self.get_actual_glucose(pred.prediction_timestamp + pd.Timedelta(minutes=120))
                            
                            res = {
                                'timestamp': pred.prediction_timestamp,
                                'current_glucose': self.engine.history_cgm[-1]['glucose'],
                                'predicted_glucose_120m': pred.predicted_glucose_120m,
                                'actual_glucose_120m': actual_120m,
                                'lower_90': pred.lower_90,
                                'upper_90': pred.upper_90,
                                'high_glucose_probability': pred.high_glucose_probability,
                                'high_glucose_risk': pred.high_glucose_risk
                            }
                            results.append(res)
                            
                            if verbose:
                                state_str = "HIGH RISK" if pred.high_glucose_risk else "NORMAL"
                                actual_str = f"{actual_120m:.1f}" if actual_120m else "Unknown"
                                print_func(f"\n--- Digital Twin: {self.twin_id} @ {ts} ---")
                                print_func(f"Current glucose: {res['current_glucose']} mg/dL")
                                print_func(f"Predicted glucose (+120m): {pred.predicted_glucose_120m:.1f} mg/dL")
                                print_func(f"Actual glucose (+120m): {actual_str} mg/dL")
                                print_func(f"90% interval: {pred.lower_90:.1f} - {pred.upper_90:.1f} mg/dL")
                                print_func(f"Risk state: {state_str} (p={pred.high_glucose_probability:.3f})")
                                
                    if speed_multiplier > 0:
                        # calculate sleep to mimic speed
                        pass # Skipping actual sleep for demo purposes unless needed
                        
        end_real = time.time()
        if verbose:
            print_func(f"\nReplay complete. Processing time: {end_real - start_real:.2f} seconds.")
            
        return results
