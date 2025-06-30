using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Runtime.InteropServices;

#if ENABLE_WINMD_SUPPORT
using Windows.UI.Xaml;
using Windows.Graphics.Imaging;
using Windows.Perception.Spatial;

// Include winrt components
using HoloLensForCV;
#endif

using UnityEngine;
using UnityEngine.UI;
using UnityEngine.XR.WSA;
using UnityEngine.XR.WSA.Input;
using System.Threading;
using Microsoft.MixedReality.Toolkit.Experimental.Utilities;
using UnityEngine.Timeline;


// App permissions, modify the appx file for research mode streams
// https://docs.microsoft.com/en-us/windows/uwp/packaging/app-capability-declarations

// Reimplement as list loop structure... 
namespace ArUcoDetectionHoloLensUnity
{
    // Using the hololens for cv .winmd file for runtime support
    // Build HoloLensForCV c++ project (x86) and copy all output files
    // to Assets->Plugins->x86
    // https://docs.unity3d.com/2018.4/Documentation/Manual/IL2CPP-WindowsRuntimeSupport.html
    public class ArUcoMarkerDetection : MonoBehaviour
    {
        private bool _isWorldAnchored = false;

        public Text myText;

        public CvUtils.DeviceTypeUnity deviceType;

        // Note: HL2 only has PV camera function currently.
        public CvUtils.SensorTypeUnity sensorTypePv;
        public CvUtils.ArUcoDictionaryName arUcoDictionaryName;

        // Params for aruco detection
        // Marker size in meters: 0.08 m
        public float markerSize;

        /// <summary>
        /// Holder for the camera parameters (intrinsics and extrinsics)
        /// of the tracking sensor on the HoloLens 2
        /// </summary>
        public CameraCalibrationParams calibParams;

        /// <summary>
        /// Game object for to use for marker instantiation and replacement
        /// </summary>
        // public GameObject markerGo;
        public GameObject markerGo1;
        public GameObject markerGo2;
        public GameObject objectGo;
        private Matrix4x4 worldTransformMarker1;
        private Matrix4x4 worldTransformMarker2;


        // Add fields to store last known positions and rotations of each marker
        private Vector3 _lastPositionMarker1;
        private Quaternion _lastRotationMarker1;
        private Vector3 _lastPositionMarker2;
        private Quaternion _lastRotationMarker2;

        private Dictionary<int, Dictionary<string, Vector3>> detectedPoses = new Dictionary<int, Dictionary<string, Vector3>>();

        // Add a field to keep track of whether the positions are valid (have been set at least once)
        private long _positionMarker1Valid = 0;
        private long _positionMarker2Valid = 0;

        private long curItr = 0;
        private long dataNewLimit = 10;


        /// <summary>
        /// List of prefab instances of detected aruco markers.
        /// </summary>
        //private List<GameObject> _markerGOs;

        private bool _mediaFrameSourceGroupsStarted = false;
        private int _frameCount = 0;
        public int skipFrames = 3;

        // Relative Position between two markers
        public Vector3 relativePosition;

        // Relative Rotation between two markers
        public Quaternion relativeRotation;

        private float scaling = 10f;

        

#if ENABLE_WINMD_SUPPORT
        // Enable winmd support to include winmd files. Will not
        // run in Unity editor.
        private SensorFrameStreamer _sensorFrameStreamerPv;
        private SpatialPerception _spatialPerception;
        private HoloLensForCV.DeviceType _deviceType;
        private MediaFrameSourceGroupType _mediaFrameSourceGroup;

        /// <summary>
        /// Media frame source groups for each sensor stream.
        /// </summary>
        private MediaFrameSourceGroup _pvMediaFrameSourceGroup;
        private SensorType _sensorType;

        /// <summary>
        /// ArUco marker tracker winRT class
        /// </summary>
        //private ArUcoMarkerTracker _arUcoMarkerTracker;

        /// <summary>
        /// Coordinate system reference for Unity to WinRt 
        /// transform construction
        /// </summary>
        private SpatialCoordinateSystem _unityCoordinateSystem;
#endif

        // Gesture handler
        GestureRecognizer _gestureRecognizer;

        #region UnityMethods

        // Use this for initialization
        async void Start()
        {
            // Initialize gesture handler
            InitializeHandler();

            // Start the media frame source groups.
            await StartHoloLensMediaFrameSourceGroups();

            // Wait for a few seconds prior to making calls to Update 
            // HoloLens media frame source groups.
            StartCoroutine(DelayCoroutine());

            // objectGo.transform.localScale = new Vector3(markerSize, markerSize, markerSize);
            // objectGo.transform.localScale /= scaling;


            // DEBUG PURPOSES
            //_positionMarker1Valid = 0;
            //_positionMarker2Valid = 0;

            //_lastPositionMarker1 = new Vector3(0.5f, 0.23f, 0.3f);
            //_lastRotationMarker1 = Quaternion.Euler(new Vector3(0, 0, 0));

            //markerGo1.transform.SetPositionAndRotation(_lastPositionMarker1, _lastRotationMarker1);

            //_lastPositionMarker2 = new Vector3(0.1f, 0, 0.51f);
            //_lastRotationMarker2 = Quaternion.Euler(new Vector3(30, 30, 30));

            //markerGo2.transform.SetPositionAndRotation(_lastPositionMarker2, _lastRotationMarker2);

            //CaptureRelativePose();

            //PlaceBackObject();
        }

        /// <summary>
        /// https://docs.unity3d.com/ScriptReference/WaitForSeconds.html
        /// Wait for some seconds for media frame source groups to complete
        /// their initialization.
        /// </summary>
        /// <returns></returns>
        IEnumerator DelayCoroutine()
        {
            Debug.Log("Started Coroutine at timestamp : " + Time.time);

            // YieldInstruction that waits for 2 seconds.
            yield return new WaitForSeconds(2);

            Debug.Log("Finished Coroutine at timestamp : " + Time.time);
        }

        // Update is called once per frame
        async void Update()
        {
            curItr += 1;
#if ENABLE_WINMD_SUPPORT
            _frameCount += 1;

            // Predict every 3rd frame
            if (_frameCount == skipFrames)
            {
                var detections = await Task.Run(() => _pvMediaFrameSourceGroup.DetectArUcoMarkers(_sensorType));
                myText.text = "tracking... " + detections.Count;
                // Update the game object pose with current detections
                UpdateArUcoDetections(detections);

                _frameCount = 0;
            }
#endif
        }

        public void CaptureRelativePose()
        {
            if (curItr - _positionMarker1Valid <= dataNewLimit && curItr - _positionMarker2Valid <= dataNewLimit)
            {
                // FJ: m1_T_m2 -> m2 on specimen, m1 on bed
                relativePosition = markerGo1.transform.InverseTransformPoint(markerGo2.transform.position);
                relativeRotation = Quaternion.Inverse(markerGo1.transform.rotation) * markerGo2.transform.rotation;

                Debug.Log("Relative pose captured:");
                Debug.Log("Relative Position: " + relativePosition);
                Debug.Log("Relative Rotation: " + relativeRotation);

                PlaceBackObject();
            }
            else
            {
                Debug.Log("Both markers must be visible to capture relative pose.");
            }
        }

        public void PlaceBackObject()
        {
            if (curItr - _positionMarker1Valid <= dataNewLimit)
            {
                objectGo.transform.SetParent(markerGo1.transform);
                objectGo.transform.localPosition = relativePosition;
                objectGo.transform.localRotation = relativeRotation;

                Debug.Log("Placed the specimen object relative to resection bed marker");
            }
            else
            {
                Debug.Log("No valid marker position available to place the object.");
            }
        }

        //public void CaptureRelativePoseDEP()
        //{
        //    if (_positionMarker1Valid && _positionMarker2Valid)
        //    {
        //        // Calculate relative position in the world coordinate system
        //        // FJ: this is from marker 2 to marker 1: m1_t_m2
        //        relativePosition = _lastPositionMarker2 - _lastPositionMarker1;

        //        // Calculate relative rotation
        //        // FJ: this is from marker 2 to marker 1: m1_R_m2
        //        relativeRotation = Quaternion.Inverse(_lastRotationMarker1) * _lastRotationMarker2;

        //        Debug.Log("Relative pose captured:");
        //        Debug.Log("Relative Position: " + relativePosition);
        //        Debug.Log("Relative Rotation: " + relativeRotation);

        //    }
        //    else
        //    {
        //        Debug.LogError("Both markers must be visible to capture relative pose.");
        //    }
        //}


        //public void PlaceBackObjectDEP()
        //{
        //    if (_positionMarker1Valid || _positionMarker2Valid)
        //    {
        //        Vector3 basePosition;
        //        Quaternion baseRotation;

        //        if (_positionMarker1Valid)
        //        {
        //            basePosition = _lastPositionMarker1;
        //            baseRotation = _lastRotationMarker1;
        //            objectGo.transform.SetParent(markerGo1.transform);
        //        }
        //        else
        //        { // TODO: remove this
        //            basePosition = _lastPositionMarker2;
        //            baseRotation = _lastRotationMarker2;
        //            objectGo.transform.SetParent(markerGo2.transform);
        //        }

        //        // Calculate the new position using the captured relative pose
        //        Vector3 newPosition = basePosition + baseRotation * relativePosition;

        //        // Calculate the new rotation
        //        Quaternion newRotation = baseRotation * relativeRotation;

        //        // Apply the corrective rotation for orientation if needed
        //        Quaternion correctiveRotation = Quaternion.Euler(0, 180, 180);
        //        newRotation = newRotation * correctiveRotation;

        //        // Set the object's position and rotation
        //        // objectGo.transform.SetPositionAndRotation(newPosition, newRotation);
        //        objectGo.transform.localPosition = relativePosition;
        //        objectGo.transform.localRotation = relativeRotation;

        //        Debug.Log("Object placed back at the marker's position with correct alignment.");
        //    }
        //    else
        //    {
        //        Debug.LogError("No valid marker position available to place the object.");
        //    }
        //}


        async void OnApplicationQuit()
        {
            await StopHoloLensMediaFrameSourceGroup();
        }

        #endregion

        async Task StartHoloLensMediaFrameSourceGroups()
        {
#if ENABLE_WINMD_SUPPORT
            // Plugin doesn't work in the Unity editor
            myText.text = "Initializing MediaFrameSourceGroups...";

            // PV
            Debug.Log("HoloLensForCVUnity.ArUcoDetection.StartHoloLensMediaFrameSourceGroup: Setting up sensor frame streamer");
            _sensorType = (SensorType)sensorTypePv;
            _sensorFrameStreamerPv = new SensorFrameStreamer();
            _sensorFrameStreamerPv.Enable(_sensorType);

            // Spatial perception
            Debug.Log("HoloLensForCVUnity.ArUcoDetection.StartHoloLensMediaFrameSourceGroup: Setting up spatial perception");
            _spatialPerception = new SpatialPerception();

            // Enable media frame source groups
            // PV
            Debug.Log("HoloLensForCVUnity.ArUcoDetection.StartHoloLensMediaFrameSourceGroup: Setting up the media frame source group");

            // Check if using research mode sensors
            if (sensorTypePv == CvUtils.SensorTypeUnity.PhotoVideo)
                _mediaFrameSourceGroup = MediaFrameSourceGroupType.PhotoVideoCamera;
            else
                _mediaFrameSourceGroup = MediaFrameSourceGroupType.HoloLensResearchModeSensors;

            // Cast device type 
            _deviceType = (HoloLensForCV.DeviceType)deviceType;
            _pvMediaFrameSourceGroup = new MediaFrameSourceGroup(
                _mediaFrameSourceGroup,
                _spatialPerception,
                _deviceType,
                _sensorFrameStreamerPv,

                // Calibration parameters from opencv, compute once for each hololens 2 device
                calibParams.focalLength.x, calibParams.focalLength.y,
                calibParams.principalPoint.x, calibParams.principalPoint.y,
                calibParams.radialDistortion.x, calibParams.radialDistortion.y, calibParams.radialDistortion.z,
                calibParams.tangentialDistortion.x, calibParams.tangentialDistortion.y,
                calibParams.imageHeight, calibParams.imageWidth);
            _pvMediaFrameSourceGroup.Enable(_sensorType);

            // Start media frame source groups
            myText.text = "Starting MediaFrameSourceGroups...";

            // Photo video
            Debug.Log("HoloLensForCVUnity.ArUcoDetection.StartHoloLensMediaFrameSourceGroup: Starting the media frame source group");
            await _pvMediaFrameSourceGroup.StartAsync();
            _mediaFrameSourceGroupsStarted = true;

            myText.text = "MediaFrameSourceGroups started...";

            // Initialize the Unity coordinate system
            // Get pointer to Unity's spatial coordinate system
            // https://github.com/qian256/HoloLensARToolKit/blob/master/ARToolKitUWP-Unity/Scripts/ARUWPVideo.cs
            try
            {
                _unityCoordinateSystem = Marshal.GetObjectForIUnknown(WorldManager.GetNativeISpatialCoordinateSystemPtr()) as SpatialCoordinateSystem;
            }
            catch (Exception)
            {
                Debug.Log("ArUcoDetectionHoloLensUnity.ArUcoMarkerDetection: Could not get pointer to Unity spatial coordinate system.");
                throw;
            }

            // Initialize the aruco marker detector with parameters
            await _pvMediaFrameSourceGroup.StartArUcoMarkerTrackerAsync(
                markerSize, 
                (int)arUcoDictionaryName, 
                _unityCoordinateSystem);
#endif
        }

        // Get the latest frame from hololens media
        // frame source group -- not needed
#if ENABLE_WINMD_SUPPORT           
        void UpdateArUcoDetections(IList<DetectedArUcoMarker> detections)
        {
            if (!_mediaFrameSourceGroupsStarted ||
                _pvMediaFrameSourceGroup == null)
            {
                return;
            }

            // Detect ArUco markers in current frame
            // https://docs.opencv.org/2.4/modules/calib3d/doc/camera_calibration_and_3d_reconstruction.html#void%20Rodrigues(InputArray%20src,%20OutputArray%20dst,%20OutputArray%20jacobian)
            //IList<DetectedArUcoMarker> detectedArUcoMarkers = _pvMediaFrameSourceGroup.GetArUcoDetections();
            //_pvMediaFrameSourceGroup.DetectArUcoMarkers(_sensorType);

            // // Store the transformations for each detected marker
            Dictionary<int, Matrix4x4> markerTransforms = new Dictionary<int, Matrix4x4>();

            // If we detect a marker, display
            if (detections.Count != 0)
            {
                // Remove world anchor from game object
                if (_isWorldAnchored)
                {
                    try
                    {
                        DestroyImmediate(objectGo.GetComponent<WorldAnchor>());
                        _isWorldAnchored = false;
                    }
                    catch (Exception)
                    {
                        throw;
                    }
                }

                // Handle the cases based on the number of detections
                switch (detections.Count)
                {
                    case 2:
                        // Two markers detected
                        HandleTwoMarkers(detections);
                        break;
                    case 1:
                        // One marker detected
                        HandleOneMarker(detections);
                        break;
                    default:
                        break;
                }
            }
            else
            {
                // Add a world anchor to the attached gameobject
                objectGo.AddComponent<WorldAnchor>();
                _isWorldAnchored = true;
            }

            myText.text = "Detected markers: " + detections.Count + ". Began streaming sensor frames. ";
            myText.text += "\nRelative Position: " + relativePosition + "\nRelative Rotation: " + relativeRotation;
        }

        void HandleTwoMarkers(IList<DetectedArUcoMarker> detections)
        {
            foreach (var marker in detections)
            {
                if (marker.Id == 1)
                {
                    UpdateMarkerData(marker, markerGo1, out _lastPositionMarker1, out _lastRotationMarker1);
                    _positionMarker1Valid = curItr;
                }
                else if (marker.Id == 2)
                {
                    UpdateMarkerData(marker, markerGo2, out _lastPositionMarker2, out _lastRotationMarker2);
                    _positionMarker2Valid = curItr;
                }
            }

            Debug.Log("Two markers detected and updated.");
        }


        void HandleOneMarker(IList<DetectedArUcoMarker> detections)
        {
            var detectedMarker = detections[0];

            if (detectedMarker.Id == 1)
            {
                UpdateMarkerData(detectedMarker, markerGo1, out _lastPositionMarker1, out _lastRotationMarker1);
                _positionMarker1Valid = curItr;
            }
            else if (detectedMarker.Id == 2)
            {
                UpdateMarkerData(detectedMarker, markerGo2, out _lastPositionMarker2, out _lastRotationMarker2);
                _positionMarker2Valid = curItr;
            }

            Debug.Log($"One marker detected: ID = {detectedMarker.Id}");
        }


        void UpdateMarkerData(DetectedArUcoMarker marker, GameObject markerObj, out Vector3 lastPosition, out Quaternion lastRotation)
        {
            // Extract position and rotation in camera space
            Vector3 position = CvUtils.Vec3FromFloat3(marker.Position);
            Quaternion rotation = CvUtils.RotationQuatFromRodrigues(CvUtils.Vec3FromFloat3(marker.Rotation));

            // Transform to Unity's world space
            Matrix4x4 cameraToWorldUnity = CvUtils.Mat4x4FromFloat4x4(marker.CameraToWorldUnity);
            Matrix4x4 transformUnityCamera = CvUtils.TransformInUnitySpace(position, rotation);

            Matrix4x4 transformUnityWorld = cameraToWorldUnity * transformUnityCamera;
            lastPosition = CvUtils.GetVectorFromMatrix(transformUnityWorld);
            lastRotation = CvUtils.GetQuatFromMatrix(transformUnityWorld);

            markerObj.transform.SetPositionAndRotation(lastPosition, lastRotation);
            Debug.Log($"Marker {marker.Id} updated: Position = {lastPosition}, Rotation = {lastRotation}");
        }
#endif

        /// <summary>
        /// Stop the media frame source groups.
        /// </summary>
        /// <returns></returns>
        async Task StopHoloLensMediaFrameSourceGroup()
        {
#if ENABLE_WINMD_SUPPORT
            if (!_mediaFrameSourceGroupsStarted ||
                _pvMediaFrameSourceGroup == null)
            {
                return;
            }

            // Wait for frame source groups to stop.
            await _pvMediaFrameSourceGroup.StopAsync();
            _pvMediaFrameSourceGroup = null;

            // Set to null value
            _sensorFrameStreamerPv = null;

            // Bool to indicate closing
            _mediaFrameSourceGroupsStarted = false;

            myText.text = "Stopped streaming sensor frames. Okay to exit app.";
#endif
        }

        #region ComImport
        // https://docs.microsoft.com/en-us/windows/uwp/audio-video-camera/imaging
        [ComImport]
        [Guid("5B0D3235-4DBA-4D44-865E-8F1D0E4FD04D")]
        [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        unsafe interface IMemoryBufferByteAccess
        {
            void GetBuffer(out byte* buffer, out uint capacity);
        }
        #endregion

#if ENABLE_WINMD_SUPPORT
        // Get byte array from software bitmap.
        // https://github.com/qian256/HoloLensARToolKit/blob/master/ARToolKitUWP-Unity/Scripts/ARUWPVideo.cs
        unsafe byte* GetByteArrayFromSoftwareBitmap(SoftwareBitmap sb)
        {
            if (sb == null)
                return null;

            SoftwareBitmap sbCopy = new SoftwareBitmap(sb.BitmapPixelFormat, sb.PixelWidth, sb.PixelHeight);
            Interlocked.Exchange(ref sbCopy, sb);
            using (var input = sbCopy.LockBuffer(BitmapBufferAccessMode.Read))
            using (var inputReference = input.CreateReference())
            {
                byte* inputBytes;
                uint inputCapacity;
                ((IMemoryBufferByteAccess)inputReference).GetBuffer(out inputBytes, out inputCapacity);
                return inputBytes;
            }
        }
#endif

        #region TapGestureHandler
        private void InitializeHandler()
        {
            // New recognizer class
            _gestureRecognizer = new GestureRecognizer();

            // Set tap as a recognizable gesture
            _gestureRecognizer.SetRecognizableGestures(GestureSettings.DoubleTap);

            // Begin listening for gestures
            _gestureRecognizer.StartCapturingGestures();

            // Capture on gesture events with delegate handler
            _gestureRecognizer.Tapped += GestureRecognizer_Tapped;

            Debug.Log("Gesture recognizer initialized.");
        }

        // On tapped event, stop all frame source groups
        private void GestureRecognizer_Tapped(TappedEventArgs obj)
        {
            StopHoloLensMediaFrameSourceGroup();
            CloseHandler();
        }

        private void CloseHandler()
        {
            _gestureRecognizer.StopCapturingGestures();
            _gestureRecognizer.Dispose();
        }
        #endregion
    }
}

