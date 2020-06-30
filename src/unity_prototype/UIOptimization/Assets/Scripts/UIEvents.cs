using System;
using System.Collections;
using System.Globalization;
using System.Text.RegularExpressions;
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
    
    public Dropdown metricDropdown;
    public Slider voxelSizeSlider;
    
    public Button interactionModeButton;
    
    public Slider cameraZoomSlider;
    public Slider cameraPivotPitchSlider;
    public Slider cameraPivotYawSlider;
    public Text cameraPivotYawText;
    public Text cameraPivotPitchText;

    public Camera mainCamera;
    public GameObject cameraPivot;
    public GameObject avatar;
    
    public GameObject interactionSpace;
    public GameObject poses;
    public Shader voxelShader;
    // public Material voxelMaterial;
    private int _spacing;

    private PythonNetworking _pythonNetworking;
    private RaycastHit _hit;
    private bool _clientStopped;
    private bool _requestPending;
    private bool _clientBusy;

    private int _prevXValue = 0;
    private int _prevYValue = 0;
    private int _prevZValue = 0;

    public GameObject testCube;

    private enum DiscomfortMetric
    {
        MuscleActivation,
        ConsumedEndurance,
        RULA
    }
    
    private DiscomfortMetric _metric;

    public void Start()
    {
        xSlider.value = 0;
        ySlider.value = 0;
        zSlider.value = 0;
        xValueText.text = "0";
        yValueText.text = "0";
        zValueText.text = "0";
        _pythonNetworking = new PythonNetworking(false);
        _metric = DiscomfortMetric.MuscleActivation;
        _spacing = 5;
        StartCoroutine(GetLimits());
    }

    public void Update()
    {
        if (_requestPending && !_clientBusy)
        {
            _requestPending = false;
            _clientBusy = true;
            StartCoroutine(GetVoxels());
        }
        
        if (Input.GetMouseButtonDown(0))
        {
            var ray = mainCamera.ScreenPointToRay(Input.mousePosition);
            if  (Physics.Raycast(ray, out _hit, Mathf.Infinity))
            {
                StartCoroutine(GetVoxelPoses(_hit.transform.gameObject));
            }
        }
    }

    public void UpdateFilters(bool forceUpdate)
    {
        // TODO: improve this
        var x = xSlider.value;
        var y = ySlider.value;
        var z = zSlider.value;
        // TODO: get value dynamically
        var offset = 5;
        if (forceUpdate || 
            _prevXValue != (int) ((x + offset) / _spacing) || _prevXValue * x < 0 ||
            _prevYValue != (int) ((y + offset) / _spacing) || _prevYValue * y < 0 ||
            _prevZValue != (int) ((z + offset) / _spacing) || _prevZValue * z < 0)
        {
            _requestPending = true;
        }
        xValueText.text = xSlider.value.ToString("n2");
        yValueText.text = ySlider.value.ToString("n2");
        zValueText.text = zSlider.value.ToString("n2");
        xSlider.enabled = xToggle.isOn;
        ySlider.enabled = yToggle.isOn;
        zSlider.enabled = zToggle.isOn;
        _prevXValue = (int) ((x + offset) / _spacing);
        _prevYValue = (int) ((y + offset) / _spacing);
        _prevZValue = (int) ((z + offset) / _spacing);
    }

    public void UpdateMetric()
    {
        _metric = (DiscomfortMetric) metricDropdown.value;
        _spacing = (int) voxelSizeSlider.value;
        UpdateFilters(true);
    }
    
    public void UpdateCameraSettings()
    {
        var cameraPivotYaw = cameraPivotYawSlider.value;
        var cameraPivotPitch = cameraPivotPitchSlider.value;
        cameraPivotYawText.text = cameraPivotYaw.ToString();
        cameraPivotPitchText.text = cameraPivotPitch.ToString();
        cameraPivot.transform.eulerAngles = new Vector3(cameraPivotPitch, cameraPivotYaw, 0);
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
        _pythonNetworking.PerformRequest("L", null);
        yield return new WaitUntil(() => _pythonNetworking.requestResult != null);
        var limits = JsonConvert.DeserializeObject<Serialization.Limits>(_pythonNetworking.requestResult);
        xSlider.minValue = limits.minX;
        xSlider.maxValue = limits.maxX;
        ySlider.minValue = limits.minY;
        ySlider.maxValue = limits.maxY;
        zSlider.minValue = limits.minZ;
        zSlider.maxValue = limits.maxZ;
        UpdateFilters(true);
        _clientBusy = false;
    }

    private IEnumerator GetVoxels()
    {
        foreach (Transform child in interactionSpace.transform)
        {
            Destroy(child.gameObject);
        }
        
        var metricString = Regex.Replace(
            _metric.ToString(),
            "((?<!^)[A-Z0-9])",
            m => "_" + m.ToString().ToLower(), 
            RegexOptions.None);
        metricString = metricString.ToLower(); 
        
        var poseRequest = new Serialization.VoxelRequest()
        {
            x = xToggle.isOn ? xSlider.value.ToString() : null,
            y = yToggle.isOn ? ySlider.value.ToString() : null,
            z = zToggle.isOn ? zSlider.value.ToString() : null,
            metric = metricString
        };
        var poseRequestJson = JsonUtility.ToJson(poseRequest);
        _pythonNetworking.PerformRequest("C", poseRequestJson);
        yield return new WaitUntil(() => _pythonNetworking.requestResult != null);
        var voxels = JsonConvert.DeserializeObject<Serialization.Voxel[]>(_pythonNetworking.requestResult);
        foreach (var voxel in voxels)
        {
            var position = new Vector3(voxel.position[2], voxel.position[1],
                voxel.position[0]);
            var scale = new Vector3(_spacing, _spacing, _spacing);
            float discomfort;
            switch (_metric)
            {
                case DiscomfortMetric.MuscleActivation:
                    discomfort = (voxel.muscleActivation ?? 1) * 25 + (voxel.reserve ?? 1) / 100;
                    break;
                case DiscomfortMetric.ConsumedEndurance:
                    // max value from DB
                    // TODO: get this values dynamically
                    discomfort = (voxel.muscleActivation ?? 10) / 10;
                    break;
                default:
                    discomfort = 1;
                    break;
            }
            var color = Color.Lerp(Color.green, Color.red, discomfort);
            Helpers.CreatePrimitiveGameObject(PrimitiveType.Cube, position, scale,
                interactionSpace.transform, null, false, voxelShader, color);
        }
        _clientBusy = false;
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
        _pythonNetworking.PerformRequest("P", poseRequestJson);
        yield return new WaitUntil(() => _pythonNetworking.requestResult != null);
        var posesObj = JsonConvert.DeserializeObject<Serialization.Pose[]>(_pythonNetworking.requestResult);
        
        foreach (var pose in posesObj)
        {
            var position = new Vector3(pose.elbow[2], pose.elbow[1],
                pose.elbow[0]);
            var scale = new Vector3(5f, 5f, 5f);
            Helpers.CreatePrimitiveGameObject(PrimitiveType.Sphere, position, scale, poses.transform);
        }
    }
    
    private void OnDestroy()
    {
        _pythonNetworking.StopClient();
    }

}
