using System;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Net.WebSockets;
using UnityEngine;
using System.Collections.Concurrent;

namespace GlucoTwin.API
{
    public class TwinWebSocketClient : MonoBehaviour
    {
        public string WebSocketUrl = "ws://localhost:8000/ws/twins/";
        public string TwinId = "DT-01";

        public Action<TwinWebSocketEventDto> OnEventReceived;
        public Action<bool> OnConnectionStatusChanged;

        private ClientWebSocket _ws;
        private CancellationTokenSource _cts;
        private ConcurrentQueue<TwinWebSocketEventDto> _mainThreadQueue = new ConcurrentQueue<TwinWebSocketEventDto>();

        private bool _isConnected = false;

        public void Connect(string twinId)
        {
            TwinId = twinId;
            _cts = new CancellationTokenSource();
            _ = ConnectAsync();
        }

        public void Disconnect()
        {
            if (_cts != null)
            {
                _cts.Cancel();
                _cts.Dispose();
                _cts = null;
            }
        }

        private async Task ConnectAsync()
        {
            while (!_cts.IsCancellationRequested)
            {
                _ws = new ClientWebSocket();
                string url = $"{WebSocketUrl}{TwinId}";
                try
                {
                    Debug.Log($"Connecting to {url}");
                    await _ws.ConnectAsync(new Uri(url), _cts.Token);
                    
                    _isConnected = true;
                    OnConnectionStatusChanged?.Invoke(true);
                    Debug.Log("WebSocket connected.");

                    await ReceiveLoop();
                }
                catch (Exception ex)
                {
                    Debug.LogWarning($"WebSocket error/disconnect: {ex.Message}");
                }
                finally
                {
                    _isConnected = false;
                    OnConnectionStatusChanged?.Invoke(false);
                    if (_ws != null) _ws.Dispose();
                }

                if (!_cts.IsCancellationRequested)
                {
                    Debug.Log("Reconnecting in 3 seconds...");
                    await Task.Delay(3000, _cts.Token);
                }
            }
        }

        private async Task ReceiveLoop()
        {
            var buffer = new byte[8192];
            while (_ws.State == WebSocketState.Open && !_cts.IsCancellationRequested)
            {
                var result = await _ws.ReceiveAsync(new ArraySegment<byte>(buffer), _cts.Token);
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, _cts.Token);
                    break;
                }
                
                string json = Encoding.UTF8.GetString(buffer, 0, result.Count);
                try
                {
                    var evt = JsonUtility.FromJson<TwinWebSocketEventDto>(json);
                    if (evt != null && !string.IsNullOrEmpty(evt.@event))
                    {
                        _mainThreadQueue.Enqueue(evt);
                    }
                }
                catch (Exception ex)
                {
                    Debug.LogError($"Error parsing WS JSON: {ex.Message}\nPayload: {json}");
                }
            }
        }

        private void Update()
        {
            while (_mainThreadQueue.TryDequeue(out var evt))
            {
                OnEventReceived?.Invoke(evt);
            }
        }

        private void OnDestroy()
        {
            Disconnect();
        }
    }
}
