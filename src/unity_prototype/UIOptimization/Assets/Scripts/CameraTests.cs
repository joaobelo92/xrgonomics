using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using Newtonsoft.Json;

public class CameraTests : MonoBehaviour
{
    
    private PythonNetworking _pythonNetworking;
    public Camera cam;
    public GameObject cube;

    private bool _clientStopped;
    private bool _clientBusy;
    
    public GameObject interactionSpace;
    
    // Start is called before the first frame update
    void Start()
    {
        _pythonNetworking = new PythonNetworking(false);
        _clientBusy = false;
    }

    // Update is called once per frame
    void Update()
    {
        if (!_clientBusy)
        {
            _clientBusy = true;
            var polygon = GetNearFarPolygon(cam);
            StartCoroutine(GetOptimalPosInCameraFrustrum(polygon));
        }
    }

    private float[] GetNearFarPolygon(Camera cam)
    {
        var a = cam.nearClipPlane;
        var A = cam.fieldOfView * 0.5f;
        A *= Mathf.Deg2Rad;
        var h = Mathf.Tan(A) * a;
        var w = h / cam.pixelHeight * cam.pixelWidth;

        var cMat = cam.transform.localToWorldMatrix;
        
        var pos0 = cMat.MultiplyPoint3x4(new Vector3(w, h, cam.nearClipPlane));
        var pos1 = cMat.MultiplyPoint3x4(new Vector3(w, -h, cam.nearClipPlane));
        var pos2 = cMat.MultiplyPoint3x4(new Vector3(-w, -h, cam.nearClipPlane));
        var pos3 = cMat.MultiplyPoint3x4(new Vector3(-w, h, cam.nearClipPlane));
        
        a = cam.farClipPlane;
        h = Mathf.Tan(A) * a;
        w = h / cam.pixelHeight * cam.pixelWidth;
        
        var pos4 = cMat.MultiplyPoint3x4(new Vector3(w, h, cam.farClipPlane));
        var pos5 = cMat.MultiplyPoint3x4(new Vector3(w, -h, cam.farClipPlane));
        var pos6 = cMat.MultiplyPoint3x4(new Vector3(-w, -h, cam.farClipPlane));
        var pos7 = cMat.MultiplyPoint3x4(new Vector3(-w, h, cam.farClipPlane));

        var polygon = new float[8 * 3]
        {
            pos0.z, pos0.y, pos0.x,
            pos1.z, pos1.y, pos1.x,
            pos2.z, pos2.y, pos2.x,
            pos3.z, pos3.y, pos3.x,
            pos4.z, pos4.y, pos4.x,
            pos5.z, pos5.y, pos5.x,
            pos6.z, pos6.y, pos6.x,
            pos7.z, pos7.y, pos7.x
        };

        return polygon;
    } 
    
    // Rect NearPlaneDimensions(Camera cam)
    // {
    //     Rect r = new Rect();
    //     float a = cam.nearClipPlane;//get length
    //     float A = cam.fieldOfView * 0.5f;//get angle
    //     A = A * Mathf.Deg2Rad;//convert tor radians
    //     float h = (Mathf.Tan(A) * a);//calc height
    //     float w = (h / cam.pixelHeight) * cam.pixelWidth;//deduct width
    //
    //
    //     r.xMin = -w;
    //     r.xMax = w;
    //     r.yMin = -h;
    //     r.yMax = h;
    //     return r;
    // }
    //
    // Rect FarPlaneDimensions(Camera cam)
    // {
    //     Rect r = new Rect();
    //     float a = cam.farClipPlane;//get length
    //     float A = cam.fieldOfView * 0.5f;//get angle
    //     A = A * Mathf.Deg2Rad;//convert tor radians
    //     float h = (Mathf.Tan(A) * a);//calc height
    //     float w = (h / cam.pixelHeight) * cam.pixelWidth;//deduct width
    //
    //     cube.transform.position =
    //         cam.transform.localToWorldMatrix.MultiplyPoint3x4(new Vector3(w, h, cam.farClipPlane));
    //     r.xMin = -w;
    //     r.xMax = w;
    //     r.yMin = -h;
    //     r.yMax = h;
    //     return r;
    // }
    
    private IEnumerator GetOptimalPosInCameraFrustrum(float[] polygon)
    {
        
        var optimalPosRequest = new Serialization.OptimalPosRequest
        {
            // polygon = new [] {polygon[2], polygon[1], polygon[0]}
            polygon = polygon
        };
        var optimalPosRequestJson = JsonUtility.ToJson(optimalPosRequest);
        _pythonNetworking.PerformRequest("O", optimalPosRequestJson);
        yield return new WaitUntil(() => _pythonNetworking.requestResult != null);
        
        var voxels = JsonConvert.DeserializeObject<float[][]>(_pythonNetworking.requestResult);
        var _spacing = 10;
        
        foreach (Transform child in interactionSpace.transform)
        {
            Destroy(child.gameObject);
        }
        foreach (var voxel in voxels)
        {
            var position = new Vector3(voxel[2], voxel[1], voxel[0]);
            var scale = new Vector3(_spacing, _spacing, _spacing);
            // float discomfort;
            // switch (_metric)
            // {
            //     case DiscomfortMetric.MuscleActivation:
            //         discomfort = (voxel.muscleActivation ?? 1) * 25 + (voxel.reserve ?? 1) / 100;
            //         break;
            //     case DiscomfortMetric.ConsumedEndurance:
            //         // max value from DB
            //         // TODO: get this values dynamically
            //         discomfort = (voxel.muscleActivation ?? 10) / 10;
            //         break;
            //     case DiscomfortMetric.Rula:
            //         // max: 9, min: 4
            //         // TODO: get this values dynamically
            //         discomfort = (voxel.muscleActivation - 4 ?? 5) / 5;
            //         break;
            //     default:
            //         discomfort = 1;
            //         break;
            // }
            // var color = Color.Lerp(Color.green, Color.red, discomfort);
            Helpers.CreatePrimitiveGameObject(PrimitiveType.Cube, position, scale, interactionSpace.transform);
        }
        _clientBusy = false;
    }
}
