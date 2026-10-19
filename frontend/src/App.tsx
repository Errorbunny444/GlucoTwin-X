import { useEffect, useState } from 'react';
import { Activity, Play, Square, Wifi, WifiOff } from 'lucide-react';
import { apiClient } from './api/client';
import { useTwinWebSocket } from './hooks/useTwinWebSocket';
import type { TwinSummary } from './types';

import { PatientSummary } from './components/PatientSummary';
import { CurrentGlucoseCard } from './components/CurrentGlucoseCard';
import { PredictionCard } from './components/PredictionCard';
import { MainGlucoseChart } from './components/MainGlucoseChart';
import { ShapPanel } from './components/ShapPanel';
import { WhatIfLab } from './components/WhatIfLab';
import { Metabolic3DTwin } from './components/Metabolic3DTwin';

function App() {
  const [twins, setTwins] = useState<TwinSummary[]>([]);
  const [activeTwinId, setActiveTwinId] = useState<string>('DT-01');
  const [history, setHistory] = useState<any[]>([]);
  const [replayRunning, setReplayRunning] = useState(false);
  const [updateTrigger, setUpdateTrigger] = useState(0);

  const { snapshot, connected } = useTwinWebSocket(activeTwinId);

  useEffect(() => {
    apiClient.getTwins().then(data => {
      setTwins(data);
    }).catch(e => console.error("Failed to load twins", e));
  }, []);

  useEffect(() => {
    if (!activeTwinId) return;
    
    // Load history
    apiClient.getGlucoseHistory(activeTwinId, 180).then(data => {
      // the endpoint currently might return just {"glucose": 110} or array depending on implementation
      // wait, backend currently returns {"glucose": value}. In Prompt 13 we might need to adjust backend or just use it.
      // But prompt 13 says "Do NOT modify FastAPI unless a genuine frontend integration bug requires a very small fix"
      // If history is just {"glucose": ...}, we wrap it in array
      if (Array.isArray(data)) {
        setHistory(data);
      } else if (data.glucose !== undefined) {
        setHistory([{ timestamp: new Date().toISOString(), glucose: data.glucose }]);
      }
    }).catch(e => console.error(e));

    // Load replay status
    apiClient.getReplayStatus(activeTwinId).then(res => {
      setReplayRunning(res.running);
    }).catch(e => console.error(e));

  }, [activeTwinId]);

  // When snapshot updates, we append to history
  useEffect(() => {
    if (snapshot?.dynamic?.current_glucose) {
      setHistory(prev => {
        const newPt = {
          timestamp: snapshot.timestamp,
          glucose: snapshot.dynamic.current_glucose
        };
        // keep last 50 points
        return [...prev, newPt].slice(-50);
      });
      // also trigger SHAP update if prediction state changes
      setUpdateTrigger(prev => prev + 1);
    }
  }, [snapshot]);

  const handleStartReplay = async () => {
    await apiClient.startReplay(activeTwinId, 10.0);
    setReplayRunning(true);
  };

  const handleStopReplay = async () => {
    await apiClient.stopReplay(activeTwinId);
    setReplayRunning(false);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      {/* Top Bar */}
      <header className="bg-gray-900 border-b border-gray-800 p-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <Activity className="text-blue-500" size={24} />
          <div>
            <h1 className="text-lg font-bold leading-tight">GlucoTwin-X</h1>
            <div className="text-xs text-gray-500">Personalized Metabolic Digital Twin</div>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">Select Twin:</span>
            <select 
              value={activeTwinId}
              onChange={e => setActiveTwinId(e.target.value)}
              className="bg-gray-800 border border-gray-700 text-white text-sm rounded focus:ring-blue-500 focus:border-blue-500 p-1.5"
            >
              {twins.map(t => (
                <option key={t.twin_id} value={t.twin_id}>
                  {t.twin_id} {t.demo_role ? `(${t.demo_role})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 bg-gray-800 rounded p-1">
            <button 
              onClick={handleStartReplay}
              disabled={replayRunning}
              className={`p-1.5 rounded ${replayRunning ? 'text-gray-500' : 'text-emerald-400 hover:bg-gray-700'}`}
              title="Start Replay"
            >
              <Play size={16} />
            </button>
            <button 
              onClick={handleStopReplay}
              disabled={!replayRunning}
              className={`p-1.5 rounded ${!replayRunning ? 'text-gray-500' : 'text-red-400 hover:bg-gray-700'}`}
              title="Stop Replay"
            >
              <Square size={16} />
            </button>
            <span className={`text-xs ml-2 mr-2 font-medium ${replayRunning ? 'text-emerald-400' : 'text-gray-500'}`}>
              {replayRunning ? 'LIVE REPLAY' : 'STOPPED'}
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs">
            {connected ? (
              <span className="flex items-center gap-1 text-emerald-400"><Wifi size={14}/> Connected</span>
            ) : (
              <span className="flex items-center gap-1 text-red-400 animate-pulse"><WifiOff size={14}/> Reconnecting...</span>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6 grid grid-cols-12 gap-6 max-w-[1920px] mx-auto w-full">
        
        {/* Left Column (3) */}
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-6">
          <PatientSummary staticState={snapshot?.static || null} />
          <CurrentGlucoseCard dynamic={snapshot?.dynamic || null} timestamp={snapshot?.timestamp} />
          <PredictionCard prediction={snapshot?.prediction || null} />
        </div>

        {/* Middle Column (6) */}
        <div className="col-span-12 lg:col-span-6 flex flex-col gap-6">
          <MainGlucoseChart history={history} prediction={snapshot?.prediction} />
          
          <div className="grid grid-cols-2 gap-6 flex-1 min-h-0">
            <ShapPanel twinId={activeTwinId} updateTrigger={updateTrigger} />
            <WhatIfLab twinId={activeTwinId} />
          </div>
        </div>

        {/* Right Column (3) */}
        <div className="col-span-12 lg:col-span-3">
          <Metabolic3DTwin snapshot={snapshot} />
        </div>

      </main>
      
      <footer className="p-4 text-center text-xs text-gray-600 border-t border-gray-900 mt-auto">
        Research and competition prototype. Not intended for clinical diagnosis or treatment.
      </footer>
    </div>
  );
}

export default App;
