import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import WebSocket
from datetime import datetime
import pandas as pd

from src.glucotwin.twin.engine import DigitalTwinEngine
from src.glucotwin.physiology.what_if import WhatIfScenario

logger = logging.getLogger(__name__)

project_root = Path(__file__).resolve().parent.parent.parent.parent

def _serialize_dt(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

class TwinService:
    def __init__(self):
        self._engines: Dict[str, DigitalTwinEngine] = {}
        self._replay_tasks: Dict[str, asyncio.Task] = {}
        self._websockets: Dict[str, List[WebSocket]] = {}
        
    def get_engine(self, twin_id: str) -> DigitalTwinEngine:
        if twin_id not in self._engines:
            engine = DigitalTwinEngine(twin_id)
            # Try to preload snapshot if available
            snap_path = project_root / "artifacts" / "twin_snapshots" / f"{twin_id}_latest.json"
            if snap_path.exists():
                with open(snap_path, "r") as f:
                    snap_data = json.load(f)
                engine.current_timestamp = datetime.fromisoformat(snap_data["timestamp"])
                engine.static_state = snap_data["static"]
                engine.history_cgm = [{"timestamp": engine.current_timestamp, "glucose": snap_data["dynamic"].get("current_glucose", 100.0)}]
                engine.history_meals = []
                engine.history_activity = []
            self._engines[twin_id] = engine
        return self._engines[twin_id]

    def list_twins(self) -> List[Dict[str, Any]]:
        static_path = project_root / "data" / "processed" / "twin_static_profiles.csv"
        if not static_path.exists():
            return []
        df = pd.read_csv(static_path)
        
        summaries = []
        for _, row in df.iterrows():
            summaries.append({
                "twin_id": row["digital_twin_id"],
                "health_group": "Type-2 Diabetes", # all in cohort
                "age": float(row["age"]),
                "gender": row["gender"],
                "bmi": float(row["bmi"]),
                "hba1c": float(row["hba1c"]),
                "data_duration_days": 10.0, # Approximate
                "completeness": float(row.get("synthea_profile_completeness", 1.0)),
                "demo_role": "Primary Demo" if row["digital_twin_id"] == "DT-01" else None
            })
        return summaries
            
    def get_snapshot(self, twin_id: str) -> Dict[str, Any]:
        from dataclasses import asdict
        engine = self.get_engine(twin_id)
        # convert datetimes
        res = asdict(engine.get_snapshot())
        if "timestamp" in res and isinstance(res["timestamp"], datetime):
            res["timestamp"] = res["timestamp"].isoformat()
        if res.get("prediction") and res["prediction"].get("prediction_timestamp"):
            if isinstance(res["prediction"]["prediction_timestamp"], datetime):
                res["prediction"]["prediction_timestamp"] = res["prediction"]["prediction_timestamp"].isoformat()
        return res

    def get_glucose(self, twin_id: str, minutes: int = 180) -> Dict[str, Any]:
        snap = self.get_snapshot(twin_id)
        return {"glucose": snap.get("dynamic", {}).get("current_glucose")}

    def get_predictions(self, twin_id: str) -> List[Dict[str, Any]]:
        engine = self.get_engine(twin_id)
        from dataclasses import asdict
        return [asdict(p) for p in engine.predictions_log[-10:]]

    def get_explanation(self, twin_id: str) -> Dict[str, Any]:
        engine = self.get_engine(twin_id)
        if not engine.is_prediction_ready():
            return {"error": "Prediction not ready"}
        if not engine.predictions_log:
            engine.predict()
        return engine.explain_current_prediction()

    def run_what_if(self, twin_id: str, carbs_g: float, activity_level: str) -> Dict[str, Any]:
        engine = self.get_engine(twin_id)
        scenarios = [
            WhatIfScenario(name=f"{carbs_g}g {activity_level}", carbs_g=carbs_g, activity_level=activity_level)
        ]
        return engine.run_what_if(scenarios)

    async def start_replay(self, twin_id: str, speed: float = 1.0):
        if twin_id in self._replay_tasks and not self._replay_tasks[twin_id].done():
            return {"status": "already_running"}
            
        task = asyncio.create_task(self._replay_loop(twin_id, speed))
        self._replay_tasks[twin_id] = task
        # give it a tiny sleep to let the task start before returning
        await asyncio.sleep(0.01)
        return {"status": "started"}

    async def stop_replay(self, twin_id: str):
        if twin_id in self._replay_tasks:
            self._replay_tasks[twin_id].cancel()
            del self._replay_tasks[twin_id]
        return {"status": "stopped"}

    def replay_status(self, twin_id: str) -> Dict[str, Any]:
        running = twin_id in self._replay_tasks and not self._replay_tasks[twin_id].done()
        return {"running": running}

    async def _replay_loop(self, twin_id: str, speed: float):
        engine = self.get_engine(twin_id)
        current_time = datetime(2020, 1, 1, 10, 0)
        try:
            for i in range(100):
                current_time += pd.Timedelta(minutes=5)
                engine.update(current_time, glucose=100.0 + (i % 20))
                if engine.is_prediction_ready():
                    engine.predict()
                
                msg = {
                    "event": "snapshot",
                    "twin_id": twin_id,
                    "timestamp": str(current_time),
                    "data": self.get_snapshot(twin_id)
                }
                # using json.dumps to avoid datetime errors
                await self.broadcast(twin_id, json.loads(json.dumps(msg, default=_serialize_dt)))
                
                await asyncio.sleep(1.0 / speed)
        except asyncio.CancelledError:
            logger.info(f"Replay cancelled for {twin_id}")

    # WebSocket Management
    async def connect_ws(self, twin_id: str, websocket: WebSocket):
        await websocket.accept()
        if twin_id not in self._websockets:
            self._websockets[twin_id] = []
        self._websockets[twin_id].append(websocket)
        
        # Send initial snapshot
        msg = {
            "event": "snapshot",
            "twin_id": twin_id,
            "data": self.get_snapshot(twin_id)
        }
        await websocket.send_text(json.dumps(msg, default=_serialize_dt))

    def disconnect_ws(self, twin_id: str, websocket: WebSocket):
        if twin_id in self._websockets and websocket in self._websockets[twin_id]:
            self._websockets[twin_id].remove(websocket)

    async def broadcast(self, twin_id: str, message: dict):
        if twin_id in self._websockets:
            disconnected = []
            for ws in self._websockets[twin_id]:
                try:
                    await ws.send_text(json.dumps(message, default=_serialize_dt))
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                self.disconnect_ws(twin_id, ws)

twin_service = TwinService()
