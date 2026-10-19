using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using System;

namespace GlucoTwin.API
{
    public class TwinApiClient : MonoBehaviour
    {
        public string BaseUrl = "http://localhost:8000/api";

        public void GetTwinSnapshot(string twinId, Action<TwinSnapshotDto> onSuccess, Action<string> onError)
        {
            StartCoroutine(GetTwinSnapshotRoutine(twinId, onSuccess, onError));
        }

        private IEnumerator GetTwinSnapshotRoutine(string twinId, Action<TwinSnapshotDto> onSuccess, Action<string> onError)
        {
            string url = $"{BaseUrl}/twins/{twinId}";
            using (UnityWebRequest request = UnityWebRequest.Get(url))
            {
                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.ConnectionError || request.result == UnityWebRequest.Result.ProtocolError)
                {
                    onError?.Invoke(request.error);
                }
                else
                {
                    try
                    {
                        string json = request.downloadHandler.text;
                        // Replace 'static' with '@static' so JsonUtility matches the field, but wait:
                        // JsonUtility maps JSON key "static" to C# field "@static" natively? 
                        // Actually, JsonUtility in Unity matches the JSON string "static" to the C# field named "static" (the @ is just a compiler escape).
                        TwinSnapshotDto snapshot = JsonUtility.FromJson<TwinSnapshotDto>(json);
                        onSuccess?.Invoke(snapshot);
                    }
                    catch (Exception ex)
                    {
                        onError?.Invoke($"Parse error: {ex.Message}");
                    }
                }
            }
        }
    }
}
