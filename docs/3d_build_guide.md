# GlucoTwin-X 3D Build Guide

This guide details the automated one-click workflow for constructing the final Metabolic 3D Digital Twin environment. Because the actual 3D visual fidelity depends on locally executed CAD and Unity software, this automated workflow brings you from zero to a playing visualization in minutes.

## Prerequisites
- **Autodesk Fusion 360** (Tested Version: Local webdeploy install)
- **Unity Editor** (Version: 2022.3.20f1 or any stable URP compatible)
- **FastAPI Environment** (Backend must be running on `localhost:8000`)

## Step 1: Generate CAD Assets (Fusion 360)
*If you already have final custom meshes, you can skip this step and place them in `unity/Assets/Game/Models/Fusion360/`.*

1. Open Autodesk Fusion 360.
2. Create a **New Design**.
3. Press `Shift + S` to open the **Scripts and Add-Ins** window.
4. Click the green `+` next to **My Scripts**. Select the folder `GlucoTwin-X/cad/fusion360/scripts/GlucoTwinGenerator`.
5. Select `GlucoTwinGenerator` and click **Run**.
6. The script will automatically generate the Pancreas, Stomach, Intestine, and Bloodstream profiles, and export them as FBX models to `cad/fusion360/exports/`.

## Step 2: Build Unity Scene
1. Open the `unity/` folder in Unity Hub.
2. If this is the first open, wait for the Unity package manager to initialize.
3. In the top toolbar, click **GlucoTwin-X > Build Final 3D Twin Scene**.
4. The editor will automatically:
   - Create `GlucoTwinVisualization.unity`
   - Setup cameras and lighting.
   - Import the exported CAD meshes.
   - Generate materials (`BodyTransparent`, `HighRiskEmphasis`, etc.).
   - Assemble `DigitalTwinPatient.prefab`.
   - Setup the UI and Particle flow logic.
   - Wire all REST/WebSocket backend C# scripts to the hierarchy.
5. In the top toolbar, click **GlucoTwin-X > Validate 3D Twin**. Ensure the console prints a green success message.

## Step 3: Run the Digital Twin
1. Ensure the Python backend is running.
2. In Unity, open `Assets/Game/Scenes/GlucoTwinVisualization.unity`.
3. Press **Play**. 
4. The twin will connect and display live data mirrored perfectly from the FastAPI / React environment.
