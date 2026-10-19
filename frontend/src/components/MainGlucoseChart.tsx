
import { Area, AreaChart, CartesianGrid, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export function MainGlucoseChart({ history, prediction }: { history: any[], prediction: any }) {
  if (!history || history.length === 0) {
    return <div className="p-4 bg-gray-800 rounded shadow h-64 flex items-center justify-center text-gray-500">Loading chart...</div>;
  }

  // Format data
  const data = history.map(d => ({
    time: new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    glucose: d.glucose,
    isPrediction: false
  }));

  // Add prediction if available
  if (prediction) {
    // Insert empty gap if needed or just add point
    data.push({
      time: new Date(prediction.prediction_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), // wait, prediction_timestamp is the time it was MADE, but the TARGET is +120
      glucose: prediction.predicted_glucose_120m,
      isPrediction: true
    });
  }

  return (
    <div className="p-4 bg-gray-800 rounded shadow h-80 flex flex-col">
      <h3 className="text-sm font-medium text-gray-400 uppercase mb-4">Glucose Timeline</h3>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorGlucose" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
            <XAxis dataKey="time" stroke="#9ca3af" fontSize={12} tickMargin={10} />
            <YAxis stroke="#9ca3af" fontSize={12} domain={['dataMin - 20', 'dataMax + 20']} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '4px', color: '#f3f4f6' }}
              itemStyle={{ color: '#60a5fa' }}
            />
            <Area 
              type="monotone" 
              dataKey="glucose" 
              stroke="#3b82f6" 
              strokeWidth={2}
              fillOpacity={1} 
              fill="url(#colorGlucose)" 
              isAnimationActive={false}
            />
            {prediction && (
              <ReferenceDot 
                x={data[data.length - 1].time} 
                y={prediction.predicted_glucose_120m} 
                r={5} 
                fill="#f87171" 
                stroke="none" 
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
