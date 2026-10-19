using UnityEngine;
using UnityEngine.UI;
using UnityEditor;
using System.IO;
using GlucoTwin.API;
using GlucoTwin.Twin;

namespace GlucoTwin.Editor
{
    public class GlucoTwinSceneBuilder : UnityEditor.EditorWindow
    {
        [MenuItem("GlucoTwin-X/Build Final 3D Twin Scene")]
        public static void BuildScene()
        {
            Debug.Log("Starting GlucoTwin-X Scene Build...");
            
            // 1. Create or Open target scene
            string scenePath = "Assets/Game/Scenes/GlucoTwinVisualization.unity";
            if (!Directory.Exists("Assets/Game/Scenes"))
            {
                Directory.CreateDirectory("Assets/Game/Scenes");
            }

            var scene = UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene, UnityEditor.SceneManagement.NewSceneMode.Single);
            
            // 2. Setup Lighting and Camera
            GameObject lightingRoot = new GameObject("Lighting");
            GameObject keyLight = new GameObject("KeyLight");
            keyLight.transform.SetParent(lightingRoot.transform);
            var l = keyLight.AddComponent<Light>();
            l.type = LightType.Directional;
            l.intensity = 1.2f;
            keyLight.transform.rotation = Quaternion.Euler(50, -30, 0);

            GameObject cameraRig = new GameObject("CameraRig");
            GameObject mainCam = new GameObject("MainCamera");
            mainCam.transform.SetParent(cameraRig.transform);
            var cam = mainCam.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.1f, 0.1f, 0.15f); // Dark medical tech bg
            mainCam.transform.position = new GameObject().transform.position + new Vector3(0, 1, -5);

            // 3. Create Materials
            EnsureMaterials();

            // 4. Create Twin Hierarchy
            GameObject patientRoot = new GameObject("DigitalTwinPatient");
            
            GameObject body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            body.name = "Body";
            body.transform.SetParent(patientRoot.transform);
            body.transform.localScale = new Vector3(2, 4, 1.5f);
            body.GetComponent<Renderer>().sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>("Assets/Game/Materials/BodyTransparent.mat");

            GameObject metabolicSystem = new GameObject("MetabolicSystem");
            metabolicSystem.transform.SetParent(patientRoot.transform);

            // Load High-Fidelity 3D Models (Pancreas, Stomach, Intestine)
            GameObject pancreas = CreateOrgan("Pancreas", PrimitiveType.Cube, new Vector3(0.06f, 0.06f, 0.06f), new Vector3(0.25f, 0.05f, 0), metabolicSystem.transform, "OrganNeutral.mat");
            GameObject stomach = CreateOrgan("Stomach", PrimitiveType.Sphere, new Vector3(0.02f, 0.02f, 0.02f), new Vector3(-0.35f, 0.35f, 0), metabolicSystem.transform, "OrganNeutral.mat");
            GameObject intestine = CreateOrgan("Intestine", PrimitiveType.Sphere, new Vector3(1.0f, 1.0f, 1.0f), new Vector3(0, -0.4f, 0), metabolicSystem.transform, "OrganNeutral.mat");
            
            // 5. Bloodstream particles
            GameObject bloodstream = new GameObject("Bloodstream");
            bloodstream.transform.SetParent(metabolicSystem.transform);
            var ps = bloodstream.AddComponent<ParticleSystem>();
            var main = ps.main;
            main.startColor = Color.red;
            main.startSize = 0.1f;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            var emission = ps.emission;
            emission.rateOverTime = 20;

            // 6. Controllers
            GameObject controllers = new GameObject("Controllers");
            controllers.transform.SetParent(patientRoot.transform);
            
            var apiClient = controllers.AddComponent<TwinApiClient>();
            var wsClient = controllers.AddComponent<TwinWebSocketClient>();
            var visualCtrl = controllers.AddComponent<TwinVisualController>();
            var metabolicCtrl = controllers.AddComponent<MetabolicStateController>();
            var flowCtrl = controllers.AddComponent<GlucoseFlowController>();

            // Assign links
            visualCtrl.ApiClient = apiClient;
            visualCtrl.WebSocketClient = wsClient;
            visualCtrl.FlowController = flowCtrl;
            visualCtrl.StateController = metabolicCtrl;
            visualCtrl.BodyTransparentMaterial = body.GetComponent<Renderer>().sharedMaterial;

            metabolicCtrl.PancreasRenderer = pancreas.GetComponentInChildren<Renderer>();
            metabolicCtrl.StomachRenderer = stomach.GetComponentInChildren<Renderer>();
            metabolicCtrl.IntestineRenderer = intestine.GetComponentInChildren<Renderer>();
            metabolicCtrl.OrganNeutralMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Game/Materials/OrganNeutral.mat");
            metabolicCtrl.PancreasHighlightMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Game/Materials/PancreasHighlight.mat");
            metabolicCtrl.HighRiskEmphasisMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/Game/Materials/HighRiskEmphasis.mat");

            flowCtrl.BloodstreamParticles = ps;

            // 7. UI Canvas (Minimal for demo)
            GameObject canvasGO = new GameObject("TwinHUD");
            var canvas = canvasGO.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvasGO.AddComponent<UnityEngine.UI.CanvasScaler>();
            canvasGO.AddComponent<UnityEngine.UI.GraphicRaycaster>();
            
            visualCtrl.TwinIdText = CreateText(canvasGO.transform, "TwinIdText", "DT-01", new Vector2(50, -50));
            visualCtrl.CurrentGlucoseText = CreateText(canvasGO.transform, "CurrentGlucoseText", "--- mg/dL", new Vector2(50, -100));
            visualCtrl.PredictionText = CreateText(canvasGO.transform, "PredictionText", "WARMING UP", new Vector2(50, -150));
            visualCtrl.RiskStateText = CreateText(canvasGO.transform, "RiskStateText", "NORMAL", new Vector2(50, -200));
            visualCtrl.ConnectionStatusText = CreateText(canvasGO.transform, "ConnectionStatusText", "DISCONNECTED", new Vector2(50, -250));

            // 8. Create Prefab
            if (!Directory.Exists("Assets/Game/Prefabs")) Directory.CreateDirectory("Assets/Game/Prefabs");
            PrefabUtility.SaveAsPrefabAsset(patientRoot, "Assets/Game/Prefabs/DigitalTwinPatient.prefab");

            // 9. Save Scene
            UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene, scenePath);
            Debug.Log($"Successfully built scene at {scenePath}");

            // 10. Run validation
            GlucoTwinBuildValidator.ValidateScene();
        }

        private static GameObject CreateOrgan(string name, PrimitiveType prim, Vector3 scale, Vector3 pos, Transform parent, string matName)
        {
            // Tries to load FBX or OBJ export from Fusion 360, falls back to primitive
            string fbxPath = $"Assets/Game/Models/Fusion360/{name.ToLower()}.fbx";
            string objPath = $"Assets/Game/Models/Fusion360/{name.ToLower()}.obj";
            GameObject obj = null;
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(fbxPath) ?? AssetDatabase.LoadAssetAtPath<GameObject>(objPath);
            if (prefab != null)
            {
                obj = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                obj.name = name;
                obj.transform.localScale = scale;
            }
            else
            {
                obj = GameObject.CreatePrimitive(prim);
                obj.name = name;
                obj.transform.localScale = scale;
            }
            obj.transform.SetParent(parent);
            obj.transform.localPosition = pos;

            var mat = AssetDatabase.LoadAssetAtPath<Material>($"Assets/Game/Materials/{matName}");
            if (mat != null)
            {
                var renderers = obj.GetComponentsInChildren<Renderer>();
                foreach (var r in renderers)
                {
                    r.sharedMaterial = mat;
                }
            }
            return obj;
        }

        private static void EnsureMaterials()
        {
            if (!Directory.Exists("Assets/Game/Materials")) Directory.CreateDirectory("Assets/Game/Materials");
            
            CreateMat("BodyTransparent.mat", new Color(0.8f, 0.9f, 1f, 0.25f), true);
            CreateMat("OrganNeutral.mat", new Color(0.7f, 0.4f, 0.4f), false);
            CreateMat("PancreasHighlight.mat", new Color(0.8f, 0.5f, 0.2f), true);
            CreateMat("HighRiskEmphasis.mat", new Color(1f, 0f, 0f), true);
        }

        private static void CreateMat(string filename, Color color, bool transparent)
        {
            string path = $"Assets/Game/Materials/{filename}";
            if (AssetDatabase.LoadAssetAtPath<Material>(path) == null)
            {
                Material mat = new Material(Shader.Find(transparent ? "Transparent/Diffuse" : "Standard"));
                mat.color = color;
                if (transparent && mat.HasProperty("_Mode"))
                {
                    mat.SetFloat("_Mode", 3); // Transparent
                }
                AssetDatabase.CreateAsset(mat, path);
            }
        }

        private static Text CreateText(Transform parent, string name, string text, Vector2 pos)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent);
            var rect = go.AddComponent<RectTransform>();
            rect.anchorMin = new Vector2(0, 1);
            rect.anchorMax = new Vector2(0, 1);
            rect.pivot = new Vector2(0, 1);
            rect.anchoredPosition = pos;
            rect.sizeDelta = new Vector2(300, 50);

            var t = go.AddComponent<Text>();
            t.text = text;
            t.fontSize = 20;
            t.color = Color.white;
            t.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf") ?? Resources.GetBuiltinResource<Font>("Arial.ttf");
            return t;
        }
    }
}
