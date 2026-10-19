import { useEffect, useRef, useState } from 'react';
import type { TwinSnapshot } from '../types';

export function useTwinWebSocket(twinId: string | null) {
  const [snapshot, setSnapshot] = useState<TwinSnapshot | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!twinId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // When using Vite proxy, the WS connects to the same host but with ws protocol
    const wsUrl = `${protocol}//${window.location.host}/ws/twins/${twinId}`;
    
    let reconnectTimeout: ReturnType<typeof setTimeout>;

    const connect = () => {
      console.log(`Connecting to WS: ${wsUrl}`);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WS Connected');
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.event === 'snapshot' && message.data) {
            setSnapshot(message.data);
          }
        } catch (e) {
          console.error('Failed to parse WS message', e);
        }
      };

      ws.onclose = () => {
        console.log('WS Disconnected');
        setConnected(false);
        // Attempt to reconnect after 3 seconds
        reconnectTimeout = setTimeout(connect, 3000);
      };

      ws.onerror = (err) => {
        console.error('WS Error', err);
        ws.close();
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [twinId]);

  return { snapshot, connected };
}
