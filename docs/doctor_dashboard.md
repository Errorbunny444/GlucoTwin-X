# React Doctor Dashboard

The GlucoTwin-X React Doctor Dashboard is a modern, single-page application built to allow clinical researchers to interact with the Digital Twin models in real-time.

## Patient Overview
Located in the top left, this provides key demographic and baseline metabolic information for the active twin (Age, Gender, BMI, HbA1c, and broad EHR context). 

## Current State
A highly visible card showing the twin's most recent glucose reading, heart rate, and overall directional trend. It serves as the immediate snapshot of what is happening right now.

## Prediction
A critical component displaying the ML-driven +120 minute glucose forecast. It features the empirical 90% prediction interval and the translated probability of high-glucose risk, visually highlighted to clearly delineate NORMAL from HIGH RISK states.

## Explainability
The "Why is risk changing?" panel connects to the backend SHAP explainer. It parses the top 5 directional features influencing the current prediction, allowing users to rapidly interpret the complex multimodal ML model.

## What-If Simulation
The Twin Lab allows interactive hypothesis testing. Users can define a hypothetical future meal (carbohydrates) and physical activity level. The backend physiological model will simulate this scenario against the baseline forecast, plotting both trajectories in the UI to demonstrate potential metabolic outcomes.

## Replay Controls
For demonstration purposes, users can start or stop a historical replay stream, simulating real-time continuous data flow from the CGM and wearable sensors.

## Unity Digital Twin (Phase 7)
A designated placeholder panel rests on the right-hand side, prepared to embed the upcoming 3D WebGL Unity Digital Twin visualization.
