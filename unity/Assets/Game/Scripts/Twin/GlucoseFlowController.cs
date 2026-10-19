using UnityEngine;

namespace GlucoTwin.Twin
{
    public class GlucoseFlowController : MonoBehaviour
    {
        public ParticleSystem BloodstreamParticles;
        
        [Header("Mapping Bounds")]
        public float MinGlucose = 70f;
        public float MaxGlucose = 250f;
        
        [Header("Particle Settings")]
        public float MinEmissionRate = 10f;
        public float MaxEmissionRate = 50f;
        
        public float MinSpeed = 1f;
        public float MaxSpeed = 5f;

        private ParticleSystem.EmissionModule _emission;
        private ParticleSystem.MainModule _main;

        void Awake()
        {
            if (BloodstreamParticles != null)
            {
                _emission = BloodstreamParticles.emission;
                _main = BloodstreamParticles.main;
            }
        }

        public void UpdateFlow(float currentGlucose, string trend)
        {
            if (BloodstreamParticles == null) return;

            // Clamp glucose for visual sanity
            float clamped = Mathf.Clamp(currentGlucose, MinGlucose, MaxGlucose);
            float normalized = (clamped - MinGlucose) / (MaxGlucose - MinGlucose);

            // Calculate target values
            float targetEmission = Mathf.Lerp(MinEmissionRate, MaxEmissionRate, normalized);
            float targetSpeed = Mathf.Lerp(MinSpeed, MaxSpeed, normalized);

            // Optional trend adjustments
            if (trend == "Rising") targetSpeed *= 1.2f;
            else if (trend == "Falling") targetSpeed *= 0.8f;

            _emission.rateOverTime = targetEmission;
            _main.simulationSpeed = targetSpeed;
            
            // Adjust color slightly based on concentration
            Color baseColor = new Color(0.8f, 0.2f, 0.2f, 1f); // Red
            if (normalized > 0.7f)
            {
                // Add a slightly toxic/amber tint for high glucose visualization
                baseColor = Color.Lerp(baseColor, new Color(1f, 0.5f, 0f, 1f), (normalized - 0.7f) / 0.3f);
            }
            _main.startColor = baseColor;
        }
    }
}
