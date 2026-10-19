# What-If Simulation

## Purpose
The What-If Simulation Engine empowers clinicians and researchers to explore hypothetical metabolic futures for a specific patient. By "branching" the current Digital Twin state, users can input varying hypothetical events (like meals or activity) to simulate their physiological impact without requiring physical patient experimentation.

## Forecast vs What-If Difference
**CRITICAL DISTINCTION:**
- **Forecast (XGBoost ML)**: Answers *"Given what we know right now, what is likely to happen?"* It is strictly based on observed historical data up to the current moment. It does NOT know about future meals.
- **What-If (Physiological ODEs)**: Answers *"What could the simplified physiological model simulate under this specified scenario?"* It explicitly accepts hypothetical future inputs (e.g., a planned meal) and mechanically simulates the physiological response.

Never mix these concepts. The forecast tells you where the patient is currently heading; the What-If simulation tells you how an intervention might alter that course.

## Inputs
The engine is intentionally constrained to a small, robust set of actionable inputs to avoid overfitting the physiological surrogate.
Supported inputs:
- **Meal Carbohydrates**: Grams of carbohydrates (0–120g).
- **Activity Level**: Simple categorical modifier (`low`, `moderate`, `high`). 

Internal constants (like insulin clearance or baseline glucose) are automatically personalized via the EHR context and hidden from the user interface.

## Baseline Scenario
Every What-If simulation inherently includes a **Baseline** scenario. This represents the trajectory if the patient takes *no new action* (0g carbs, low activity). All alternate scenarios are plotted and compared against this Baseline to provide meaningful context.

## Alternate Scenario Branching
A user may simulate 2-4 scenarios simultaneously for comparison. 
Example branches:
- Baseline (0g)
- 30g Meal
- 60g Meal
- 60g Meal + Moderate Activity

## Outputs
For each scenario, the engine calculates:
- A 120-minute continuous simulated glucose trajectory
- Peak simulated glucose
- Time to peak
- Expected glucose at 120 minutes
- Absolute delta vs the Baseline at 120 minutes

## Limitations
This simulation is driven by a reduced-order Bergman-inspired minimal model surrogate (Python RK45 solver matching the intended MATLAB `.m` equations). It captures primary carbohydrate-insulin dynamics but does not model complex phenomena like gastroparesis, complex macronutrient delays (fat/protein), or precise endogenous beta-cell failure states. 

## Safety Disclaimer
Every generated result embeds the following safety contract:
> *Simulated research scenario based on a simplified physiological model. Not a clinical recommendation or treatment prediction.*
