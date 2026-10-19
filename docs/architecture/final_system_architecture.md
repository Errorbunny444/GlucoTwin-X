# Final System Architecture

The complete end-to-end architecture for GlucoTwin-X demonstrates a hybrid approach, uniting data-driven ML forecasting with mechanistic ODE physiological simulation.

```mermaid
flowchart TD
    subgraph Data Foundation
        EHR[Synthea EHR Context]
        CGM[CGMacros Dynamic Streaming]
    end

    subgraph Digital Twin Backend (Python/FastAPI)
        DTL[Digital Twin Data Layer]
        FE[Feature Engineering Pipeline]
        
        XGB[XGBoost Forecasting & Classifier]
        SHAP[SHAP Explainability]
        
        DTE[DigitalTwinEngine]
        Replay[Historical Replay Engine]
        
        Physio[Physiological ODE Surrogate]
        WhatIf[What-If Scenario Simulator]
    end

    subgraph Visualization Clients
        React[React + Vite Doctor Dashboard]
        Unity[Unity 3D Metabolic Twin]
    end

    EHR & CGM --> DTL
    DTL --> FE
    FE --> XGB
    XGB --> SHAP
    XGB --> DTE
    
    DTE <--> Physio
    Physio <--> WhatIf
    Replay --> DTE
    
    DTE -- "REST / WebSocket" --> React
    DTE -- "REST / WebSocket" --> Unity
    WhatIf -- "REST" --> React
```

## Hybrid Concept
1. **Data-Driven (XGBoost)**: Provides the highly accurate 120-minute predictions and risk classification based on the patient's *observed historical reality*.
2. **Mechanistic (ODE Physiology)**: Simulates *explicit hypothetical alternative futures* (the What-If Lab). The Python `solve_ivp` RK45 solver functions as a direct surrogate for the mathematically equivalent MATLAB/Simulink implementation (which is prepared but gated by desktop licensing limitations in this prototype).
