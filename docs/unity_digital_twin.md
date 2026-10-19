# Unity 3D Metabolic Digital Twin

This document describes the Phase 6 Unity visual implementation of the GlucoTwin-X Digital Twin, including the automated CAD pipeline.

## Purpose
The Unity scene (`GlucoTwinVisualization`) is designed to answer "Can I SEE the Digital Twin changing?". It is a strictly visual consumer of the FastAPI backend. It does NOT simulate physiology or run ML models natively; it mirrors the state of the React dashboard in real-time.

## Symbolic Nature
The Unity visuals are a **symbolic representation of metabolic Digital Twin state**.
- Glucose particle density does not equal an actual molecule count.
- Pancreas glowing/pulsing does not imply literal physical pancreatic damage, but rather a transition in the ML risk classification state.
- The bloodstream and organ paths are stylized for readable communication, not surgical anatomical accuracy.

## Automated Architecture Pipeline

### Fusion 360 Generation
A Python API script (`cad/fusion360/scripts/GlucoTwinGenerator/GlucoTwinGenerator.py`) automates the creation of a simplified metabolic anatomy kit. It generates sketches and profiles for the Pancreas, Stomach, Intestine, and Bloodstream path.

### Export Workflow
The Fusion script automatically invokes the export manager to dump `.fbx` models (with `.obj` fallback) into `cad/fusion360/exports/`.

### Automatic Scene Builder
To avoid manual dragging and dropping, the `GlucoTwinSceneBuilder.cs` editor script reconstructs the entire 3D environment programmatically via `GlucoTwin-X > Build Final 3D Twin Scene`. It loads the CAD meshes, creates necessary GameObjects, assigns the `TwinVisualController`, and serializes the final `DigitalTwinPatient.prefab`.

## Scene Hierarchy
- **DigitalTwinPatient (Prefab)**
  - `Body` (Semi-transparent full-body mesh placeholder)
  - `MetabolicSystem`
    - `Stomach` (Handles `meal_recorded` glowing events)
    - `Pancreas` (Reacts to High-Risk and Rising trends)
    - `Intestine`
    - `Bloodstream` (Spline/mesh pathway)
  - `GlucoseParticles` (ParticleSystem mapping glucose levels to density/speed)
  - `Controllers`
    - `TwinApiClient.cs` (REST snapshot fetching)
    - `TwinWebSocketClient.cs` (Live data streaming)
    - `TwinVisualController.cs` (State mapping & UI binding)

## Backend Integration
The Unity app connects to the same FastAPI backend (`http://localhost:8000`) used by the React Dashboard. 
1. The `TwinApiClient` fires a REST GET request on startup to fetch the latest `TwinSnapshotDto`.
2. The `TwinWebSocketClient` opens a persistent `ClientWebSocket` connection to `/ws/twins/{TwinId}` to stream changes.

## Visual State Mapping
- **Stable**: Baseline glucose particle emission. Pancreas uses neutral `PancreasHighlight` material.
- **Rising**: Glucose particles speed up by 20%. Pancreas emits a subtle amber glow.
- **Falling**: Glucose particles slow down by 20%.
- **High Risk**: Triggered by backend `high_glucose_risk == true`. Pancreas switches to `HighRiskEmphasis` material with an active red pulse. Bloodstream particles tint amber/orange.
- **Warm-Up**: If `prediction_ready == false`, UI shows "WARM UP" and predictions are hidden.

## Runtime Verification & Limitations
As the automated codebase generation executes outside of local GUI interaction limits, **Unity Play Mode execution is currently queued for local run**. The Unity project folder has been initialized with the 2022.3.20f1 version descriptor to allow immediate opening in Unity Hub. All backend synchronization scripts strictly match the FastAPI Python schemas to ensure `JsonUtility` serialization binds cleanly on local execution.
