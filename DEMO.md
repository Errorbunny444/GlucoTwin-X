# GlucoTwin-X Competition Demo Launcher

Follow these steps to launch the entire end-to-end demo of the GlucoTwin-X project.

## 1. Start FastAPI Backend
Open a terminal in the project root:
```bash
# Activate virtual environment
.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate  # Mac/Linux

# Start Backend
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
Verify: Backend is running when `http://localhost:8000/api/health` returns `status: ok`.

## 2. Start React Dashboard
Open a second terminal in the project root:
```bash
cd frontend
npm run dev
```
Verify: Open `http://localhost:5173` in your browser. The React dashboard should load. Select `DT-01`.

## 3. Start Unity 3D Twin
Open the `unity/` folder as a project in the Unity Hub (using your installed stable URP-compatible version).
1. Open the scene `GlucoTwinVisualization`.
2. Press the **Play** button.
3. Verify: The floating UI should say "CONNECTED" and display the current DT-01 state.

## 4. Run the Live Demo Sequence
1. **Introduce Patient**: Show the React dashboard static profile for DT-01.
2. **Current State**: Show the live streaming glucose metrics.
3. **Live Replay**: Click the "Play" icon button in the React header to start the real-time replay engine. Both React and Unity will now update dynamically.
4. **Explainability**: Switch focus to the SHAP panel to show ML interpretation of the risk score.
5. **3D Twin**: Show the Unity scene visually responding to the ML states (glucose particles accelerating, pancreas glowing on high risk).
6. **What-If Simulation**: In the React dashboard, run a 60g carb scenario to simulate the physiological ODE alternative future.
