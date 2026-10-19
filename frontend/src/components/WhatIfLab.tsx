import { useState } from 'react';
import { apiClient } from '../api/client';
import type { WhatIfResponse } from '../types';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export function WhatIfLab({ twinId }: { twinId: string }) {
  const [carbs, setCarbs] = useState<number>(60);
  const [activity, setActivity] = useState<string>('moderate');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WhatIfResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSimulate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.runWhatIf(twinId, carbs, activity);
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  // Prepare chart data
  let chartData: any[] = [];
  if (result && result.baseline && result.scenarios.length > 0) {
    const baseline = result.baseline.trajectory;
    const scenario = result.scenarios[0].trajectory;
    // Assume same time offsets
    chartData = baseline.map((pt, i) => ({
      time: `+${pt.time_offset_min}m`,
      baseline: pt.glucose,
      scenario: scenario[i] ? scenario[i].glucose : null
    }));
  }

  return (
    <div className="p-4 bg-gray-800 rounded shadow flex flex-col gap-4">
      <h3 className="text-sm font-medium text-gray-400 uppercase">What-If Twin Lab</h3>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Carbohydrates (g)</label>
          <input 
            type="range" 
            min="0" max="120" step="5"
            value={carbs}
            onChange={e => setCarbs(parseInt(e.target.value))}
            className="w-full accent-blue-500"
          />
          <div className="text-right text-sm text-gray-200 font-medium mt-1">{carbs} g</div>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Activity Level</label>
          <select 
            value={activity}
            onChange={e => setActivity(e.target.value)}
            className="w-full bg-gray-700 text-white rounded p-2 text-sm border-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="low">Low</option>
            <option value="moderate">Moderate</option>
            <option value="high">High</option>
          </select>
        </div>
      </div>

      <button 
        onClick={handleSimulate}
        disabled={loading}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-medium py-2 rounded transition-colors"
      >
        {loading ? 'Simulating...' : 'Simulate Scenario'}
      </button>

      {error && <div className="text-red-400 text-xs text-center">{error}</div>}

      {result && chartData.length > 0 && (
        <div className="mt-4 border-t border-gray-700 pt-4">
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                <XAxis dataKey="time" stroke="#9ca3af" fontSize={10} tickMargin={5} />
                <YAxis stroke="#9ca3af" fontSize={10} domain={['dataMin - 10', 'dataMax + 10']} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '4px', color: '#f3f4f6' }}
                  itemStyle={{ fontSize: '12px' }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                <Line type="monotone" dataKey="baseline" name="Baseline" stroke="#6b7280" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="scenario" name="Selected Scenario" stroke="#f59e0b" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-4 text-sm">
            <div className="bg-gray-700/50 p-2 rounded">
              <div className="text-gray-400 text-xs uppercase">Baseline +120m</div>
              <div className="text-gray-200 font-semibold">{result.baseline.glucose_120m.toFixed(1)}</div>
            </div>
            <div className="bg-amber-900/20 border border-amber-700/30 p-2 rounded">
              <div className="text-amber-500 text-xs uppercase">Scenario +120m</div>
              <div className="text-amber-400 font-semibold">{result.scenarios[0].glucose_120m.toFixed(1)}</div>
              <div className="text-xs text-gray-400 mt-1">
                Delta: {result.scenarios[0].delta_120m_vs_baseline > 0 ? '+' : ''}{result.scenarios[0].delta_120m_vs_baseline.toFixed(1)}
              </div>
            </div>
          </div>
          <div className="mt-4 text-[10px] text-gray-500 leading-tight italic">
            {result.disclaimer}
          </div>
        </div>
      )}
    </div>
  );
}
