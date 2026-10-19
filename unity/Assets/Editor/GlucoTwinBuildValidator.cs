using UnityEngine;
using UnityEditor;
using System.IO;

namespace GlucoTwin.Editor
{
    public class GlucoTwinBuildValidator
    {
        [MenuItem("GlucoTwin-X/Validate 3D Twin")]
        public static void ValidateScene()
        {
            int errors = 0;
            Debug.Log("--- GlucoTwin-X Validation Started ---");

            if (!File.Exists("Assets/Game/Scenes/GlucoTwinVisualization.unity"))
            {
                Debug.LogError("Validation Failed: Scene GlucoTwinVisualization not found.");
                errors++;
            }

            if (!File.Exists("Assets/Game/Prefabs/DigitalTwinPatient.prefab"))
            {
                Debug.LogError("Validation Failed: DigitalTwinPatient prefab not found.");
                errors++;
            }

            var patient = GameObject.Find("DigitalTwinPatient");
            if (patient == null)
            {
                Debug.LogError("Validation Failed: DigitalTwinPatient GameObject missing from active scene.");
                errors++;
            }
            else
            {
                if (patient.GetComponentInChildren<GlucoTwin.Twin.TwinVisualController>() == null)
                {
                    Debug.LogError("Validation Failed: TwinVisualController script missing on prefab.");
                    errors++;
                }
                if (patient.GetComponentInChildren<GlucoTwin.API.TwinApiClient>() == null)
                {
                    Debug.LogError("Validation Failed: TwinApiClient script missing on prefab.");
                    errors++;
                }
            }

            if (errors == 0)
            {
                Debug.Log("<color=green>Validation Passed: The 3D Digital Twin scene is complete and ready for playback.</color>");
            }
            else
            {
                Debug.LogError($"Validation Failed with {errors} errors. Run 'Build Final 3D Twin Scene' to fix.");
            }
            Debug.Log("--- Validation Finished ---");
        }
    }
}
