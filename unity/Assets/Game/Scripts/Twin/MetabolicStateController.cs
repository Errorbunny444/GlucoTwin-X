using System.Collections;
using UnityEngine;

namespace GlucoTwin.Twin
{
    public class MetabolicStateController : MonoBehaviour
    {
        [Header("Organ Renderers")]
        public Renderer PancreasRenderer;
        public Renderer StomachRenderer;
        public Renderer IntestineRenderer;

        [Header("Materials")]
        public Material OrganNeutralMat;
        public Material PancreasHighlightMat;
        public Material HighRiskEmphasisMat;

        private bool _isMealAnimating = false;
        private Color _originalPancreasColor;

        void Start()
        {
            if (PancreasHighlightMat != null)
            {
                _originalPancreasColor = PancreasHighlightMat.HasProperty("_EmissionColor") 
                    ? PancreasHighlightMat.GetColor("_EmissionColor") 
                    : PancreasHighlightMat.color;
            }
        }

        public void UpdateRiskState(bool highRisk, string trend)
        {
            if (PancreasRenderer == null) return;

            if (highRisk)
            {
                PancreasRenderer.material = HighRiskEmphasisMat != null ? HighRiskEmphasisMat : PancreasRenderer.material;
                // Add subtle pulsing
                StartCoroutine(PulseEmission(PancreasRenderer.material, Color.red * 2f, 1f));
            }
            else
            {
                PancreasRenderer.material = PancreasHighlightMat != null ? PancreasHighlightMat : PancreasRenderer.material;
                
                if (trend == "Rising")
                {
                    SetMaterialGlow(PancreasRenderer.material, new Color(1f, 0.5f, 0f) * 1.5f); // Amber
                }
                else
                {
                    SetMaterialGlow(PancreasRenderer.material, _originalPancreasColor);
                }
            }
        }

        private void SetMaterialGlow(Material mat, Color glowColor)
        {
            if (mat == null) return;
            if (mat.HasProperty("_EmissionColor"))
            {
                mat.EnableKeyword("_EMISSION");
                mat.SetColor("_EmissionColor", glowColor);
            }
            else
            {
                mat.color = glowColor;
            }
        }

        public void TriggerMealAnimation()
        {
            if (_isMealAnimating) return;
            StartCoroutine(MealAnimationRoutine());
        }

        private IEnumerator MealAnimationRoutine()
        {
            _isMealAnimating = true;

            if (StomachRenderer != null && OrganNeutralMat != null)
            {
                Material stomachMat = StomachRenderer.material;
                Color baseColor = stomachMat.color;
                Color highlightColor = new Color(0.5f, 0.8f, 0.5f, 1f); // Greenish digestion glow

                // Fade in
                float t = 0;
                while (t < 1f)
                {
                    t += Time.deltaTime * 2f;
                    stomachMat.color = Color.Lerp(baseColor, highlightColor, t);
                    if (stomachMat.HasProperty("_EmissionColor"))
                    {
                        stomachMat.EnableKeyword("_EMISSION");
                        stomachMat.SetColor("_EmissionColor", highlightColor * t);
                    }
                    yield return null;
                }

                // Hold
                yield return new WaitForSeconds(2f);

                // Fade out
                t = 1f;
                while (t > 0f)
                {
                    t -= Time.deltaTime;
                    stomachMat.color = Color.Lerp(baseColor, highlightColor, t);
                    if (stomachMat.HasProperty("_EmissionColor"))
                    {
                        stomachMat.SetColor("_EmissionColor", highlightColor * t);
                    }
                    yield return null;
                }
                if (stomachMat.HasProperty("_EmissionColor"))
                {
                    stomachMat.DisableKeyword("_EMISSION");
                }
                stomachMat.color = baseColor;
            }

            _isMealAnimating = false;
        }

        private IEnumerator PulseEmission(Material mat, Color targetEmission, float duration)
        {
            if (mat == null) yield break;
            Color baseCol = mat.color;
            while (true)
            {
                float pingPong = Mathf.PingPong(Time.time * 2f, 1f);
                if (mat.HasProperty("_EmissionColor"))
                {
                    mat.EnableKeyword("_EMISSION");
                    mat.SetColor("_EmissionColor", Color.Lerp(Color.black, targetEmission, pingPong));
                }
                else
                {
                    mat.color = Color.Lerp(baseCol, Color.red, pingPong);
                }
                yield return null;
            }
        }
    }
}
