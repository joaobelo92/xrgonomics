using System;
using System.Collections;
using System.Globalization;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.UI;

// ReSharper disable SpecifyACultureInStringConversionExplicitly

// ReSharper disable once InconsistentNaming
public class UIEvents : MonoBehaviour
{
    public Slider xSlider;
    public Slider ySlider;
    public Slider zSlider;
    public Toggle xToggle;
    public Toggle yToggle;
    public Toggle zToggle;
    public Text xValueText;
    public Text yValueText;
    public Text zValueText;
    
    public Button interactionModeButton;
    
    public Slider cameraZoomSlider;
    public Slider cameraPivotYawSlider;
    public Text cameraPivotYawText;

    public Camera mainCamera;
    public GameObject cameraPivot;
    public GameObject avatar;
    
    public GameObject interactionSpace;
    public GameObject poses;
    public Material voxelMaterial;

    private PythonNetworking pythonNetworking;
    private RaycastHit hit;
    private bool clientStopped;
    private bool requestPending;
    private bool clientBusy;

    public void Start()
    {
        xSlider.value = 0;
        ySlider.value = 0;
        zSlider.value = 0;
        pythonNetworking = new PythonNetworking(false);
        StartCoroutine(GetLimits());
    }

    public void Update()
    {
        if (requestPending && !clientBusy)
        {
            requestPending = false;
            clientBusy = true;
            StartCoroutine(GetVoxels());
        }
        
        if (Input.GetMouseButtonDown(0))
        {
            Ray ray = mainCamera.ScreenPointToRay(Input.mousePosition);
            if  (Physics.Raycast(ray, out hit, Mathf.Infinity))
            {
                StartCoroutine(GetVoxelPoses(hit.transform.gameObject));
            }
        }
    }

    public void UpdateFilters()
    {
        xValueText.text = xSlider.value.ToString("n2");
        yValueText.text = ySlider.value.ToString("n2");
        zValueText.text = zSlider.value.ToString("n2");
        xSlider.enabled = xToggle.isOn;
        ySlider.enabled = yToggle.isOn;
        zSlider.enabled = zToggle.isOn;
        requestPending = true;
    }
    
    public void UpdateCameraSettings()
    {
        var cameraPivotYaw = cameraPivotYawSlider.value;
        cameraPivotYawText.text = cameraPivotYaw.ToString();
        cameraPivot.transform.eulerAngles = new Vector3(0, cameraPivotYaw, 0);
        mainCamera.transform.localPosition = new Vector3(0, 0, cameraZoomSlider.value);
    }

    public void ShowAvatar()
    {
        avatar.SetActive(!avatar.activeSelf);
    }

    public void ToggleInteractionMode()
    {
        interactionSpace.SetActive(!interactionSpace.activeSelf);
        poses.SetActive(!interactionSpace.activeSelf);
        interactionModeButton.gameObject.SetActive(!interactionSpace.activeSelf);
    }

    private IEnumerator GetLimits()
    {
        pythonNetworking.PerformRequest("L", null);
        yield return new WaitUntil(() => pythonNetworking.requestResult != null);
        var limits = JsonConvert.DeserializeObject<Serialization.Limits>(pythonNetworking.requestResult);
        xSlider.minValue = limits.minX;
        xSlider.maxValue = limits.maxX;
        ySlider.minValue = limits.minY;
        ySlider.maxValue = limits.maxY;
        zSlider.minValue = limits.minZ;
        zSlider.maxValue = limits.maxZ;
        UpdateFilters();
    }

    private IEnumerator GetVoxels()
    {
        foreach (Transform child in interactionSpace.transform)
        {
            Destroy(child.gameObject);
        }
        
        var poseRequest = new Serialization.AnchorRequest
        {
            x = xToggle.isOn ? xSlider.value.ToString() : null,
            y = yToggle.isOn ? ySlider.value.ToString() : null,
            z = zToggle.isOn ? zSlider.value.ToString() : null
        };
        var poseRequestJson = JsonUtility.ToJson(poseRequest);
        pythonNetworking.PerformRequest("C", poseRequestJson);
        yield return new WaitUntil(() => pythonNetworking.requestResult != null);
        var anchors = JsonConvert.DeserializeObject<Serialization.Anchor[]>(pythonNetworking.requestResult);
        foreach (var anchor in anchors)
        {
            var position = new Vector3(anchor.position[2], anchor.position[1],
                anchor.position[0]);
            var scale = new Vector3(5f, 5f, 5f);
            Helpers.CreatePrimitiveGameObject(PrimitiveType.Cube, position, scale,
                interactionSpace.transform, null, false, voxelMaterial);
        }
        clientBusy = false;
    }
    
    private IEnumerator GetVoxelPoses(GameObject voxel)
    {
        foreach (Transform child in poses.transform)
        {
            Destroy(child.gameObject);
        }
        
        ToggleInteractionMode();
        // Clone voxel into poses GameObject
        Instantiate(voxel, poses.transform);

        var pos = voxel.transform.position;
        print(pos.magnitude);
        var poseRequest = new Serialization.PoseRequest
        {
            x = pos.z,
            y = pos.y,
            z = pos.x
        };
        var poseRequestJson = JsonConvert.SerializeObject(poseRequest);
        pythonNetworking.PerformRequest("P", poseRequestJson);
        yield return new WaitUntil(() => pythonNetworking.requestResult != null);
        var posesObj = JsonConvert.DeserializeObject<Serialization.Pose[]>(pythonNetworking.requestResult);
        
        foreach (var pose in posesObj)
        {
            var position = new Vector3(pose.elbow[2], pose.elbow[1],
                pose.elbow[0]);
            
            print(position.magnitude + " " + (pos - position).magnitude);
            var scale = new Vector3(5f, 5f, 5f);
            Helpers.CreatePrimitiveGameObject(PrimitiveType.Sphere, position, scale, poses.transform);
        }
    }
    
    private void OnDestroy()
    {
        pythonNetworking.StopClient();
    }

}
