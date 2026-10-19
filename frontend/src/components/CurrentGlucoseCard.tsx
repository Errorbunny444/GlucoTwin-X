import type { DynamicTwinState } from '../types';
import { Heart, TrendingUp, TrendingDown, Minus } from 'lucide-react';

export function CurrentGlucoseCard({ dynamic, timestamp }: { dynamic: DynamicTwinState | null, timestamp: string | undefined }) {
  if (!dynamic) {
    return <div className="p-6 bg-gray-800 rounded shadow animate-pulse h-32"></div>;
  }

  const getTrendIcon = () => {
    switch (dynamic.glucose_trend) {
      case 'Rising': return <TrendingUp className="text-orange-400" size={18} />;
      case 'Falling': return <TrendingDown className="text-blue-400" size={18} />;
      default: return <Minus className="text-gray-400" size={18} />;
    }
  };

  return (
    <div className="p-6 bg-gray-800 rounded shadow flex flex-col justify-between">
      <div className="text-gray-400 text-sm font-medium mb-2 uppercase tracking-wide">Current Glucose</div>
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-4xl font-bold text-white">
          {dynamic.current_glucose !== null ? dynamic.current_glucose.toFixed(1) : '--'}
        </span>
        <span className="text-gray-400">mg/dL</span>
      </div>
      <div className="grid grid-cols-2 gap-4 text-sm text-gray-300">
        <div className="flex items-center gap-2">
          {getTrendIcon()}
          <span>{dynamic.glucose_trend}</span>
        </div>
        <div className="flex items-center gap-2">
          <Heart className="text-red-400" size={16} />
          <span>{dynamic.heart_rate ? `${dynamic.heart_rate} bpm` : '--'}</span>
        </div>
        <div className="col-span-2 text-xs text-gray-500 mt-2">
          Last update: {timestamp ? new Date(timestamp).toLocaleTimeString() : '--'}
        </div>
      </div>
    </div>
  );
}
