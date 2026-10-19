import { useEffect, useState } from 'react';
import type { ExplanationResponse } from '../types';
import { apiClient } from '../api/client';
import { ArrowDown, ArrowUp } from 'lucide-react';

export function ShapPanel({ twinId, updateTrigger }: { twinId: string, updateTrigger: number }) {
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    const fetchExp = async () => {
      setLoading(true);
      try {
        const res = await apiClient.getExplanation(twinId);
        if (active) setExplanation(res);
      } catch (e) {
        console.error(e);
      } finally {
        if (active) setLoading(false);
      }
    };
    // Debounce or only fetch occasionally
    fetchExp();
    return () => { active = false; };
  }, [twinId, updateTrigger]); // Trigger when risk changes or periodically

  if (loading && !explanation) {
    return <div className="p-4 bg-gray-800 rounded shadow h-48 animate-pulse"></div>;
  }

  if (!explanation || !explanation.top_features) {
    return (
      <div className="p-4 bg-gray-800 rounded shadow h-48 flex items-center justify-center text-gray-500 text-sm">
        Explanation unavailable
      </div>
    );
  }

  return (
    <div className="p-4 bg-gray-800 rounded shadow">
      <h3 className="text-sm font-medium text-gray-400 uppercase mb-4">Why is risk changing?</h3>
      <div className="space-y-3">
        {explanation.top_features.map((feat, idx) => (
          <div key={idx} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {feat.direction === 'up' ? (
                <ArrowUp size={16} className="text-red-400" />
              ) : (
                <ArrowDown size={16} className="text-emerald-400" />
              )}
              <span className="text-sm text-gray-200">{feat.feature}</span>
            </div>
            <div className="text-xs text-gray-500">
              Val: {typeof feat.value === 'number' ? feat.value.toFixed(1) : feat.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
