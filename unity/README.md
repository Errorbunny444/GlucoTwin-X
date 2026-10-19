# GlucoTwin-X Unity Visualizer

This folder contains the Unity project for the 3D Metabolic Digital Twin visualization.

## Requirements
- Unity Editor (Use the latest stable installed version, preferably configured with URP).
- GlucoTwin-X FastAPI backend running on port `8000`.

## Quick Start
1. Open this `unity/` folder in Unity Hub.
2. Ensure the backend is running (`uvicorn app.main:app --reload` from `backend/`).
3. Open the scene `GlucoTwinVisualization` (create a new empty scene and name it this if it doesn't exist, then attach the scripts).
4. Create a UI Canvas with TextMeshPro objects for Twin ID, Glucose, Prediction, Risk, and Connection Status.
5. Create a `DigitalTwinPatient` GameObject and attach `TwinVisualController`, `TwinApiClient`, and `TwinWebSocketClient`. Link the UI elements and sub-controllers.
6. Press **Play**.

## Features
- Connects automatically to DT-01.
- Listens to WebSockets for real-time replay data.
- Visualizes glucose flow using Unity Particle Systems.
- Highlights the pancreas based on ML Risk state.

## Note on Mock Mode
If the backend is not available, check `UseMockData` on the `TwinVisualController` to test the visual materials and animations statically. **Ensure this is OFF during the final live demo.**
