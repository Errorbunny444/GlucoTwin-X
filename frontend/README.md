# GlucoTwin-X Dashboard

This is the React Doctor Dashboard for the GlucoTwin-X Digital Twin project.

## Install

```bash
npm install
```

## Run

```bash
npm run dev
```

## Required backend URL

By default, Vite proxies `/api` and `/ws` to `http://localhost:8000`. Ensure the FastAPI backend is running before starting the frontend.

## Main Functionality

- Real-time metabolic Digital Twin WebSocket streaming
- ML-driven 2-hour glucose forecasting with empirical intervals
- SHAP-based risk explainability 
- Interactive What-If simulation engine (Carbohydrates & Activity)
