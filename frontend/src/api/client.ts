import type { TwinSummary, TwinSnapshot, ExplanationResponse, WhatIfResponse } from '../types';

const API_BASE = '/api';

export const apiClient = {
  getTwins: async (): Promise<TwinSummary[]> => {
    const res = await fetch(`${API_BASE}/twins`);
    if (!res.ok) throw new Error('Failed to fetch twins');
    return res.json();
  },

  getTwinSnapshot: async (twinId: string): Promise<TwinSnapshot> => {
    const res = await fetch(`${API_BASE}/twins/${twinId}`);
    if (!res.ok) throw new Error('Failed to fetch snapshot');
    return res.json();
  },

  getGlucoseHistory: async (twinId: string, minutes: number = 180): Promise<any> => {
    const res = await fetch(`${API_BASE}/twins/${twinId}/glucose?minutes=${minutes}`);
    if (!res.ok) throw new Error('Failed to fetch glucose history');
    return res.json();
  },

  getPredictions: async (twinId: string): Promise<any[]> => {
    const res = await fetch(`${API_BASE}/twins/${twinId}/predictions`);
    if (!res.ok) throw new Error('Failed to fetch predictions');
    return res.json();
  },

  getExplanation: async (twinId: string): Promise<ExplanationResponse> => {
    const res = await fetch(`${API_BASE}/twins/${twinId}/explanation`);
    if (!res.ok) throw new Error('Failed to fetch explanation');
    return res.json();
  },

  runWhatIf: async (twinId: string, carbsG: number, activityLevel: string): Promise<WhatIfResponse> => {
    const res = await fetch(`${API_BASE}/twins/${twinId}/what-if`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ carbs_g: carbsG, activity_level: activityLevel })
    });
    if (!res.ok) throw new Error('Failed to run what-if simulation');
    return res.json();
  },

  startReplay: async (twinId: string, speed: number = 1.0): Promise<any> => {
    const res = await fetch(`${API_BASE}/twins/${twinId}/replay/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speed })
    });
    if (!res.ok) throw new Error('Failed to start replay');
    return res.json();
  },

  stopReplay: async (twinId: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/twins/${twinId}/replay/stop`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to stop replay');
    return res.json();
  },

  getReplayStatus: async (twinId: string): Promise<{ running: boolean }> => {
    const res = await fetch(`${API_BASE}/twins/${twinId}/replay/status`);
    if (!res.ok) throw new Error('Failed to get replay status');
    return res.json();
  }
};
