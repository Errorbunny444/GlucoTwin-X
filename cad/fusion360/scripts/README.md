# GlucoTwin-X Fusion 360 Generator

## Instructions

This folder contains the automated Python script for Autodesk Fusion 360 to generate the simplified metabolic anatomy kit.

### Prerequisites
- Autodesk Fusion 360 installed.

### How to Run
1. Open Fusion 360.
2. Create a new empty design.
3. Press `Shift + S` or go to **Utilities > Scripts and Add-Ins**.
4. Click the green `+` icon next to **My Scripts** and select the folder `GlucoTwin-X/cad/fusion360/scripts/GlucoTwinGenerator`.
5. Select `GlucoTwinGenerator` in the list and click **Run**.

The script will automatically:
- Generate the Pancreas, Stomach, Intestine, and Bloodstream profiles and features.
- Export `.fbx` (or `.obj` fallback) files to the `cad/fusion360/exports/` directory.
- Attempt to save the Fusion design file.

Once exported, you can proceed to use the Unity Editor script to automatically import and build the 3D Twin scene.
