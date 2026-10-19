import type { PredictionState } from '../types';
import clsx from 'clsx';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

export function PredictionCard({ prediction }: { prediction: PredictionState | null }) {
  if (!prediction) {
    return (
      <div className="p-6 bg-gray-800 rounded shadow flex flex-col justify-center items-center h-32 text-gray-500">
        Waiting for prediction...
      </div>
    );
  }

  const isHighRisk = prediction.high_glucose_risk;
  const riskPct = (prediction.high_glucose_probability * 100).toFixed(0);

  return (
    <div className={clsx(
      "p-6 rounded shadow flex flex-col justify-between transition-colors duration-500",
      isHighRisk ? "bg-red-900/40 border border-red-700/50" : "bg-gray-800"
    )}>
      <div className="text-gray-400 text-sm font-medium mb-2 uppercase tracking-wide">
        +120 Minute Forecast
      </div>
      
      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-4xl font-bold text-white">
          {prediction.predicted_glucose_120m.toFixed(1)}
        </span>
        <span className="text-gray-400">mg/dL</span>
      </div>
      
      <div className="text-xs text-gray-500 mb-4">
        90% Interval: {prediction.lower_90.toFixed(0)} &ndash; {prediction.upper_90.toFixed(0)} mg/dL
      </div>
      
      <div className="border-t border-gray-700 pt-4 mt-auto">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-gray-400 uppercase">Risk</div>
            <div className="text-xl font-semibold text-white">{riskPct}%</div>
          </div>
          <div className={clsx(
            "flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium",
            isHighRisk ? "bg-red-500/20 text-red-400" : "bg-emerald-500/20 text-emerald-400"
          )}>
            {isHighRisk ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
            {isHighRisk ? "HIGH RISK" : "NORMAL"}
          </div>
        </div>
      </div>
    </div>
  );
}
