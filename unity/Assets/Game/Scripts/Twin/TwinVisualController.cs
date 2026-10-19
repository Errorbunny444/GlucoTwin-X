using UnityEngine;
using UnityEngine.UI;
using GlucoTwin.API;

namespace GlucoTwin.Twin
{
    public class TwinVisualController : MonoBehaviour
    {
        public string TwinId = "DT-01";
        public bool UseMockData = false;

        [Header("Networking")]
        public TwinApiClient ApiClient;
        public TwinWebSocketClient WebSocketClient;

        [Header("Sub-Controllers")]
        public GlucoseFlowController FlowController;
        public MetabolicStateController StateController;

        [Header("UI")]
        public Text ConnectionStatusText;
        public Text TwinIdText;
        public Text CurrentGlucoseText;
        public Text PredictionText;
        public Text RiskStateText;
        public Text RiskProbText;
        
        [Header("Body Opacity")]
        [Range(0f, 1f)]
        public float BodyOpacity = 0.3f;
        public Material BodyTransparentMaterial;

        private TwinSnapshotDto _lastSnapshot;

        void Start()
        {
            if (UseMockData)
            {
                RunMockMode();
                return;
            }

            if (TwinIdText != null) TwinIdText.text = TwinId;
            UpdateConnectionUI(false, "DISCONNECTED");

            // Register WS events
            if (WebSocketClient != null)
            {
                WebSocketClient.OnConnectionStatusChanged += OnWsConnectionChanged;
                WebSocketClient.OnEventReceived += OnWsEvent;
                WebSocketClient.Connect(TwinId);
            }

            // Fallback REST fetch if WS doesn't immediately send a snapshot
            if (ApiClient != null)
            {
                ApiClient.GetTwinSnapshot(TwinId, 
                    onSuccess: snap => {
                        if (_lastSnapshot == null) ApplySnapshot(snap);
                    },
                    onError: err => {
                        Debug.LogWarning($"REST API Error: {err}");
                    }
                );
            }
        }

        void Update()
        {
            // Dynamically update body opacity
            if (BodyTransparentMaterial != null)
            {
                Color c = BodyTransparentMaterial.color;
                if (Mathf.Abs(c.a - BodyOpacity) > 0.01f)
                {
                    c.a = BodyOpacity;
                    BodyTransparentMaterial.color = c;
                }
            }
        }

        private void OnWsConnectionChanged(bool isConnected)
        {
            UpdateConnectionUI(isConnected, isConnected ? "CONNECTED" : "RECONNECTING");
        }

        private void OnWsEvent(TwinWebSocketEventDto evt)
        {
            if (evt.@event == "snapshot" && evt.data != null)
            {
                ApplySnapshot(evt.data);
            }
            else if (evt.@event == "meal_recorded")
            {
                StateController?.TriggerMealAnimation();
            }
        }

        private void ApplySnapshot(TwinSnapshotDto snap)
        {
            _lastSnapshot = snap;

            if (snap.dynamic != null)
            {
                if (CurrentGlucoseText != null)
                    CurrentGlucoseText.text = snap.dynamic.current_glucose > 0 ? snap.dynamic.current_glucose.ToString("F1") + " mg/dL" : "--";
                
                if (FlowController != null)
                {
                    FlowController.UpdateFlow(snap.dynamic.current_glucose, snap.dynamic.glucose_trend);
                }
            }

            if (snap.prediction_ready && snap.prediction != null)
            {
                if (PredictionText != null)
                {
                    PredictionText.text = $"{snap.prediction.predicted_glucose_120m.ToString("F1")} mg/dL\n<size=50%>{snap.prediction.lower_90:F0}-{snap.prediction.upper_90:F0}</size>";
                }
                
                if (RiskProbText != null)
                {
                    RiskProbText.text = (snap.prediction.high_glucose_probability * 100f).ToString("F0") + "%";
                }

                if (RiskStateText != null)
                {
                    RiskStateText.text = snap.prediction.high_glucose_risk ? "HIGH RISK" : "NORMAL";
                    RiskStateText.color = snap.prediction.high_glucose_risk ? Color.red : Color.green;
                }

                if (StateController != null)
                {
                    StateController.UpdateRiskState(snap.prediction.high_glucose_risk, snap.dynamic?.glucose_trend);
                }
            }
            else
            {
                if (PredictionText != null) PredictionText.text = "WARMING UP";
                if (RiskStateText != null)
                {
                    RiskStateText.text = "WARM UP";
                    RiskStateText.color = Color.gray;
                }
                if (RiskProbText != null) RiskProbText.text = "--";
            }
        }

        private void UpdateConnectionUI(bool connected, string text)
        {
            if (ConnectionStatusText != null)
            {
                ConnectionStatusText.text = text;
                ConnectionStatusText.color = connected ? Color.green : Color.yellow;
            }
        }

        private void RunMockMode()
        {
            UpdateConnectionUI(true, "MOCK MODE");
            if (TwinIdText != null) TwinIdText.text = "DT-MOCK";
            if (CurrentGlucoseText != null) CurrentGlucoseText.text = "155.0 mg/dL";
            if (PredictionText != null) PredictionText.text = "185.0 mg/dL";
            if (RiskStateText != null) {
                RiskStateText.text = "HIGH RISK";
                RiskStateText.color = Color.red;
            }
            
            if (FlowController != null) FlowController.UpdateFlow(155f, "Rising");
            if (StateController != null) StateController.UpdateRiskState(true, "Rising");
        }
    }
}
