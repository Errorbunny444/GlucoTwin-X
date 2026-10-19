using System;
using UnityEngine;

namespace GlucoTwin.API
{
    [Serializable]
    public class StaticTwinStateDto
    {
        public string twin_id;
        public int age;
        public string gender;
        public float bmi;
        public float hba1c;
        public float fasting_glucose;
        public float fasting_insulin;
    }

    [Serializable]
    public class DynamicTwinStateDto
    {
        public string current_timestamp;
        public float current_glucose;
        public string glucose_trend;
        public float heart_rate;
        public float minutes_since_last_meal;
        public float recent_carbs_120m;
    }

    [Serializable]
    public class PredictionStateDto
    {
        public string prediction_timestamp;
        public float predicted_glucose_120m;
        public float lower_90;
        public float upper_90;
        public float high_glucose_probability;
        public bool high_glucose_risk;
        public float alert_threshold;
    }

    [Serializable]
    public class TwinSnapshotDto
    {
        public string twin_id;
        public string timestamp;
        public string status;
        public bool prediction_ready;
        public StaticTwinStateDto @static;
        public DynamicTwinStateDto dynamic;
        public PredictionStateDto prediction;
    }

    [Serializable]
    public class TwinWebSocketEventDto
    {
        public string @event;
        public string twin_id;
        public string timestamp;
        public TwinSnapshotDto data;
    }
}
